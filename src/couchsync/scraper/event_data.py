"""Read the Event JSON-LD observed in authenticated Couchsurfing event pages.

Only structured fields needed by the calendar are selected. No scripts are executed.
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
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


class AboutText(HTMLParser):
    """Convert event About markup to readable calendar text without executing HTML."""

    BLOCKS = {"p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "blockquote"}
    HIDDEN = {"script", "style", "iframe"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = []

    def handle_starttag(self, tag, attrs):
        if tag in self.HIDDEN:
            self.hidden.append(tag)
        elif not self.hidden and tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if self.hidden:
            if tag == self.hidden[-1]:
                self.hidden.pop()
        elif tag in self.BLOCKS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def about_text(value: str) -> str:
    parser = AboutText()
    parser.feed(value)
    parser.close()
    lines = [line.strip() for line in "".join(parser.parts).splitlines()]
    return "\n".join(line for line in lines if line)


def event_location(location: dict) -> str:
    """Use only the venue/address supplied by the event; never infer or geocode it."""
    if not isinstance(location, dict) or not isinstance(location.get("name", ""), str):
        raise SelectorError("Event location structure changed")
    name = location.get("name", "").strip()
    address = location.get("address", "")
    if isinstance(address, str):
        parts = [name, address.strip()]
    elif isinstance(address, dict):
        fields = {}
        for key in ("streetAddress", "addressLocality", "addressRegion", "postalCode"):
            value = address.get(key, "")
            if not isinstance(value, str):
                raise SelectorError("Event postal address structure changed")
            fields[key] = value.strip()
        country = address.get("addressCountry", "")
        if isinstance(country, dict):
            country = country.get("name", "")
        if not isinstance(country, str):
            raise SelectorError("Event postal country structure changed")
        region_postal = " ".join(filter(None, [fields["addressRegion"], fields["postalCode"]]))
        city = ", ".join(filter(None, [fields["addressLocality"], region_postal]))
        parts = [name, fields["streetAddress"], city, country.strip()]
    else:
        raise SelectorError("Event postal address structure changed")
    # A venue name can already be its street address. Avoid identical repeated lines.
    result = []
    seen = set()
    for part in parts:
        normalized = " ".join(part.split()).casefold()
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(part)
    return "\n".join(result)


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
    location = event_location(data.get("location", {}))
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
        description=about_text(description),
        location=location,
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
