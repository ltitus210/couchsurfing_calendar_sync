import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch

import pytest

from couchsync.cli import setup
from couchsync.config import Config
from couchsync.database import Database
from couchsync.models import Record
from couchsync.profiles import export_defaults, upgrade_events
from couchsync.scraper.browser import browser, scrape
from couchsync.scraper.defaults import profile
from couchsync.scraper.hosting import (
    LayoutUnavailable,
    collect_hosting,
    incoming_status,
    stay_dates,
    stay_state,
)
from couchsync.scraper.selectors import SelectorError, load


@pytest.fixture
def cfg(tmp_path):
    result = Config(tmp_path / "data", tmp_path / "config.toml", tmp_path / "logs")
    result.initialize()
    return result


def test_shared_defaults_cover_requested_categories_without_account_data(cfg):
    data = load(cfg.selectors, cfg.categories)
    assert {s["category"] for s in data["sources"]} == set(cfg.categories)
    assert not cfg.selectors.exists()
    text = json.dumps(data)
    assert "expected_count" not in text and "latitude" not in text and "/Users/" not in text
    assert (
        next(s for s in data["sources"] if s["category"] == "hosting")["adapter"]
        == "messages_stays"
    )
    assert next(s for s in data["sources"] if s["category"] == "invited")["optional"]
    data["sources"].clear()
    assert profile(cfg.categories)["sources"]  # No process-wide mutation of defaults.


def test_fresh_setup_prints_sync_instead_of_inspection_handoff(cfg, capsys):
    with patch("builtins.input", side_effect=["", "", "", "", "", "", "n"]):
        setup(cfg)
    output = capsys.readouterr().out
    assert "no initial inspection needed" in output
    assert "Next:" in output and " sync" in output
    assert "Log in first:" in output and " login" in output
    assert cfg.config.exists() and not cfg.selectors.exists()
    assert load(Config.load(cfg.config).selectors, cfg.categories)["layout_version"]


def test_custom_profile_precedence_and_explicit_missing_override(cfg):
    custom = Path(__file__).parent / "fixtures/selectors.synthetic.toml"
    cfg.selectors.write_bytes(custom.read_bytes())
    assert load(cfg.selectors, ["interested"])["auth_marker"] == "#signed-in"
    with pytest.raises(SelectorError):
        load(cfg.config.parent / "custom-missing.toml", ["going"])


def test_repair_export_is_opt_in_and_preserves_existing_files(cfg):
    assert upgrade_events(cfg)["result"] == "already_current"
    result = export_defaults(cfg)
    assert result["result"] == "exported"
    saved = cfg.selectors.read_bytes()
    assert load(cfg.selectors, cfg.categories)["layout_version"]
    with pytest.raises(SelectorError):
        export_defaults(cfg)
    assert cfg.selectors.read_bytes() == saved


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Wednesday, November 11 – Thursday, November 12, 2026", ("2026-11-11", "2026-11-12")),
        ("December 31 – January 2, 2027", ("2026-12-31", "2027-01-02")),
        ("November 11, 2026", ("2026-11-11", "")),
        ("November 11 – November 12", ("", "")),
        ("February 30 – March 2, 2026", ("", "")),
        ("November 11 – November 11, 2026", ("2026-11-11", "2026-11-11")),
    ],
)
def test_hosting_dates_require_explicit_source_year(text, expected):
    assert stay_dates(text) == expected


@pytest.mark.parametrize(
    "heading,text,banner,accept,decline,trip,expected",
    [
        ("Your Request", "Your guest", "Pending Stay", True, True, False, None),
        ("Stay Request", "", "Pending Stay", True, True, False, "pending"),
        ("Stay Request", "", "Pending Stay", True, True, True, None),
        (
            "Your Guest",
            "Waiting on guest to confirm",
            "Accepted Stay",
            False,
            False,
            False,
            "pending",
        ),
        ("Your Guest", "Request accepted", "Confirmed Stay", False, False, False, "confirmed"),
        ("Your Stay", "", "Confirmed Stay", False, False, False, None),
    ],
)
def test_incoming_direction_is_required(heading, text, banner, accept, decline, trip, expected):
    assert incoming_status(heading, text, banner, accept, decline, trip) == expected


@pytest.mark.parametrize("empty", [False, True])
@pytest.mark.parametrize("invited", [False, True])
def test_default_event_layout_without_per_account_files(cfg, empty, invited):
    fixture = (Path(__file__).parent / "fixtures/spa-events.html").read_text()
    if invited:
        fixture = fixture.replace(
            'organizing:["Example1_ho"]', 'organizing:["Example1_ho"],invited:["Example4_ho"]'
        )
        fixture = fixture.replace(
            "organizing:'Organizing'", "organizing:'Organizing',invited:'Invited'"
        )
    if empty:
        fixture = fixture.replace('invited:["Example4_ho"]', "invited:[]")
        fixture = (
            fixture.replace('going:["Example1_ho","Example2_ho"]', "going:[]")
            .replace('interested:["Example3_ho"]', "interested:[]")
            .replace('organizing:["Example1_ho"]', "organizing:[]")
        )
        fixture = fixture.replace(
            "window.addEventListener('popstate',render);render();",
            "const originalRender=render;render=function(){originalRender();const panel=document.querySelector('[role=tabpanel]');if(panel&&!panel.children.length)panel.innerHTML='<p>No upcoming events</p>';};window.addEventListener('popstate',render);render();",
        )

    class Session:
        def load(self):
            return {"cookies": [], "origins": []}

        def save(self, state):
            pass

    async def check():
        async with browser() as context:
            context.set_default_timeout(250)
            await context.route(
                "**/*",
                lambda route: route.fulfill(status=200, content_type="text/html", body=fixture),
            )

            @asynccontextmanager
            async def reuse(*args):
                yield context

            with patch("couchsync.scraper.browser.browser", reuse):
                records, metrics = await scrape(cfg, Session())
            assert len(records) == (0 if empty else 3 + int(invited))
            if invited and not empty:
                assert any(r.status == "invited" for r in records)
            assert metrics["layout"] == "2026-11-10" and metrics["complete"] is False
            assert ("invited" in metrics["source_notes"]) is not invited
            assert "hosting" in metrics["source_notes"]
            assert not cfg.selectors.exists()

    asyncio.run(check())


def test_stay_panel_parser_ignores_message_contents():
    async def check():
        async with browser() as context:
            page = await context.new_page()
            await page.goto("about:blank")
            await page.set_content(
                '<ul role="log"><li><h4>Your Guest</h4><div>When</div><div>Travelers</div><button>Accept Stay</button><button>Decline</button></li></ul>'
            )
            with pytest.raises(LayoutUnavailable):
                from couchsync.scraper.hosting import request_panel

                await request_panel(page)

    asyncio.run(check())


def test_assumed_stays_ui_is_read_only_and_includes_both_directions():
    fixture = (Path(__file__).parent / "fixtures/stays-assumed.html").read_text()

    async def check():
        async with browser() as context:
            unsafe = []
            await context.expose_binding("unsafe", lambda source: unsafe.append(True))
            await context.route(
                "**/*",
                lambda route: route.fulfill(status=200, content_type="text/html", body=fixture),
            )
            page = await context.new_page()
            source = next(s for s in profile(["hosting"])["sources"])
            records, note = await collect_hosting(page, source, 'role=button[name="Profile"]')
            assert len(records) == 5
            assert {r.status for r in records} == {"pending", "confirmed"}
            assert all(r.start == "2026-11-11" and r.end == "2026-11-12" for r in records)
            assert {r.direction for r in records} == {"incoming", "outgoing"}
            assert (
                next(r for r in records if r.source_id == "OutgoingAccepted_tp_cs").status
                == "pending"
            )
            assert (
                next(r for r in records if r.source_id == "OutgoingConfirmed_tp_cs").status
                == "confirmed"
            )
            assert all(r.url.endswith("/stays/" + r.source_id) for r in records)
            assert "1 unrecognized stay panels skipped" in note
            assert "PRIVATE MESSAGE" not in str(records) and unsafe == []

    asyncio.run(check())


@pytest.mark.parametrize("direction", ["incoming", "outgoing"])
def test_stay_observations_update_pending_keep_uid_and_retain_missing(cfg, direction):
    pending = Record(
        "SyntheticStay",
        "hosting",
        "Synthetic person",
        "2026-11-11",
        "2026-11-12",
        status="pending",
        direction=direction,
    )
    db = Database(cfg.data / "test.db")
    try:
        with db.transaction():
            db.apply([pending], False, observations_only=True)
        before = db.rows()[0]
        with db.transaction():
            db.apply([replace(pending, status="confirmed")], False, observations_only=True)
        confirmed = db.rows()[0]
        assert confirmed["uid"] == before["uid"] and confirmed["sequence"] == 1
        assert json.loads(confirmed["payload"])["status"] == "confirmed"
        with db.transaction():
            db.apply([], False, observations_only=True)
        assert db.rows()[0] == confirmed
        with pytest.raises(ValueError), db.transaction():
            db.apply([replace(pending, direction="unknown")], False, observations_only=True)
        assert db.rows()[0] == confirmed
    finally:
        db.close()


@pytest.mark.parametrize(
    "banner,expected",
    [
        ("Pending Stay", "pending"),
        ("Accepted Stay", "pending"),
        ("Confirmed Stay", "confirmed"),
        ("Upcoming Stay", "confirmed"),
    ],
)
def test_outgoing_stay_state_uses_explicit_metadata(banner, expected):
    assert stay_state("Your Request", banner, False, False, True) == ("outgoing", expected)
    assert stay_state("Your Request", banner, True, True, True) is None
    assert stay_state("Your Stay", banner, False, False, False) is None
