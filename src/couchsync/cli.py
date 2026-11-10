from __future__ import annotations

import argparse
import asyncio
import getpass
import json
import secrets
import sqlite3
import sys
from pathlib import Path

from filelock import FileLock

from .calendar import generate
from .config import Config
from .database import Database
from .publisher import WebDAV, serve
from .scraper import browser
from .scraper.selectors import load
from .secrets import Session, Vault
from .sync import run
from .util import atomic_write


def auth_objects(cfg):
    import hashlib

    identity = hashlib.sha256(str(cfg.data.resolve()).encode()).hexdigest()[:20]
    vault = Vault(identity)
    return vault, Session(cfg.data / "session.enc", vault)


def parser():
    p = argparse.ArgumentParser(prog="couchsync")
    p.add_argument("--config", type=Path, help="Non-secret TOML configuration")
    commands = p.add_subparsers(dest="command", required=True)
    for name in ("setup", "login", "logout", "status", "preview", "doctor", "logs", "serve"):
        commands.add_parser(name)
    sync = commands.add_parser("sync")
    sync.add_argument("--dry-run", action="store_true")
    export = commands.add_parser("export")
    export.add_argument("--output", type=Path, required=True)
    export.add_argument(
        "--feed", choices=["all", "organized", "events", "hosting", "confirmed"], default="all"
    )
    for name in ("backup", "restore"):
        cmd = commands.add_parser(name)
        cmd.add_argument("path", type=Path)
    for name, options in {
        "auth": ["status", "refresh"],
        "scraper": ["check", "inspect", "diagnostics", "upgrade-events"],
        "service": ["install", "start", "stop", "status", "uninstall"],
        "calendar": ["url", "rotate-token", "revoke", "publish", "credentials"],
    }.items():
        group = commands.add_parser(name)
        group.add_argument("action", choices=options)
        if name == "service":
            group.add_argument("--task", choices=["all", "sync", "serve"], default="all")
        if name == "calendar":
            group.add_argument(
                "--feed",
                default="all",
                choices=["all", "organized", "events", "hosting", "confirmed"],
            )
    return p


def setup(cfg):
    if cfg.config.exists():
        print(
            "Existing configuration preserved. Edit it using examples/config.example.toml as reference."
        )
        return
    print(
        "Python 3.13+ and Chromium are required. Install Chromium: python -m playwright install chromium"
    )
    name = input("Calendar name [Couchsurfing]: ").strip() or "Couchsurfing"
    event_privacy = (
        input("Event privacy full/limited/generic/busy [limited]: ").strip() or "limited"
    )
    hosting_privacy = input("Hosting privacy full/limited/private [limited]: ").strip() or "limited"
    interval = int(input("Sync interval in seconds, minimum 3600 [3600]: ") or "3600")
    categories = input(
        "Categories, comma separated [organized,going,interested,invited,hosting]: "
    ).strip()
    enabled = categories.split(",") if categories else cfg.categories
    remote = input("Optional HTTPS WebDAV base URL (blank for local): ").strip()
    raw = (
        f"name = {json.dumps(name)}\ninterval = {interval}\n"
        f"event_privacy = {json.dumps(event_privacy)}\nhosting_privacy = {json.dumps(hosting_privacy)}\n"
        f"categories = {json.dumps([x.strip() for x in enabled])}\n[feeds.all]\n"
    )
    if remote:
        raw += f"\n[remote]\nbase_url = {json.dumps(remote)}\natomic_move = true\n"
    # Validate before writing a new configuration.
    cfg.name, cfg.interval, cfg.event_privacy, cfg.hosting_privacy = (
        name,
        interval,
        event_privacy,
        hosting_privacy,
    )
    cfg.categories = [x.strip() for x in enabled]
    cfg.remote = {"base_url": remote} if remote else {}
    cfg.validate()
    atomic_write(cfg.config, raw.encode())
    if input("Open interactive Couchsurfing login now? [y/N]: ").lower() == "y":
        _, session = auth_objects(cfg)
        asyncio.run(browser.login(session))
    print("Next: scraper inspect, configure selectors, scraper check, sync --dry-run, sync.")
    print("Background services: service install then service start, after a successful sync.")
    print("Local Apple subscription: http://127.0.0.1:8765/couchsurfing.ics")
    print(
        "Google Calendar requires an externally reachable HTTPS feed. See docs/google-calendar.md."
    )


def status(cfg):
    db = Database(cfg.data / "couchsync.db")
    try:
        counts = {}
        undated = 0
        for row in db.rows():
            record = json.loads(row["payload"])
            key = record["kind"] + ":" + record["status"]
            counts[key] = counts.get(key, 0) + 1
            undated += int(not record["start"] or not record["end"])
        print(
            json.dumps(
                {
                    "last_success": db.meta("last_success"),
                    "last_complete_success": db.meta("last_complete_success"),
                    "counts": counts,
                    "undated": undated,
                    "metrics": json.loads(db.meta("metrics") or "{}"),
                },
                indent=2,
            )
        )
    finally:
        db.close()


def doctor(cfg):
    checks = {"configuration": True}
    try:
        _, session = auth_objects(cfg)
        session.load()
        checks["session_decryptable"] = True
    except Exception:
        checks["session_decryptable"] = False
    try:
        load(cfg.selectors, cfg.categories)
        checks["selectors_configured"] = True
    except Exception:
        checks["selectors_configured"] = False
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        checks["chromium_installed"] = Path(pw.chromium.executable_path).exists()
    db = Database(cfg.data / "couchsync.db")
    try:
        checks["database_integrity"] = db.db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        db.close()
    import httpx

    try:
        checks["local_feed"] = (
            httpx.head(f"http://127.0.0.1:{cfg.port}/couchsurfing.ics", timeout=2).status_code
            == 200
        )
    except httpx.HTTPError:
        checks["local_feed"] = False
    checks["live_authentication_checked"] = False
    print(json.dumps(checks, indent=2))
    print("Service status: couchsync service status. Live authentication: couchsync scraper check.")


def calendar_command(cfg, args):
    if args.feed not in cfg.feeds:
        raise ValueError("Enable the requested feed in configuration first")
    if args.action == "url" and not cfg.remote:
        suffix = "couchsurfing" if args.feed == "all" else args.feed
        print(f"http://127.0.0.1:{cfg.port}/{suffix}.ics")
        return
    vault, _ = auth_objects(cfg)
    if args.action == "credentials":
        vault.set("webdav-user", input("WebDAV publishing username: "))
        vault.set("webdav-password", getpass.getpass("WebDAV publishing password: "))
        return
    if not cfg.remote:
        raise ValueError("Remote HTTPS publication is not configured")
    publisher = WebDAV(cfg, vault)
    if args.action == "url":
        print(publisher.url(args.feed))
    elif args.action == "publish":
        data = (cfg.data / "snapshots" / f"{args.feed}.ics").read_bytes()
        publisher.publish(args.feed, data)
        print("Published completed snapshot")
    elif args.action in {"rotate-token", "revoke"}:
        # Do not claim revocation until remote DELETE succeeds.
        old = vault.get("feed-" + args.feed)
        if args.action == "revoke":
            if old and old != "REVOKED":
                publisher.revoke(args.feed, old)
            # Tombstone blocks accidental republishing to the revoked URL.
            vault.set("feed-" + args.feed, "REVOKED")
            print("Revoked. Use rotate-token to create a new subscription URL.")
            return
        new = secrets.token_urlsafe(32)
        data = (cfg.data / "snapshots" / f"{args.feed}.ics").read_bytes()
        publisher.publish(args.feed, data, token=new)
        if old and old != "REVOKED":
            publisher.revoke(args.feed, old)
        vault.set("feed-" + args.feed, new)
        print("Rotated; run calendar url and replace the subscription in your calendar app")


def execute(args):
    cfg = Config.load(args.config)
    cfg.initialize()
    cmd = args.command
    if cmd == "setup":
        setup(cfg)
    elif cmd in {"login", "logout", "auth"}:
        _, session = auth_objects(cfg)
        if cmd == "logout":
            session.clear()
            print("Local session removed; revoke website sessions separately if needed")
        elif cmd == "auth" and args.action == "status":
            session.load()
            print(
                "Encrypted session decryptable; run scraper check to validate live authentication"
            )
        else:
            asyncio.run(browser.login(session))
    elif cmd == "sync":
        vault, session = auth_objects(cfg)
        print(json.dumps(run(cfg, session, vault, args.dry_run), indent=2))
    elif cmd == "status":
        status(cfg)
    elif cmd in {"export", "preview"}:
        db = Database(cfg.data / "couchsync.db")
        try:
            data = generate(db.rows(), cfg, getattr(args, "feed", "all"))
            if cmd == "export":
                atomic_write(args.output, data)
                print("Exported privacy-filtered calendar")
            else:
                from icalendar import Calendar

                events = Calendar.from_ical(data).walk("VEVENT")
                for event in events:
                    print(str(event.get("summary")), event.decoded("dtstart").isoformat())
        finally:
            db.close()
    elif cmd == "doctor":
        doctor(cfg)
    elif cmd == "scraper":
        if args.action == "upgrade-events":
            from .profiles import upgrade_events

            print(json.dumps(upgrade_events(cfg), indent=2))
        elif args.action == "diagnostics":
            doctor(cfg)  # Counts/booleans only, no HTML, source IDs, titles or cookies.
        elif args.action == "inspect":
            _, session = auth_objects(cfg)
            asyncio.run(browser.inspect(session))
        else:
            vault, session = auth_objects(cfg)
            # Use the same lock and rate limiting as sync; dry-run validates without updates.
            print(json.dumps(run(cfg, session, vault, dry_run=True), indent=2))
    elif cmd == "serve":
        serve(cfg)
    elif cmd == "service":
        from .scheduler import manage

        manage(cfg, args.action, args.task)
    elif cmd == "calendar":
        calendar_command(cfg, args)
    elif cmd == "logs":
        path = cfg.logs / "sync.log"
        print(path.read_text()[-10000:] if path.exists() else "No logs yet")
    elif cmd in {"backup", "restore"}:
        with FileLock(str(cfg.data / "sync.lock"), timeout=0):
            target = cfg.data / "couchsync.db"
            db = Database(target)
            try:
                if cmd == "backup":
                    db.backup(args.path)
                    print("Private database backup created; session keys are excluded")
                else:
                    with sqlite3.connect(
                        f"file:{args.path.resolve().as_posix()}?mode=ro", uri=True
                    ) as source:
                        if source.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                            raise ValueError("Backup integrity check failed")
                        if source.execute("PRAGMA user_version").fetchone()[0] != 1:
                            raise ValueError("Unsupported backup schema")
                        # Validate the complete schema and render before replacing anything.
                        from .models import Record

                        source.row_factory = sqlite3.Row
                        rows = [dict(row) for row in source.execute("SELECT * FROM records")]
                        required = {
                            "key",
                            "uid",
                            "payload",
                            "hash",
                            "sequence",
                            "first_seen",
                            "last_seen",
                            "verified",
                            "modified",
                            "canceled",
                            "completeness",
                        }
                        columns = {r[1] for r in source.execute("PRAGMA table_info(records)")}
                        if columns != required:
                            raise ValueError("Unexpected backup schema")
                        source.execute("SELECT key, value FROM meta").fetchall()
                        source.execute("SELECT key, at, payload, sequence FROM history").fetchall()
                        for row in rows:
                            Record(**json.loads(row["payload"])).validate()
                        rendered = {f: generate(rows, cfg, f) for f in cfg.feeds}
                        db.backup(
                            target.with_suffix(
                                ".before-restore-" + __import__("uuid").uuid4().hex + ".bak"
                            )
                        )
                        source.backup(db.db)
                    for feed, data in rendered.items():
                        atomic_write(cfg.data / "snapshots" / f"{feed}.ics", data)
                    print("Restored database and regenerated private snapshots")
            finally:
                db.close()


def main():
    args = parser().parse_args()
    try:
        execute(args)
    except KeyboardInterrupt:
        print("Stopped", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        # Never print third-party exceptions containing URLs, page content, or secrets.
        from .scraper.selectors import SelectorError

        safe = str(exc) if isinstance(exc, SelectorError) else type(exc).__name__
        print(
            f"Couchsync could not complete: {safe}. Run doctor; see docs/troubleshooting.md.",
            file=sys.stderr,
        )
        raise SystemExit(1)
