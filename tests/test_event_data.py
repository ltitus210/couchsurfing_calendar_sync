import asyncio
import json
from contextlib import asynccontextmanager
from unittest.mock import patch

import pytest
import tomli_w

from couchsync.config import Config
from couchsync.scraper.browser import browser, scrape
from couchsync.scraper.event_data import event_record
from couchsync.scraper.selectors import SelectorError, load


def sample(**changes):
    data = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": "Synthetic gathering café",
        "description": "Fictional fixture only",
        "url": "https://www.couchsurfing.com/c/events/synthetic-gathering-Test123_ho",
        "eventStatus": "https://schema.org/EventScheduled",
        "startDate": "2026-12-01T23:00:00.000Z",
        "endDate": "2026-12-02T01:00:00.000Z",
        "location": {"@type": "Place", "name": "Synthetic venue"},
    }
    return data | changes


@pytest.mark.parametrize(
    "category,expected",
    [
        ("organized", "organizing"),
        ("going", "going"),
        ("interested", "interested"),
        ("invited", "invited"),
    ],
)
def test_structured_event_relationships(category, expected):
    record = event_record(json.dumps(sample()), category)
    assert record.source_id == "Test123_ho" and record.status == expected
    assert record.relationships == [expected]
    assert record.dates()[0].hour == 23
    assert record.location == "Synthetic venue"


def test_cancellation_stable_id():
    active = event_record(json.dumps(sample()), "going")
    canceled = event_record(
        json.dumps(sample(eventStatus="https://schema.org/EventCancelled")), "going"
    )
    assert active.key == canceled.key and canceled.status == "canceled"
    assert canceled.relationships == []


@pytest.mark.parametrize(
    "changes",
    [
        {"@type": "Person"},
        {"startDate": ""},
        {"endDate": "2026-12-01T22:00:00Z"},
        {"startDate": "2026-12-01T23:00:00"},
        {"eventStatus": "https://schema.org/EventPostponed"},
        {"url": "https://evil.example/c/events/synthetic-Test123_ho"},
        {"url": "https://www.couchsurfing.com/c/events/title-without-stable-id"},
        {"location": "Unknown shape"},
    ],
)
def test_reject_invalid_structured_data(changes):
    with pytest.raises(SelectorError):
        event_record(json.dumps(sample(**changes)), "going")


def profile(count=1):
    panel = 'role=tabpanel[name="Going"]'
    return {
        "validated_on": "Synthetic fixture only",
        "auth_marker": 'role=button[name="Profile"]',
        "sources": [
            {
                "category": "going",
                "kind": "event",
                "url": "https://www.couchsurfing.com/c/events/my-events?tab=going",
                "container": panel,
                "item": panel + " >> [data-couch-crash][data-user-created]",
                "expected_count": count,
                "max_pages": 1,
                "detail_link": 'a[href^="/c/events/"]',
                "detail_container": 'body:has(script[data-testid="hangout-json-ld"])',
                "event_json_ld": 'script[data-testid="hangout-json-ld"]',
            }
        ],
    }


@pytest.mark.parametrize(
    "visible_count,expected,duplicate", [(1, 1, False), (0, 1, False), (2, 1, False), (2, 2, True)]
)
def test_real_browser_inspected_count_profile(tmp_path, visible_count, expected, duplicate):
    cfg = Config(
        tmp_path / "data", tmp_path / "config.toml", tmp_path / "logs", categories=["going"]
    )
    cfg.selectors.write_text(tomli_w.dumps(profile(expected)))
    load(cfg.selectors, cfg.categories)

    class Session:
        def load(self):
            return {"cookies": [], "origins": []}

        def save(self, state):
            pass

    async def check():
        async with browser() as context:
            cards = "".join(
                '<div data-couch-crash="false" data-user-created="true"><a href="/c/events/synthetic-gathering-Test123_ho">Synthetic</a></div>'
                for _ in range(visible_count)
            )
            listing = (
                '<button aria-label="Profile"></button><section role="tabpanel" aria-label="Going">'
                + cards
                + "</section>"
            )
            detail = (
                '<button aria-label="Profile"></button><script data-testid="hangout-json-ld" type="application/ld+json">'
                + json.dumps(sample())
                + "</script>"
            )
            hits = []

            async def route_request(route):
                hits.append(route.request.url)
                html = listing if "my-events" in route.request.url else detail
                await route.fulfill(status=200, content_type="text/html", body=html)

            await context.route("**/*", route_request)

            @asynccontextmanager
            async def reuse(*args):
                yield context

            with patch("couchsync.scraper.browser.browser", reuse):
                if visible_count != expected or duplicate:
                    with pytest.raises(SelectorError):
                        await scrape(cfg, Session())
                else:
                    records, metrics = await scrape(cfg, Session())
                    assert len(records) == 1 and records[0].start.endswith("Z")
                    assert metrics["coverage"] == "inspected-count event lists"
            if visible_count != expected:
                assert len(hits) == 1  # Count failure is detected before detail requests.

    asyncio.run(check())


@pytest.mark.parametrize("value", [0, -1, True, "1"])
def test_invalid_inspected_counts(tmp_path, value):
    path = tmp_path / "selectors.toml"
    path.write_text(tomli_w.dumps(profile(value)))
    with pytest.raises(SelectorError):
        load(path, ["going"])


def test_separate_selector_profile(tmp_path):
    path = tmp_path / "event-first.toml"
    path.write_text('selector_file = "event-first.selectors.toml"\ncategories = ["going"]\n')
    cfg = Config.load(path)
    assert cfg.selectors == tmp_path / "event-first.selectors.toml"


@pytest.mark.parametrize(
    "location,expected",
    [
        (
            {"name": "Fictional Hall", "address": "100 Example St, Example City"},
            "Fictional Hall\n100 Example St, Example City",
        ),
        (
            {
                "name": "Fictional Hall",
                "address": {
                    "@type": "PostalAddress",
                    "streetAddress": "100 Example St",
                    "addressLocality": "Example City",
                    "addressRegion": "DC",
                    "postalCode": "00000",
                    "addressCountry": "US",
                },
            },
            "Fictional Hall\n100 Example St\nExample City, DC 00000\nUS",
        ),
        (
            {
                "address": {
                    "streetAddress": "100 Example St",
                    "addressCountry": {"@type": "Country", "name": "Example Country"},
                }
            },
            "100 Example St\nExample Country",
        ),
        (
            {"name": "100 Example St", "address": {"streetAddress": "100 Example St"}},
            "100 Example St",
        ),
        ({"name": "Online"}, "Online"),
        ({}, ""),
    ],
)
def test_event_location_includes_source_postal_address(location, expected):
    assert event_record(json.dumps(sample(location=location)), "going").location == expected


@pytest.mark.parametrize(
    "address", [None, [], {"streetAddress": []}, {"addressCountry": []}, {"postalCode": 12345}]
)
def test_changed_address_structure_is_not_silently_discarded(address):
    with pytest.raises(SelectorError):
        event_record(json.dumps(sample(location={"address": address})), "going")


@pytest.mark.parametrize(
    "description,expected",
    [
        ("Meet at the entrance.\nBring a hat.", "Meet at the entrance.\nBring a hat."),
        (
            "<p>Meet &amp; greet</p><p>Bring <strong>snacks</strong>.<br>All welcome!</p>",
            "Meet & greet\nBring snacks.\nAll welcome!",
        ),
        ("<ul><li>First</li><li>Second</li></ul>", "First\nSecond"),
        (
            "<p>Visible</p><script>PRIVATE SCRIPT</script><style>PRIVATE STYLE</style><iframe>HIDDEN</iframe><p>End</p>",
            "Visible\nEnd",
        ),
        ("", ""),
    ],
)
def test_about_is_readable_plain_calendar_text(description, expected):
    assert (
        event_record(json.dumps(sample(description=description)), "going").description == expected
    )


def test_browser_refreshes_event_address_and_about_with_stable_calendar_uid(tmp_path):
    from icalendar import Calendar
    from couchsync.calendar import generate
    from couchsync.database import Database

    cfg = Config(
        tmp_path / "data", tmp_path / "config.toml", tmp_path / "logs", categories=["going"]
    )
    cfg.initialize()
    cfg.selectors.write_text(tomli_w.dumps(profile()))
    versions = [
        sample(
            description="<p>Original About</p>",
            location={"name": "Original venue", "address": "100 Example St"},
        ),
        sample(
            description="<p>Changed About</p>",
            location={
                "name": "Changed venue",
                "address": {"streetAddress": "200 Example St", "addressLocality": "Example City"},
            },
        ),
    ]
    versions.extend([versions[1], sample(description="", location={})])
    current = {"data": versions[0]}

    class Session:
        def load(self):
            return {"cookies": [], "origins": []}

        def save(self, state):
            pass

    async def check():
        db = Database(cfg.data / "details.db")
        try:
            async with browser() as context:

                async def serve_fixture(route):
                    if "my-events" in route.request.url:
                        body = '<button aria-label="Profile"></button><section role="tabpanel" aria-label="Going"><article data-couch-crash data-user-created><a href="/c/events/synthetic-gathering-Test123_ho">Fixture</a></article></section>'
                    else:
                        body = (
                            '<button aria-label="Profile"></button><script data-testid="hangout-json-ld" type="application/ld+json">'
                            + json.dumps(current["data"])
                            + "</script>"
                        )
                    await route.fulfill(status=200, content_type="text/html", body=body)

                await context.route("**/*", serve_fixture)

                @asynccontextmanager
                async def reuse(*args):
                    yield context

                uid = None
                with patch("couchsync.scraper.browser.browser", reuse):
                    for index, data in enumerate(versions):
                        current["data"] = data
                        records, metrics = await scrape(cfg, Session())
                        with db.transaction():
                            db.apply(records, metrics["complete"])
                        entry = Calendar.from_ical(generate(db.rows(), cfg)).walk("VEVENT")[0]
                        uid = uid or str(entry["uid"])
                        assert str(entry["uid"]) == uid
                        assert int(entry["sequence"]) == [0, 1, 1, 2][index]
                        expected = event_record(json.dumps(data), "going")
                        assert str(entry["location"]) == expected.location
                        assert str(entry["description"]) == expected.description
                        assert str(entry["url"]) == data["url"]
                        if index == 1:
                            assert "200 Example St" in str(entry["location"])
                            assert str(entry["description"]) == "Changed About"
        finally:
            db.close()

    asyncio.run(check())
