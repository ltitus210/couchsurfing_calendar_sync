"""Read the Event JSON-LD observed in authenticated Couchsurfing event pages.

Only structured fields needed by the calendar are selected. No scripts are executed.
"""

from __future__ import annotations

import json
import re
from urllib.parse import urlsplit

from ..models import Record
from ..util import https_url
from .selectors import SelectorError

RELATIONSHIPS = {
    "organized": "organizing",
    "going": "going",
    "interested": "interested",
    "invited": "invited",
}


def event_record(raw: str, category: str) -> Record:
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        raise SelectorError("Event JSON-LD is invalid") from None
    if not isinstance(data, dict) or data.get("@type") != "Event":
        raise SelectorError("Expected exactly one structured Event")
    if category not in RELATIONSHIPS:
        raise SelectorError("Unsupported event relationship")
    url = data.get("url")
    if not isinstance(url, str):
        raise SelectorError("Event canonical URL missing")
    try:
        https_url(url, couchsurfing=True)
    except ValueError:
        raise SelectorError("Event canonical URL is not a Couchsurfing HTTPS URL") from None
    parsed = urlsplit(url)
    match = re.fullmatch(r"/c/events/[^/]+-([A-Za-z0-9]+_ho)", parsed.path)
    if not match or parsed.query:
        raise SelectorError("Event URL no longer exposes the inspected stable identifier")
    event_status = data.get("eventStatus")
    if event_status not in {
        "https://schema.org/EventScheduled",
        "https://schema.org/EventCancelled",
    }:
        raise SelectorError("Event lifecycle status needs inspection")
    for key in ("name", "startDate", "endDate"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise SelectorError("Structured event title or dates missing")
    relationship = RELATIONSHIPS[category]
    canceled = event_status.endswith("EventCancelled")
    location = data.get("location", {})
    if not isinstance(location, dict) or not isinstance(location.get("name", ""), str):
        raise SelectorError("Event location structure changed")
    description = data.get("description", "")
    if not isinstance(description, str):
        raise SelectorError("Event description structure changed")
    record = Record(
        source_id=match.group(1),
        kind="event",
        title=data["name"].strip(),
        start=data["startDate"],
        end=data["endDate"],
        status="canceled" if canceled else relationship,
        raw_status=f"{relationship}; {event_status}",
        relationships=[] if canceled else [relationship],
        url=url,
        description=description,
        location=location.get("name", ""),
    )
    try:
        record.validate()
        # Do not infer a timezone from the machine when source dates lose their offset.
        from datetime import datetime

        if any(datetime.fromisoformat(v).tzinfo is None for v in (record.start, record.end)):
            raise ValueError("Missing offset")
    except (ValueError, TypeError):
        raise SelectorError(
            "Structured event dates are invalid or lack an explicit offset"
        ) from None
    return record


def relationship_record(record: Record, category: str) -> Record:
    """Reuse verified event details for another observed list membership."""
    from dataclasses import replace

    if record.status == "canceled":
        return replace(record, relationships=[])
    if category not in RELATIONSHIPS:
        raise SelectorError("Unsupported event relationship")
    relationship = RELATIONSHIPS[category]
    lifecycle = record.raw_status.split("; ", 1)[-1]
    return replace(
        record,
        status=relationship,
        relationships=[relationship],
        raw_status=f"{relationship}; {lifecycle}",
    )
