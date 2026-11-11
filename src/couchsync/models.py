from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from zoneinfo import ZoneInfo

from .util import clean, https_url

ACTIVE = {"organizing", "going", "interested", "invited", "pending", "confirmed"}
INACTIVE = {"declined", "withdrawn", "canceled", "expired", "completed"}
PRECEDENCE = ["organizing", "going", "interested", "invited"]


@dataclass
class Record:
    source_id: str
    kind: str
    title: str
    start: str = ""
    end: str = ""
    timezone: str = ""
    status: str = ""
    raw_status: str = ""
    relationships: list[str] = field(default_factory=list)
    url: str = ""
    location: str = ""
    description: str = ""
    direction: str = "incoming"

    @property
    def key(self) -> str:
        # Preserve existing incoming/event keys while separating outgoing stays.
        kind = "stay" if self.kind == "hosting" and self.direction == "outgoing" else self.kind
        return f"{kind}:{self.source_id}"

    def validate(self) -> None:
        if self.kind not in {"event", "hosting"} or not self.source_id or len(self.source_id) > 200:
            raise ValueError("Invalid source identifier/type")
        if self.status not in ACTIVE | INACTIVE:
            raise ValueError("Unknown source status")
        if set(self.relationships) - ACTIVE:
            raise ValueError("Unknown relationship")
        if self.kind == "hosting" and self.direction not in {"incoming", "outgoing"}:
            raise ValueError("Stay direction must be incoming or outgoing")
        if self.kind == "event" and self.status in {"pending", "confirmed"}:
            raise ValueError("Hosting status on event")
        if self.kind == "hosting" and self.status in {
            "organizing",
            "going",
            "interested",
            "invited",
        }:
            raise ValueError("Event status on hosting request")
        if self.url:
            https_url(self.url, couchsurfing=True)
        for name in ("title", "description", "location", "raw_status"):
            setattr(self, name, clean(getattr(self, name)))
        self.relationships = sorted(set(self.relationships))
        if self.start and self.end:
            start, end = self.dates()
            if end < start or (self.kind == "event" and end == start):
                raise ValueError("Invalid date interval")

    def dates(self) -> tuple[date | datetime, date | datetime]:
        if self.kind == "hosting":
            return date.fromisoformat(self.start), date.fromisoformat(self.end)

        def parse(value: str) -> datetime:
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                if not self.timezone:
                    raise ValueError("Event needs an explicit offset or IANA timezone")
                zone = ZoneInfo(self.timezone)
                first, second = dt.replace(tzinfo=zone, fold=0), dt.replace(tzinfo=zone, fold=1)
                if first.utcoffset() != second.utcoffset():
                    raise ValueError(
                        "Ambiguous/nonexistent local time requires explicit UTC offset"
                    )
                dt = first
            return dt

        return parse(self.start), parse(self.end)

    def payload(self) -> str:
        return json.dumps(asdict(self), sort_keys=True, ensure_ascii=False)

    def digest(self) -> str:
        return hashlib.sha256(self.payload().encode()).hexdigest()


def deduplicate(records: list[Record]) -> list[Record]:
    merged: dict[str, Record] = {}
    for record in records:
        record.validate()
        previous = merged.get(record.key)
        if previous:
            # Conflicting dates/details or explicit cancellation require inspection.
            if any(
                getattr(previous, k) != getattr(record, k)
                for k in ("start", "end", "title", "timezone")
            ):
                raise ValueError("Conflicting duplicate record details")
            if (previous.status in INACTIVE) != (record.status in INACTIVE):
                raise ValueError("Conflicting active/canceled record")
            if record.kind == "hosting" and previous.status != record.status:
                raise ValueError("Conflicting hosting status")
            relationships = set(previous.relationships + record.relationships)
            if record.kind == "event" and record.status in ACTIVE:
                relationships.update((previous.status, record.status))
                record.status = next(s for s in PRECEDENCE if s in relationships)
            record.relationships = sorted(relationships)
        merged[record.key] = record
    return list(merged.values())
