from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from icalendar import Calendar, Event

from .config import Config
from .models import Record


def generate(rows: list[dict], cfg: Config, feed: str = "all") -> bytes:
    cal = Calendar()
    cal.add("prodid", "-//Couchsync//Private calendars//EN")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", cfg.name)
    settings = cfg.feeds.get(feed, {})
    cutoff = datetime.now(UTC).date() - timedelta(days=cfg.retention_days)
    for row in rows:
        r = Record(**json.loads(row["payload"]))
        if not r.start or not r.end:
            continue  # Still retained in database diagnostics; no invented dates.
        if feed == "organized" and "organizing" not in r.relationships and r.status != "organizing":
            continue
        if feed == "events" and r.kind != "event":
            continue
        if feed == "hosting" and r.kind != "hosting":
            continue
        if feed == "confirmed" and (r.kind != "hosting" or r.status != "confirmed"):
            continue
        start, end = r.dates()
        end_day = end.date() if isinstance(end, datetime) else end
        if end_day < cutoff:
            continue
        if r.kind == "hosting" and end == start:
            end += timedelta(days=1)  # Explicit same-day stays occupy that day.
        # UTC avoids floating times and client-dependent timezone database differences.
        if isinstance(start, datetime):
            start, end = start.astimezone(UTC), end.astimezone(UTC)
        privacy = settings.get(
            f"{r.kind if r.kind == 'hosting' else 'event'}_privacy",
            cfg.hosting_privacy if r.kind == "hosting" else cfg.event_privacy,
        )
        prefix = cfg.prefixes.get(r.status, f"[{r.status.title()}]")
        title = r.title
        if r.kind == "hosting":
            title = (
                f"Couchsurfing: Hosting {r.title}"
                if privacy == "full"
                else "Couchsurfing: Hosting guest"
            )
        elif privacy in {"generic", "limited"}:
            title = r.title if privacy == "limited" else "Couchsurfing event"
        if privacy in {"busy", "private"}:
            title = "Busy"
        else:
            title = f"{prefix} {title}"
        ev = Event()
        ev.add("uid", row["uid"])
        ev.add("dtstart", start)
        ev.add("dtend", end)
        stamp = datetime.fromisoformat(row["modified"])
        ev.add("dtstamp", stamp)
        ev.add("last-modified", stamp)
        ev.add("sequence", row["sequence"])
        ev.add("summary", title)
        ev.add("status", "CANCELLED" if row["canceled"] else "CONFIRMED")
        ev.add("transp", "OPAQUE" if cfg.busy.get(r.status, False) else "TRANSPARENT")
        ev.add("class", "PRIVATE")
        if privacy not in {"busy", "private"}:
            ev.add("categories", [r.kind])
            ev.add("x-couchsync-status", r.status)
            ev.add("x-couchsync-relationships", ",".join(r.relationships))
        if privacy == "full":
            ev.add("description", r.description)
            ev.add("location", r.location)
            if r.url:
                ev.add("url", r.url)
        cal.add_component(ev)
    return cal.to_ical()
