"""Local, reversible migration from exact-count bootstrap to event observations."""

from __future__ import annotations

import json
import re
import uuid
from copy import deepcopy
from urllib.parse import urlsplit

from filelock import FileLock

from .scraper.selectors import SelectorError, load, validate
from .util import atomic_write

LABELS = {"going": "Going", "interested": "Interested", "organized": "Organizing"}


def flat_profile(data: dict) -> bytes:
    """Serialize the narrow, flat selector profile without adding a runtime dependency."""

    def line(key, value):
        if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise SelectorError("Unsupported selector-profile key")
        if type(value) not in {str, bool, int}:
            raise SelectorError(
                "This profile has custom nested settings; automatic migration stopped"
            )
        return f"{key} = {json.dumps(value, ensure_ascii=False)}"

    lines = [line(k, v) for k, v in data.items() if k != "sources"]
    for source in data["sources"]:
        lines.extend(["", "[[sources]]"])
        lines.extend(line(k, v) for k, v in source.items())
    return ("\n".join(lines) + "\n").encode()


def upgrade_events(cfg) -> dict:
    with FileLock(str(cfg.data / "sync.lock"), timeout=0):
        original = cfg.selectors.read_bytes()
        adapter = load(cfg.selectors, cfg.categories)
        updated = deepcopy(adapter)
        for source in updated["sources"]:
            if (
                source["category"] not in LABELS
                or not source.get("event_json_ld")
                or urlsplit(source["url"]).path != "/c/events/my-events"
            ):
                raise SelectorError(
                    "Only the inspected Going/Interested/Organizing profile can be upgraded"
                )
            if "expected_count" not in source and source.get("completion") != "observed":
                raise SelectorError("This is not an inspected event bootstrap profile")
            source.pop("expected_count", None)
            source["completion"] = "observed"
            source["max_pages"] = 1
            source["tab_label"] = LABELS[source["category"]]
            source["detail_navigation"] = "same_tab"
        validate(updated, cfg.categories)
        if updated == adapter:
            return {
                "result": "already_upgraded",
                "coverage": "observed events only; list completeness unverified",
            }
        encoded = flat_profile(updated)
        if cfg.selectors.read_bytes() != original:
            raise SelectorError("Selectors changed while upgrading; no settings were replaced")
        backup = cfg.selectors.with_name(
            cfg.selectors.name + ".before-observations-" + uuid.uuid4().hex[:8] + ".bak"
        )
        atomic_write(backup, original)
        atomic_write(cfg.selectors, encoded)
        return {
            "result": "upgraded",
            "backup": str(backup),
            "coverage": "observed events only; missing entries retained",
            "note": "A successful live sync is still required before enabling the hourly worker",
        }
