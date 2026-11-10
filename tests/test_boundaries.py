import asyncio
import json

from couchsync.database import Database
import plistlib
import threading
import tomllib
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree as ET

import httpx
import pytest
from filelock import FileLock, Timeout

from couchsync.config import Config
from couchsync.publisher import WebDAV, handler
from couchsync.scheduler import launchd, windows_xml
from couchsync.scraper.browser import browser, collect_page
from couchsync.scraper.selectors import SelectorError, load
from couchsync.sync import run
from couchsync.util import atomic_write

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def cfg(tmp_path):
    result = Config(tmp_path / "data", tmp_path / "config.toml", tmp_path / "logs")
    result.initialize()
    return result


def test_schedulers(cfg):
    mac = plistlib.loads(plistlib.dumps(launchd(cfg, "sync")))
    assert mac["StartInterval"] == 3600
    assert mac["StartCalendarInterval"] == {"Minute": 0}
    assert mac["ProgramArguments"][-1] == "sync"
    assert launchd(cfg, "serve")["KeepAlive"]
    tree = ET.fromstring(windows_xml(cfg, "sync", "Test User"))
    ns = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
    assert tree.find(".//t:LogonType", ns).text == "InteractiveToken"
    assert tree.find(".//t:RunLevel", ns).text == "LeastPrivilege"
    assert tree.find(".//t:Interval", ns).text == "PT3600S"
    assert tree.find(".//t:StartWhenAvailable", ns).text == "true"
    assert tree.find(".//t:MultipleInstancesPolicy", ns).text == "IgnoreNew"


def test_feed_server_caching_traversal_no_scrape(cfg):
    folder = cfg.data / "snapshots"
    atomic_write(folder / "all.ics", b"fixture calendar")
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler(folder, {"all"}))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        with httpx.Client() as client:
            response = client.get(base + "/couchsurfing.ics")
            assert response.status_code == 200 and response.content == b"fixture calendar"
            assert (
                client.get(
                    base + "/couchsurfing.ics", headers={"If-None-Match": response.headers["etag"]}
                ).status_code
                == 304
            )
            assert client.head(base + "/couchsurfing.ics").content == b""
            assert client.get(base + "/%2e%2e/session.enc").status_code == 404
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


class Vault:
    def __init__(self):
        self.values = {"webdav-user": "synthetic-user", "webdav-password": "synthetic-password"}

    def get(self, key):
        return self.values.get(key)

    def token(self, feed):
        return self.values.get("feed-" + feed, "synthetic-token")


def test_webdav_atomic_publish_revocation(cfg):
    cfg.remote = {"base_url": "https://calendar.example.com/private", "atomic_move": True}
    requests = []

    def receive(request):
        requests.append(request)
        return httpx.Response(
            {"MKCOL": 201, "PUT": 201, "MOVE": 204, "DELETE": 204}[request.method]
        )

    real = httpx.Client
    with patch(
        "couchsync.publisher.httpx.Client",
        side_effect=lambda **kw: real(transport=httpx.MockTransport(receive), **kw),
    ):
        publisher = WebDAV(cfg, Vault())
        publisher.publish("all", b"calendar")
        assert [r.method for r in requests] == ["MKCOL", "PUT", "MOVE"]
        assert requests[-1].headers["destination"].endswith("/synthetic-token/all.ics")
        assert requests[-2].content == b"calendar"
        publisher.revoke("all", "old-token")
        assert requests[-1].method == "DELETE"
        assert "old-token" in str(requests[-1].url)
    vault = Vault()
    vault.values["feed-all"] = "REVOKED"
    with pytest.raises(RuntimeError):
        WebDAV(cfg, vault).url("all")


def test_webdav_failed_upload_does_not_move(cfg):
    cfg.remote = {"base_url": "https://calendar.example.com/private"}
    requests = []

    def receive(request):
        requests.append(request.method)
        return httpx.Response(201 if request.method == "MKCOL" else 500)

    real = httpx.Client
    with patch(
        "couchsync.publisher.httpx.Client",
        side_effect=lambda **kw: real(transport=httpx.MockTransport(receive), **kw),
    ):
        with pytest.raises(RuntimeError):
            WebDAV(cfg, Vault()).publish("all", b"calendar")
    assert requests == ["MKCOL", "PUT"]


def test_worker_failure_and_due_guard(cfg):
    atomic_write(cfg.data / "snapshots" / "all.ics", b"last-good")

    async def fail(*args):
        raise SelectorError("Synthetic failure")

    with patch("couchsync.sync.scrape", side_effect=fail):
        with pytest.raises(SelectorError):
            run(cfg, None, None)
        assert (cfg.data / "snapshots" / "all.ics").read_bytes() == b"last-good"
        assert run(cfg, None, None)["result"] == "not_due"
    with FileLock(str(cfg.data / "sync.lock")):
        with pytest.raises(Timeout):
            run(cfg, None, None)


def test_selectors_require_inspection(cfg):
    with pytest.raises(SelectorError):
        load(cfg.selectors, cfg.categories)
    adapter = load(FIXTURES / "selectors.synthetic.toml", ["interested"])
    assert len(adapter["sources"]) == 1
    with pytest.raises(SelectorError):
        load(FIXTURES / "selectors.synthetic.toml", cfg.categories)


def test_real_browser_synthetic_parser():
    async def check():
        adapter = tomllib.loads((FIXTURES / "selectors.synthetic.toml").read_text())
        source = adapter["sources"][0]
        async with browser() as context:
            page = await context.new_page()
            await page.set_content((FIXTURES / "synthetic.html").read_text())
            records = await collect_page(page, source, adapter["auth_marker"])
            assert records[0].status == "interested" and records[0].source_id == "synthetic-42"
            await page.locator(".status").evaluate("el => el.textContent = 'Unknown'")
            with pytest.raises(SelectorError):
                await collect_page(page, source, adapter["auth_marker"])
            await page.locator("article").evaluate("el => el.remove()")
            with pytest.raises(SelectorError):
                await collect_page(page, source, adapter["auth_marker"])
            await page.locator("#list").evaluate(
                "el => el.innerHTML = '<p id=empty>Explicit empty list</p>'"
            )
            assert await collect_page(page, source, adapter["auth_marker"]) == []

    asyncio.run(check())


def test_live_adapter_navigation_with_synthetic_routes(cfg):
    """Exercise actual Playwright navigation/pagination while intercepting all website traffic."""
    from contextlib import asynccontextmanager
    from couchsync.scraper.browser import scrape

    fixture = (FIXTURES / "synthetic.html").read_text()
    cfg.categories = ["interested"]
    cfg.selectors.write_text((FIXTURES / "selectors.synthetic.toml").read_text())

    class Session:
        def load(self):
            return {"cookies": [], "origins": []}

        def save(self, state):
            pass

    async def check():
        async with browser() as context:
            await context.route(
                "**/*",
                lambda route: route.fulfill(status=200, body=fixture, content_type="text/html"),
            )

            @asynccontextmanager
            async def reuse(*args):
                yield context

            with patch("couchsync.scraper.browser.browser", reuse):
                records, metrics = await scrape(cfg, Session())
            assert len(records) == 1 and metrics["complete"]
            assert metrics["requests"] == 1

    asyncio.run(check())


def test_navigation_stops_on_rate_limit():
    from couchsync.scraper.browser import navigate

    async def check():
        async with browser() as context:
            count = 0

            async def limited(route):
                nonlocal count
                count += 1
                await route.fulfill(status=429, body="Synthetic rate limit")

            await context.route("**/*", limited)
            page = await context.new_page()
            with pytest.raises(SelectorError):
                await navigate(page, "https://www.couchsurfing.com/")
            assert count == 1

    asyncio.run(check())


def test_successful_worker_and_dry_run(cfg):
    from couchsync.models import Record

    record = Record(
        "fictional", "hosting", "Synthetic Guest", "2026-12-01", "2026-12-04", status="pending"
    )

    async def collect(*args):
        return [record], {"complete": True, "requests": 1, "sources": {"hosting": 1}}

    with patch("couchsync.sync.scrape", side_effect=collect):
        result = run(cfg, None, None, dry_run=True)
        assert result["result"] == "dry_run"
        db = Database(cfg.data / "couchsync.db")
        assert db.rows() == []
        with db.transaction():
            db.db.execute("DELETE FROM meta WHERE key='last_attempt'")
        db.close()
        assert not (cfg.data / "snapshots" / "all.ics").exists()
        assert run(cfg, None, None)["result"] == "success"
        assert b"Synthetic Guest" not in (cfg.data / "snapshots" / "all.ics").read_bytes()


def test_backup_restore_cli(cfg, tmp_path):
    from couchsync.cli import execute, parser
    from couchsync.models import Record

    cfg.config.write_text(
        f"data = {json.dumps(str(cfg.data))}\nlogs = {json.dumps(str(cfg.logs))}\n"
    )
    db = Database(cfg.data / "couchsync.db")
    with db.transaction():
        db.apply(
            [Record("stay", "hosting", "Synthetic", "2026-12-01", "2026-12-03", status="pending")],
            True,
        )
    db.close()
    backup = tmp_path / "backup.db"
    execute(parser().parse_args(["--config", str(cfg.config), "backup", str(backup)]))
    execute(parser().parse_args(["--config", str(cfg.config), "restore", str(backup)]))
    assert (cfg.data / "snapshots" / "all.ics").exists()
    assert list(cfg.data.glob("*.bak"))
