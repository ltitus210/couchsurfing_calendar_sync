from dataclasses import replace
from datetime import date

import pytest
from cryptography.fernet import InvalidToken
from icalendar import Calendar

from couchsync.calendar import generate
from couchsync.config import Config
from couchsync.database import Database
from couchsync.models import Record, deduplicate
from couchsync.secrets import Session
from couchsync.util import https_url


@pytest.fixture
def cfg(tmp_path):
    return Config(tmp_path / "data", tmp_path / "config.toml", tmp_path / "logs")


@pytest.fixture
def db(tmp_path):
    result = Database(tmp_path / "state" / "test.db")
    yield result
    result.close()


def event(status="interested", **kwargs):
    return Record(
        "42",
        "event",
        "Café, friends; \\ music\nUnicode 🎉",
        "2026-12-01T18:00:00+01:00",
        "2026-12-01T20:00:00+01:00",
        status=status,
        raw_status=status,
        relationships=[status] if status not in {"declined", "canceled"} else [],
        **kwargs,
    )


def apply(db, records):
    with db.transaction():
        db.apply(records, True)


def components(db, cfg, feed="all"):
    data = generate(db.rows(), cfg, feed)
    assert b"\r\n" in data
    assert all(len(line) <= 75 for line in data.split(b"\r\n"))
    return Calendar.from_ical(data).walk("VEVENT")


@pytest.mark.parametrize(
    "status,busy",
    [("organizing", True), ("going", True), ("interested", False), ("invited", False)],
)
def test_rsvp_availability(db, cfg, status, busy):
    apply(db, [event(status)])
    item = components(db, cfg)[0]
    assert str(item["transp"]) == ("OPAQUE" if busy else "TRANSPARENT")
    assert str(item["status"]) == "CONFIRMED"
    assert str(item["x-couchsync-status"]) == status


def test_transitions_uid_sequence_idempotence(db, cfg):
    uid = None
    for n, status in enumerate(["invited", "interested", "going", "interested", "declined"]):
        apply(db, [event(status)])
        item = components(db, cfg)[0]
        uid = uid or str(item["uid"])
        assert str(item["uid"]) == uid
        assert int(item["sequence"]) == n
    before = db.rows()
    apply(db, [event("declined")])
    assert db.rows()[0]["modified"] == before[0]["modified"]
    assert db.rows()[0]["sequence"] == 4
    assert str(components(db, cfg)[0]["status"]) == "CANCELLED"


def test_organizer_dedup_keeps_attendance():
    records = deduplicate([event("going"), event("organizing")])
    assert len(records) == 1
    assert records[0].status == "organizing"
    assert records[0].relationships == ["going", "organizing"]
    with pytest.raises(ValueError):
        deduplicate([event(), replace(event(), end="2026-12-02T20:00:00+01:00")])


@pytest.mark.parametrize(
    "reason", ["authentication", "pagination", "selector", "network", "rate_limit"]
)
def test_incomplete_preserves_records(db, reason):
    apply(db, [event()])
    before = db.rows()
    with pytest.raises(ValueError), db.transaction():
        db.apply([], False)
    assert db.rows() == before
    apply(db, [])
    assert db.rows() == before  # Missing is not verified cancellation.


def test_mass_cancellation_rolls_back(db):
    records = [replace(event("going"), source_id=str(n)) for n in range(4)]
    apply(db, records)
    before = db.rows()
    with pytest.raises(ValueError), db.transaction():
        db.apply([replace(r, status="canceled", relationships=[]) for r in records], True)
    assert db.rows() == before


def test_hosting_pending_confirmed_and_dates(db, cfg):
    request = Record(
        "stay-1",
        "hosting",
        "SECRET GUEST",
        "2026-12-04",
        "2026-12-07",
        status="pending",
        raw_status="Awaiting confirmation",
        url="https://www.couchsurfing.com/",
        description="SECRET MESSAGE",
        location="SECRET ADDRESS",
    )
    apply(db, [request])
    item = components(db, cfg)[0]
    uid = item["uid"]
    assert item.decoded("dtstart") == date(2026, 12, 4)
    assert item.decoded("dtend") == date(2026, 12, 7)
    assert str(item["transp"]) == "TRANSPARENT"
    assert b"SECRET" not in generate(db.rows(), cfg)
    apply(db, [replace(request, status="confirmed")])
    item = components(db, cfg)[0]
    assert item["uid"] == uid and int(item["sequence"]) == 1
    assert str(item["transp"]) == "OPAQUE"
    apply(db, [replace(request, status="confirmed", end=request.start)])
    assert components(db, cfg)[0].decoded("dtend") == date(2026, 12, 5)
    apply(db, [replace(request, end="")])
    assert components(db, cfg) == []
    assert len(db.rows()) == 1


@pytest.mark.parametrize("mode", ["limited", "generic", "busy", "private"])
def test_privacy_no_metadata_leaks(db, cfg, mode):
    cfg.event_privacy = mode
    record = replace(
        event(),
        title="SECRET TITLE",
        location="SECRET ADDRESS",
        description="SECRET DESCRIPTION",
        source_id="SECRET ID",
        url="https://www.couchsurfing.com/?secret=SECRET",
    )
    apply(db, [record])
    data = generate(db.rows(), cfg)
    if mode != "limited":
        assert b"SECRET" not in data
    else:
        assert b"SECRET ADDRESS" not in data and b"SECRET DESCRIPTION" not in data
    if mode in {"busy", "private"}:
        assert b"X-COUCHSYNC" not in data and b"CATEGORIES" not in data


def test_timezones_unicode_round_trip(db, cfg):
    cfg.event_privacy = "full"
    record = replace(event(), title="🎉" * 100)
    apply(db, [record])
    item = components(db, cfg)[0]
    assert str(item["summary"]).endswith(record.title)
    assert item.decoded("dtstart").hour == 17
    with pytest.raises(ValueError):
        replace(
            event(),
            start="2026-11-01T01:30:00",
            end="2026-11-01T03:00:00",
            timezone="America/New_York",
        ).validate()
    with pytest.raises(ValueError):
        replace(
            event(),
            start="2026-03-08T02:30:00",
            end="2026-03-08T04:00:00",
            timezone="America/New_York",
        ).validate()


def test_backups(db, tmp_path):
    apply(db, [event()])
    target = tmp_path / "private" / "backup.db"
    db.backup(target)
    other = Database(target)
    assert other.rows() == db.rows()
    other.close()
    with pytest.raises(ValueError):
        db.backup(target)


class MemoryVault:
    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value):
        self.values[key] = value

    def delete(self, key):
        self.values.pop(key, None)


def test_session_encrypted_tamper_logout(tmp_path):
    vault = MemoryVault()
    session = Session(tmp_path / "session.enc", vault)
    state = {"cookies": [{"name": "secret", "value": "COOKIE-PRIVATE"}]}
    session.save(state)
    assert session.load() == state
    assert b"COOKIE-PRIVATE" not in session.path.read_bytes()
    ciphertext = session.path.read_bytes()
    session.path.write_bytes(ciphertext[:40] + b"X" + ciphertext[41:])
    with pytest.raises(InvalidToken):
        session.load()
    session.clear()
    assert not session.path.exists() and not vault.values


@pytest.mark.parametrize(
    "url",
    [
        "http://www.couchsurfing.com",
        "https://evil.example/",
        "https://user:pw@www.couchsurfing.com",
        "https://www.couchsurfing.com.evil.example/",
    ],
)
def test_reject_unsafe_navigation(url):
    with pytest.raises(ValueError):
        https_url(url, couchsurfing=True)


def test_config_validation(cfg):
    cfg.interval = 1
    with pytest.raises(ValueError):
        cfg.validate()


def test_separate_feed_privacy_and_filtering(db, cfg):
    cfg.feeds = {
        "all": {},
        "organized": {},
        "events": {},
        "hosting": {},
        "confirmed": {"hosting_privacy": "private"},
    }
    stay = Record("stay", "hosting", "PRIVATE NAME", "2026-12-01", "2026-12-03", status="confirmed")
    apply(db, [event("organizing"), stay])
    assert len(components(db, cfg, "all")) == 2
    assert len(components(db, cfg, "organized")) == 1
    assert len(components(db, cfg, "events")) == 1
    assert len(components(db, cfg, "hosting")) == 1
    item = components(db, cfg, "confirmed")[0]
    assert str(item["summary"]) == "Busy"
    assert "x-couchsync-status" not in item


def test_insecure_keyring_backend_rejected(monkeypatch):
    from couchsync.secrets import Vault
    import keyring

    monkeypatch.setattr(keyring, "get_keyring", lambda: object())
    with pytest.raises(RuntimeError):
        Vault("test")
