from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler

from filelock import FileLock

from .calendar import generate
from .database import Database
from .publisher import WebDAV
from .scraper.browser import scrape
from .util import atomic_write, now


def logger(cfg):
    log = logging.getLogger("couchsync")
    if not log.handlers:
        h = RotatingFileHandler(cfg.logs / "sync.log", maxBytes=250000, backupCount=3)
        (cfg.logs / "sync.log").chmod(0o600)
        h.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        log.addHandler(h)
        log.setLevel(logging.INFO)
    return log


def snapshots(db, cfg):
    # Render all feeds first: invalid records cannot replace a good snapshot.
    rendered = {feed: generate(db.rows(), cfg, feed) for feed in cfg.feeds}
    for feed, data in rendered.items():
        atomic_write(cfg.data / "snapshots" / f"{feed}.ics", data)
    return rendered


def run(cfg, session, vault, dry_run=False):
    cfg.initialize()
    log = logger(cfg)
    started = time.monotonic()
    with FileLock(str(cfg.data / "sync.lock"), timeout=0):
        db = Database(cfg.data / "couchsync.db")
        try:
            last = db.meta("last_attempt")
            if (
                last
                and (datetime.now(UTC) - datetime.fromisoformat(last)).total_seconds()
                < cfg.interval
            ):
                return {"result": "not_due"}
            # Attempts, including failures and dry runs, respect the rate limit.
            with db.transaction():
                db.meta("last_attempt", now())
            records, metrics = asyncio.run(scrape(cfg, session))
            if dry_run:
                # Validate reconciliation, rendering and mass-cancellation safety, then roll back.
                class DryRun(Exception):
                    pass

                try:
                    with db.transaction():
                        db.apply(records, metrics["complete"], cfg.max_cancellations)
                        for feed in cfg.feeds:
                            generate(db.rows(), cfg, feed)
                        raise DryRun()
                except DryRun:
                    pass
                return {"result": "dry_run", **metrics}
            with db.transaction():
                db.apply(records, metrics["complete"], cfg.max_cancellations)
                rendered = {f: generate(db.rows(), cfg, f) for f in cfg.feeds}
                db.meta("metrics", json.dumps(metrics))
            for feed, data in rendered.items():
                atomic_write(cfg.data / "snapshots" / f"{feed}.ics", data)
            if cfg.remote:
                publisher = WebDAV(cfg, vault)
                for feed, data in rendered.items():
                    publisher.publish(feed, data)
            log.info(
                "sync success records=%d requests=%d duration=%.2f",
                len(records),
                metrics["requests"],
                time.monotonic() - started,
            )
            return {"result": "success", **metrics}
        except Exception as exc:
            # Exception messages may contain URLs or extracted personal data: type only in logs.
            log.error(
                "sync failed type=%s duration=%.2f", type(exc).__name__, time.monotonic() - started
            )
            raise
        finally:
            db.close()
