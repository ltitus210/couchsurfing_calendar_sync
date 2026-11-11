"""Conservative read-only adapter for the observed Messages / Stays interface.

Incoming panel labels are explicit shared-layout assumptions, not live-confirmed fixtures.
Unknown panels are reported, never treated as proof that previous stays disappeared.
"""

from __future__ import annotations

import asyncio
import re
from datetime import date
from urllib.parse import urljoin, urlsplit

from playwright.async_api import TimeoutError as BrowserTimeout

from ..models import Record, deduplicate
from ..util import https_url
from . import traffic
from .selectors import SelectorError

MONTHS = {
    name: i
    for i, name in enumerate(
        (
            "january",
            "february",
            "march",
            "april",
            "may",
            "june",
            "july",
            "august",
            "september",
            "october",
            "november",
            "december",
        ),
        1,
    )
}
DATE_PART = re.compile(r"\b(" + "|".join(MONTHS) + r")\s+(\d{1,2})(?:,?\s+(\d{4}))?\b", re.I)
STAY_LINK = re.compile(r"^(Pending|Confirmed|Upcoming|Accepted) Stay$", re.I)


class LayoutUnavailable(Exception):
    pass


def stay_dates(text: str) -> tuple[str, str]:
    """Parse displayed English dates; require a source year, never use today's year."""
    matches = DATE_PART.findall(text)
    if not matches or len(matches) > 2:
        return "", ""
    values = [
        (MONTHS[m.lower()], int(day), int(year) if year else None) for m, day, year in matches
    ]
    years = [y for _, _, y in values if y is not None]
    if not years:
        return "", ""
    if len(values) == 1:
        m, d, y = values[0]
        try:
            return date(y or years[0], m, d).isoformat(), ""
        except ValueError:
            return "", ""
    (am, ad, ay), (dm, dd, dy) = values
    if ay is None:
        ay = dy - int((am, ad) > (dm, dd))
    if dy is None:
        dy = ay + int((dm, dd) < (am, ad))
    try:
        arrival, departure = date(ay, am, ad), date(dy, dm, dd)
        if departure < arrival:
            return "", ""
        return arrival.isoformat(), departure.isoformat()
    except ValueError:
        return "", ""


def incoming_status(
    heading: str, text: str, banner: str, accept: bool, decline: bool, outgoing_trip: bool
) -> str | None:
    if re.search(r"\byour request\b", heading, re.I) or outgoing_trip:
        return None
    if accept and decline:
        return "pending"
    host = re.search(
        r"\b(your guests?|you[’']re hosting|you are hosting|hosting (request|stay|arrangement))\b",
        heading + " " + text,
        re.I,
    )
    if not host:
        return None
    if re.fullmatch(r"(Confirmed|Upcoming) Stay", banner, re.I):
        return "confirmed"
    if re.search(r"pending|awaiting|waiting.*confirm|accepted", banner + " " + text, re.I):
        return "pending"
    return None


async def request_panel(page):
    for heading in await page.get_by_role("heading", level=4).all():
        # Never use headings from a conversation/message list as stay metadata.
        if await heading.locator(
            "xpath=ancestor::*[@role='list' or @role='log' or self::ul or self::ol]"
        ).count():
            continue
        title = (await heading.inner_text()).strip()
        if not re.search(r"request|guest|stay|hosting", title, re.I):
            continue
        node = heading
        for _ in range(10):
            node = node.locator("xpath=..")
            if not await node.count():
                break
            if (
                await node.get_by_role("textbox").count()
                or await node.locator("[role=log], [role=list], ul, ol").count()
            ):
                break
            if (
                await node.get_by_text("When", exact=True).count()
                and await node.get_by_text("Travelers", exact=True).count()
            ):
                return node, title
    raise LayoutUnavailable()


async def when_text(panel) -> str:
    label = panel.get_by_text("When", exact=True)
    if await label.count() != 1:
        return ""
    node = label
    for _ in range(3):
        node = node.locator("xpath=..")
        text = await node.inner_text()
        if DATE_PART.search(text):
            return text[:1000]
    return ""


async def parse_stay(page, banner: str) -> Record | None:
    await page.get_by_role("heading", level=4).first.wait_for(state="visible")
    await page.get_by_text("When", exact=True).first.wait_for(state="visible")
    panel, heading = await request_panel(page)
    if re.search(r"\byour request\b", heading, re.I):
        return None
    outgoing = bool(await panel.get_by_role("button", name="View Your Trip", exact=True).count())
    accept = bool(
        await panel.get_by_role("button", name=re.compile(r"^Accept (Stay|Request)$", re.I)).count()
    )
    decline = bool(
        await panel.get_by_role(
            "button", name=re.compile(r"^Decline( Stay| Request)?$", re.I)
        ).count()
    )
    # Classify only dedicated metadata/control labels, never conversation text.
    status = incoming_status(heading, "", banner, accept, decline, outgoing)
    if status is None:
        raise LayoutUnavailable()
    https_url(page.url, couchsurfing=True)
    match = re.fullmatch(r"/c/chat/[^/]+/stays/([A-Za-z0-9_]+)", urlsplit(page.url).path)
    if not match:
        raise LayoutUnavailable()
    start, end = stay_dates(await when_text(panel))
    title = await page.title()
    suffix = " - Messages - Couchsurfing"
    guest = title[: -len(suffix)].strip() if title.endswith(suffix) else "Guest"
    record = Record(
        source_id=match.group(1),
        kind="hosting",
        title=guest or "Guest",
        start=start,
        end=end,
        status=status,
        raw_status=banner,
        url=urlsplit(page.url)._replace(query="", fragment="").geturl(),
        direction="incoming",
    )
    record.validate()
    return record


async def sidebar(page):
    search = page.get_by_role("searchbox").first
    if not await search.count():
        raise LayoutUnavailable()
    node = search
    for _ in range(12):
        node = node.locator("xpath=..")
        if not await node.count():
            break
        toggle = node.get_by_role("button", name="Stays", exact=True).and_(
            page.locator("[aria-pressed]")
        )
        if (
            await toggle.count() == 1
            and await node.get_by_role("button", name="Pending", exact=True).count() == 1
            and await node.get_by_role("button", name="Confirmed", exact=True).count() == 1
        ):
            return node, toggle
    raise LayoutUnavailable()


async def collect_hosting(page, source, auth_marker):
    from .browser import navigate

    records = []
    unknown = 0
    outgoing = 0
    try:
        await navigate(page, source["url"])
        await page.locator(auth_marker).wait_for(state="visible")
        await page.get_by_role("button", name="Messages", exact=True).click()
        await page.get_by_role("heading", name="Messages", exact=True).first.wait_for(
            state="visible"
        )
        chats = set()
        for tab_name in ("Chats", "Chat Requests"):
            tab = page.get_by_role("tab", name=tab_name, exact=True)
            if not await tab.count():
                continue
            await tab.click()
            try:
                area, toggle = await sidebar(page)
            except LayoutUnavailable:
                unknown += 1
                continue
            if await toggle.get_attribute("aria-pressed") != "true":
                await toggle.click()
            for state in ("Pending", "Confirmed"):
                if traffic.restricted(page.context):
                    raise SelectorError("Account access restriction encountered; stopping")
                await area.get_by_role("button", name=state, exact=True).click()
                await asyncio.sleep(1)
                for link in await area.locator("a[href]").all():
                    url = urljoin(page.url, await link.get_attribute("href") or "")
                    parts = urlsplit(url)
                    if parts.hostname in {
                        "www.couchsurfing.com",
                        "couchsurfing.com",
                    } and re.fullmatch(r"/c/chat/[^/]+", parts.path):
                        chats.add(parts._replace(query="", fragment="").geturl())
        limit = source.get("max_items", 20)
        capped = len(chats) > limit
        for url in sorted(chats)[:limit]:
            if traffic.restricted(page.context):
                raise SelectorError("Account access restriction encountered; stopping")
            await asyncio.sleep(1)
            await navigate(page, url)
            await page.locator(auth_marker).wait_for(state="visible")
            banners = page.get_by_role("link", name=STAY_LINK)
            chosen = None
            for candidate in await banners.all():
                if await candidate.locator(
                    "xpath=ancestor::*[@role='list' or @role='log' or self::ul or self::ol]"
                ).count():
                    continue
                target = urljoin(page.url, await candidate.get_attribute("href") or "")
                if urlsplit(target).path.startswith(urlsplit(url).path + "/stays/"):
                    chosen = candidate
                    break
            if chosen is None:
                unknown += 1
                continue
            banner = (await chosen.inner_text()).strip()
            target = urljoin(page.url, await chosen.get_attribute("href") or "")
            https_url(target, couchsurfing=True)
            await chosen.click()
            await page.wait_for_url(lambda current: urlsplit(current).path == urlsplit(target).path)
            try:
                record = await parse_stay(page, banner)
            except LayoutUnavailable:
                unknown += 1
                continue
            if record is None:
                outgoing += 1
            else:
                records.append(record)
        note = "Assumed shared hosting layout; incoming direction checked; full-list coverage unverified"
        if outgoing:
            note += f"; {outgoing} outgoing requests excluded"
        if unknown:
            note += f"; {unknown} unrecognized stay panels skipped"
        if capped:
            note += f"; limited to {limit} observed chats"
        if any(not r.start or not r.end for r in records):
            note += "; undated requests retained in diagnostics, omitted from calendar"
        return deduplicate(records), note
    except (LayoutUnavailable, BrowserTimeout):
        if traffic.restricted(page.context):
            raise SelectorError("Account access restriction encountered; stopping") from None
        if not await page.locator(auth_marker).is_visible():
            raise SelectorError(
                "Authenticated account context unavailable; previous data preserved"
            ) from None
        return (
            records,
            "Hosting layout not recognized; previous stays retained; event sources can still update",
        )
