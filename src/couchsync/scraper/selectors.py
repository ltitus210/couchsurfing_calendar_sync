from __future__ import annotations

import tomllib
from pathlib import Path

from ..util import https_url


class SelectorError(RuntimeError):
    pass


def load(path: Path, categories: list[str]) -> dict:
    if not path.exists():
        raise SelectorError(
            "Authenticated selectors not configured. Run scraper inspect; see docs/selectors.md"
        )
    data = tomllib.loads(path.read_text())
    if not data.get("validated_on") or not data.get("auth_marker"):
        raise SelectorError("Selectors must include validated_on and an authenticated-only marker")
    sources = data.get("sources", [])
    if set(s.get("category") for s in sources) != set(categories):
        raise SelectorError("Every enabled category needs an inspected source")
    if len(sources) != len(categories):
        raise SelectorError("Duplicate source category")
    for source in sources:
        https_url(source["url"], couchsurfing=True)
        if source.get("kind") != ("hosting" if source["category"] == "hosting" else "event"):
            raise SelectorError("Source kind/category mismatch")
        for key in ("container", "item"):
            if not source.get(key):
                raise SelectorError(f"Source missing required adapter setting: {key}")
        if "expected_count" in source:
            count = source["expected_count"]
            if type(count) is not int or count < 1:
                raise SelectorError("An inspected-count profile requires a positive exact count")
            if not source.get("event_json_ld") or source["kind"] != "event":
                raise SelectorError(
                    "Inspected counts are supported only for event first-sync profiles"
                )
            if source.get("max_pages", 1) != 1:
                raise SelectorError("Inspected counts cannot be mixed with guessed pagination")
        elif not source.get("end") or not source.get("empty"):
            raise SelectorError("Source requires explicit end and empty markers")
        if source.get("event_json_ld"):
            if (
                source["kind"] != "event"
                or not source.get("detail_link")
                or not source.get("detail_container")
            ):
                raise SelectorError("Structured event data requires an event detail-page scope")
        elif not {"source_id", "title", "raw_status", "start", "end"} <= set(
            source.get("fields", {})
        ) or not source.get("statuses"):
            raise SelectorError("Source fields missing identifiers, status, or dates")
        if source["kind"] == "hosting" and not source.get("incoming_marker"):
            raise SelectorError("Hosting requires an incoming-only scope marker")
    return data
