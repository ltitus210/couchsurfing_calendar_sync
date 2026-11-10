from __future__ import annotations

import hashlib
import secrets
from email.utils import formatdate, parsedate_to_datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Protocol
from urllib.parse import quote, urlsplit

import httpx

from .util import https_url


class Publisher(Protocol):
    def publish(self, feed: str, data: bytes) -> None: ...


class WebDAV:
    """TLS WebDAV static-file publisher; credentials stay in the OS vault."""

    def __init__(self, cfg, vault):
        self.cfg, self.vault = cfg, vault
        self.base = https_url(cfg.remote["base_url"]).rstrip("/")

    def url(self, feed: str, token: str | None = None) -> str:
        value = token or self.vault.token(feed)
        if value == "REVOKED":
            raise RuntimeError("Feed revoked; use calendar rotate-token")
        return f"{self.base}/{quote(value, safe='')}/{feed}.ics"

    def publish(self, feed: str, data: bytes, token: str | None = None) -> None:
        username = self.vault.get("webdav-user")
        password = self.vault.get("webdav-password")
        if not username or not password:
            raise RuntimeError("Configure WebDAV publishing credentials with calendar credentials")
        url = self.url(feed, token)
        directory = url.rsplit("/", 1)[0]
        with httpx.Client(auth=(username, password), timeout=30, follow_redirects=False) as client:
            response = client.request("MKCOL", directory)
            if response.status_code not in {201, 405}:
                raise RuntimeError("WebDAV directory creation failed")
            atomic = self.cfg.remote.get("atomic_move", True)
            temporary = url + ".tmp-" + secrets.token_hex(8) if atomic else url
            response = client.put(
                temporary, content=data, headers={"Content-Type": "text/calendar"}
            )
            if response.status_code not in {200, 201, 204}:
                raise RuntimeError("Calendar upload failed; previous published file retained")
            if atomic:
                response = client.request(
                    "MOVE", temporary, headers={"Destination": url, "Overwrite": "T"}
                )
                if response.status_code not in {201, 204}:
                    client.delete(temporary)
                    raise RuntimeError("WebDAV atomic MOVE failed; previous snapshot retained")

    def revoke(self, feed: str, token: str) -> None:
        with httpx.Client(
            auth=(self.vault.get("webdav-user"), self.vault.get("webdav-password")),
            timeout=30,
            follow_redirects=False,
        ) as client:
            response = client.delete(self.url(feed, token))
            if response.status_code not in {200, 204, 404}:
                raise RuntimeError("Remote revocation failed; old token remains active")


def handler(snapshot_dir: Path, feeds: set[str]):
    class FeedHandler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Never log bearer URLs or private request headers.

        def do_HEAD(self):
            self.do_GET(head=True)

        def do_GET(self, head=False):
            name = urlsplit(self.path).path
            mapping = {("/couchsurfing.ics" if f == "all" else f"/{f}.ics"): f for f in feeds}
            if name not in mapping:
                self.send_error(404)
                return
            path = snapshot_dir / f"{mapping[name]}.ics"
            if not path.exists():
                self.send_error(503, "No completed snapshot")
                return
            data = path.read_bytes()
            etag = '"' + hashlib.sha256(data).hexdigest() + '"'
            modified = path.stat().st_mtime
            unchanged = self.headers.get("If-None-Match") == etag
            if "If-None-Match" not in self.headers and self.headers.get("If-Modified-Since"):
                try:
                    unchanged = int(modified) <= int(
                        parsedate_to_datetime(self.headers["If-Modified-Since"]).timestamp()
                    )
                except (ValueError, TypeError, OverflowError):
                    pass
            self.send_response(304 if unchanged else 200)
            self.send_header("ETag", etag)
            self.send_header("Last-Modified", formatdate(modified, usegmt=True))
            self.send_header("Cache-Control", "private, max-age=300")
            self.send_header("Content-Type", "text/calendar; charset=utf-8")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(0 if unchanged else len(data)))
            self.end_headers()
            if not unchanged and not head:
                self.wfile.write(data)

    return FeedHandler


def serve(cfg) -> None:
    ThreadingHTTPServer(
        ("127.0.0.1", cfg.port), handler(cfg.data / "snapshots", set(cfg.feeds))
    ).serve_forever()
