from __future__ import annotations

import tomllib
from pathlib import Path

from ..util import https_url


class SelectorError(RuntimeError):
    pass


def load(path: Path, categories: list[str]) -> dict:
    if not path.exists():
        if path.name == "selectors.toml":
            from .defaults import profile

            return validate(profile(categories), categories)
        raise SelectorError(
            "Custom selector file missing; restore it or use the built-in selectors.toml default"
        )
    return validate(tomllib.loads(path.read_text()), categories)


def validate(data: dict, categories: list[str]) -> dict:
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
        if source.get("adapter"):
            if (
                source["adapter"] != "messages_stays"
                or source["category"] != "hosting"
                or source.get("completion") != "observed"
                or type(source.get("max_items", 20)) is not int
                or not 1 <= source.get("max_items", 20) <= 100
            ):
                raise SelectorError("Invalid built-in hosting adapter settings")
            continue
        for key in ("container", "item"):
            if not source.get(key):
                raise SelectorError(f"Source missing required adapter setting: {key}")
        if source.get("completion") not in {None, "observed"}:
            raise SelectorError("Unknown completion policy")
        if source.get("completion") == "observed":
            if (
                not source.get("event_json_ld")
                or source["kind"] != "event"
                or "expected_count" in source
            ):
                raise SelectorError(
                    "Observed-event mode requires structured events without fixed counts"
                )
            if any(
                not (s.get("event_json_ld") and s.get("kind") == "event")
                and s.get("adapter") != "messages_stays"
                for s in sources
            ):
                raise SelectorError(
                    "Observed mode requires structured events or the guarded incoming-stay adapter"
                )
        if source.get("detail_navigation") not in {None, "same_tab"}:
            raise SelectorError("Unknown detail navigation mode")
        if source.get("detail_navigation") and not source.get("event_json_ld"):
            raise SelectorError("Same-tab navigation requires structured event identity checks")
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
        elif source.get("completion") != "observed" and (
            not source.get("end") or not source.get("empty")
        ):
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
