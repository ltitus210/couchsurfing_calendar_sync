import asyncio
import json
import threading
from contextlib import asynccontextmanager
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import pytest
import tomli_w

from couchsync.config import Config
from couchsync.database import Database
from couchsync.models import Record
from couchsync.profiles import upgrade_events
from couchsync.scraper.browser import browser, scrape
from couchsync.scraper.selectors import SelectorError, load
from couchsync.scraper.traffic import summary
from couchsync.sync import run


def event(source_id="Example1_ho", status="going"):
    return Record(
        source_id,
        "event",
        "Synthetic",
        "2026-12-01T18:00:00Z",
        "2026-12-01T20:00:00Z",
        status=status,
        raw_status=status,
        relationships=[status] if status != "canceled" else [],
    )


@pytest.fixture
def cfg(tmp_path):
    cfg = Config(
        tmp_path / "data",
        tmp_path / "config.toml",
        tmp_path / "logs",
        categories=["going", "interested", "organized"],
    )
    cfg.initialize()
    return cfg


def profile(observed=True):
    sources = []
    for category, tab, label in [
        ("going", "going", "Going"),
        ("interested", "interested", "Interested"),
        ("organized", "organizing", "Organizing"),
    ]:
        panel = f'role=tabpanel[name="{label}"]'
        source = {
            "category": category,
            "kind": "event",
            "url": f"https://www.couchsurfing.com/c/events/my-events?tab={tab}",
            "container": panel,
            "item": panel + " >> [data-couch-crash][data-user-created]",
            "max_pages": 1,
            "detail_link": 'a[href^="/c/events/"]',
            "detail_container": 'body:has(script[data-testid="hangout-json-ld"])',
            "event_json_ld": 'script[data-testid="hangout-json-ld"]',
        }
        if observed:
            source.update(completion="observed", tab_label=label, detail_navigation="same_tab")
        else:
            source["expected_count"] = 1
        sources.append(source)
    return {
        "validated_on": "Synthetic fixture only",
        "auth_marker": 'role=button[name="Profile"]',
        "sources": sources,
    }


def test_spa_variable_counts_and_shared_details(cfg):
    cfg.selectors.write_text(tomli_w.dumps(profile()))
    fixture = (Path(__file__).parent / "fixtures/spa-events.html").read_text()

    class Session:
        def load(self):
            return {"cookies": [], "origins": []}

        def save(self, state):
            pass

    async def check():
        async with browser() as context:
            await context.route(
                "**/*",
                lambda route: route.fulfill(status=200, content_type="text/html", body=fixture),
            )

            @asynccontextmanager
            async def reuse(*args):
                yield context

            with patch("couchsync.scraper.browser.browser", reuse):
                records, metrics = await scrape(cfg, Session())
            assert metrics["sources"] == {"going": 2, "interested": 1, "organized": 1}
            assert metrics["complete"] is False and metrics["observations_only"] is True
            assert (
                metrics["requests"] == 1
            )  # One app load; list tabs/details use client navigation.
            assert len(records) == 3
            organized = next(r for r in records if r.source_id == "Example1_ho")
            assert (
                organized.relationships == ["going", "organizing"]
                and organized.status == "organizing"
            )
            visits = await context.pages[0].evaluate("window.visits")
            assert visits == {"Example1_ho": 1, "Example2_ho": 1, "Example3_ho": 1}

    asyncio.run(check())


def test_background_media_are_blocked_before_transfer():
    hits = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            hits.append(self.path)
            if self.path == "/":
                body = b'<html><head><link rel="stylesheet" href="/style.css"><script src="/app.js"></script></head><body><img src="/photo.png"><div>Fixture</div></body></html>'
                kind = "text/html"
            elif self.path == "/style.css":
                body = b"body{font-family:serif}"
                kind = "text/css"
            else:
                body = b"window.syntheticReady=true;"
                kind = "application/javascript"
            self.send_response(200)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()

    async def check():
        async with browser() as context:
            page = await context.new_page()
            await page.goto(f"http://127.0.0.1:{server.server_port}/", wait_until="load")
            assert await page.evaluate("window.syntheticReady") is True
            measured = summary(context)
            assert measured["requests_blocked"] == 1
            assert measured["requests_allowed"] == 3
            assert measured["requests_by_type"]["image"] == 1

    try:
        asyncio.run(check())
    finally:
        server.shutdown()
        server.server_close()
        worker.join()
    assert "/photo.png" not in hits and "/app.js" in hits


def test_observations_preserve_missing_and_update_uids(cfg):
    db = Database(cfg.data / "test.db")
    try:
        with db.transaction():
            db.apply([event(), event("Missing_ho")], True)
        before = {r["key"]: r for r in db.rows()}
        with db.transaction():
            db.apply([event(status="interested"), event("New_ho")], False, observations_only=True)
        after = {r["key"]: r for r in db.rows()}
        assert after["event:Missing_ho"] == before["event:Missing_ho"]
        current = after["event:Example1_ho"]
        assert current["uid"] == before["event:Example1_ho"]["uid"] and current["sequence"] == 1
        assert (
            json.loads(current["payload"])["status"] == "interested"
            and current["completeness"] == "observed"
        )
        assert len(after) == 3
        with pytest.raises(ValueError), db.transaction():
            db.apply([], False)
    finally:
        db.close()


def test_observations_keep_unverified_organizer_membership(cfg):
    db = Database(cfg.data / "test.db")
    try:
        with db.transaction():
            db.apply([event(status="organizing")], True)
        with db.transaction():
            db.apply([event(status="interested")], False, observations_only=True)
        r = json.loads(db.rows()[0]["payload"])
        assert r["status"] == "organizing" and r["relationships"] == ["interested", "organizing"]
        with db.transaction():
            db.apply([event(status="canceled")], False, observations_only=True)
        assert db.rows()[0]["canceled"] == 1
    finally:
        db.close()


def test_observed_mass_cancellation_still_rolls_back(cfg):
    db = Database(cfg.data / "test.db")
    try:
        records = [event(f"Example{i}_ho") for i in range(4)]
        with db.transaction():
            db.apply(records, True)
        before = db.rows()
        with pytest.raises(ValueError), db.transaction():
            db.apply(
                [replace(r, status="canceled", relationships=[]) for r in records],
                False,
                observations_only=True,
            )
        assert db.rows() == before
    finally:
        db.close()


def test_profile_upgrade_is_reversible_and_idempotent(cfg):
    old = tomli_w.dumps(profile(False))
    cfg.selectors.write_text(old)
    result = upgrade_events(cfg)
    assert Path(result["backup"]).read_text() == old
    converted = load(cfg.selectors, cfg.categories)
    assert all(
        "expected_count" not in s and s["completion"] == "observed" for s in converted["sources"]
    )
    assert all(s["detail_navigation"] == "same_tab" for s in converted["sources"])
    assert upgrade_events(cfg)["result"] == "already_upgraded"


def test_profile_upgrade_rejects_unknown_source_without_overwrite(cfg):
    data = profile(False)
    data["sources"][0]["url"] = "https://www.couchsurfing.com/c/other"
    original = tomli_w.dumps(data)
    cfg.selectors.write_text(original)
    with pytest.raises(SelectorError):
        upgrade_events(cfg)
    assert cfg.selectors.read_text() == original and not list(cfg.selectors.parent.glob("*.bak"))


def test_observation_worker_reports_partial_coverage(cfg):
    async def observations(*args):
        return [event()], {
            "complete": False,
            "observations_only": True,
            "requests": 1,
            "sources": {"going": 1},
            "coverage": "verified observed events; full-list coverage unverified",
        }

    with patch("couchsync.sync.scrape", side_effect=observations):
        result = run(cfg, None, None)
    assert result["result"] == "updated_observations" and result["complete"] is False
    assert (cfg.data / "snapshots" / "all.ics").exists()


def test_publisher_service_can_install_without_scraper_profile(cfg, tmp_path):
    from couchsync.scheduler import manage

    with (
        patch("couchsync.scheduler.sys.platform", "darwin"),
        patch("couchsync.scheduler.Path.home", return_value=tmp_path),
        patch("couchsync.scheduler.os.getuid", return_value=501, create=True),
    ):
        manage(cfg, "install", "serve")
    directory = tmp_path / "Library/LaunchAgents"
    assert (directory / "org.couchsync.serve.plist").exists()
    assert not (directory / "org.couchsync.sync.plist").exists()


@pytest.mark.parametrize("status", [401, 403, 429])
def test_access_restriction_stops_later_transfers(status):
    from types import SimpleNamespace
    from couchsync.scraper.traffic import Traffic

    counter = Traffic()
    counter.response(
        SimpleNamespace(status=status, url="https://www.couchsurfing.com/c/events/my-events")
    )
    actions = []

    class Route:
        request = SimpleNamespace(resource_type="document")

        async def abort(self, error):
            actions.append("abort")

        async def continue_(self):
            actions.append("continue")

    asyncio.run(counter.route(Route()))
    assert actions == ["abort"] and counter.allowed == 0 and counter.blocked == 1


def test_third_party_access_errors_do_not_expire_the_account():
    from types import SimpleNamespace
    from couchsync.scraper.traffic import Traffic

    counter = Traffic()
    counter.response(SimpleNamespace(status=403, url="https://maps.example.test/unavailable"))
    assert not counter.access_restricted


def test_generic_detail_queries_remain_distinct():
    from urllib.parse import parse_qs, urlsplit
    from couchsync.scraper.browser import collect_page

    source = {
        "kind": "hosting",
        "container": "#incoming",
        "incoming_marker": "#incoming",
        "item": "article",
        "empty": "#empty",
        "detail_link": "a",
        "detail_container": "#stay",
        "statuses": {"Pending": "pending"},
        "fields": {
            "source_id": {"selector": ".id", "attribute": "data-id"},
            "title": {"selector": ".guest"},
            "raw_status": {"selector": ".status"},
            "start": {"selector": ".start", "attribute": "datetime"},
            "end": {"selector": ".end", "attribute": "datetime"},
        },
    }

    async def check():
        async with browser() as context:

            async def route_request(route):
                source_id = parse_qs(urlsplit(route.request.url).query)["id"][0]
                body = f'<div id="signed-in">Synthetic</div><div id="stay"><span class="id" data-id="{source_id}"></span><span class="guest">Synthetic guest</span><span class="status">Pending</span><time class="start" datetime="2026-12-01"></time><time class="end" datetime="2026-12-03"></time></div>'
                await route.fulfill(status=200, content_type="text/html", body=body)

            await context.route("https://www.couchsurfing.com/**", route_request)
            page = await context.new_page()
            await page.set_content(
                '<div id="signed-in">Synthetic</div><section id="incoming"><article><a href="https://www.couchsurfing.com/request?id=1">First</a></article><article><a href="https://www.couchsurfing.com/request?id=2">Second</a></article></section>'
            )
            records = await collect_page(page, source, "#signed-in", {})
            assert [record.source_id for record in records] == ["1", "2"]

    asyncio.run(check())
