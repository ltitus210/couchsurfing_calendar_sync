from __future__ import annotations

import re
from datetime import datetime

from ..models import Record
from .selectors import SelectorError


async def field(item, spec: dict) -> str:
    locator = item.locator(spec["selector"])
    count = await locator.count()
    if count != 1:
        if not count and spec.get("optional"):
            return ""
        raise SelectorError("Field selector must identify exactly one element")
    value = (
        await locator.get_attribute(spec["attribute"])
        if spec.get("attribute")
        else await locator.inner_text()
    )
    value = (value or "").strip()
    if spec.get("pattern"):
        match = re.fullmatch(spec["pattern"], value)
        if not match:
            raise SelectorError("Field pattern changed")
        value = match.group(1)
    if value and spec.get("format"):
        parsed = datetime.strptime(value, spec["format"])
        value = parsed.date().isoformat() if spec.get("date_only") else parsed.isoformat()
    return value


async def parse_item(item, source: dict) -> Record:
    values = {name: await field(item, spec) for name, spec in source["fields"].items()}
    raw = values.get("raw_status", "")
    if raw not in source["statuses"]:
        raise SelectorError("Unrecognized source status; update inspected status mapping")
    status = source["statuses"][raw]
    relationships = (
        [status]
        if source["kind"] == "event" and status in {"organizing", "going", "interested", "invited"}
        else []
    )
    record = Record(**values, kind=source["kind"], status=status, relationships=relationships)
    record.validate()
    return record
