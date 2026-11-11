from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager

from playwright.async_api import async_playwright, expect

from . import traffic

from ..models import deduplicate
from ..util import https_url
from .parser import parse_item
from .selectors import SelectorError, load


@asynccontextmanager
async def browser(state: dict | None = None, visible: bool = False):
    async with async_playwright() as pw:
        instance = await pw.chromium.launch(headless=not visible, chromium_sandbox=True)
        try:
            options = {"storage_state": state, "accept_downloads": False}
            if not visible:
                options["service_workers"] = "block"
            context = await instance.new_context(**options)
            context.set_default_timeout(15000)
            if not visible:
                await traffic.install(context)
            yield context
        finally:
            await instance.close()


async def login(session) -> None:
    # Explicit user-driven flow; no password collection and no plaintext state file.
    async with browser(visible=True) as context:
        page = await context.new_page()
        await page.goto("https://www.couchsurfing.com/", wait_until="domcontentloaded")
        answer = await asyncio.to_thread(input, "Log in in the browser. Type SAVE when complete: ")
        if answer.strip() != "SAVE":
            raise RuntimeError("Login not saved")
        https_url(page.url, couchsurfing=True)
        await session_save(session, context)


async def session_save(session, context) -> None:
    session.save(await context.storage_state(indexed_db=True))


async def inspect(session) -> None:
    async with browser(session.load(), visible=True) as context:
        page = await context.new_page()
        await page.goto("https://www.couchsurfing.com/", wait_until="domcontentloaded")
        print(
            "Chrome is paused for inspection. Browse normally; this does not configure the scraper.\n"
            "When finished, press Resume in Playwright Inspector to save the session and close Chrome.\n"
            "For first-sync setup see docs/event-first-sync.md. No raw captures are saved."
        )
        await page.pause()
        await session_save(session, context)


async def navigate(page, url: str) -> None:
    https_url(url, couchsurfing=True)
    for attempt in range(3):
        response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        https_url(page.url, couchsurfing=True)
        status = response.status if response else 0
        if status in {401, 403, 429}:
            raise SelectorError("Access blocked, rate limited, or login required; no retry")
        if 500 <= status <= 599 and attempt < 2:
            await asyncio.sleep(2 ** (attempt + 1))
            continue
        if status != 200:
            raise SelectorError("Page unavailable; existing data preserved")
        return


async def collect_page(page, source: dict, auth_marker: str, seen=None) -> list:
    await page.locator(auth_marker).wait_for(state="visible")
    await page.locator(source["container"]).wait_for(state="attached")
    if source.get("incoming_marker"):
        await page.locator(source["incoming_marker"]).wait_for(state="visible")
    # An inspected-count profile is a first-sync guard, not pagination discovery.
    items = page.locator(source["item"])
    if source.get("completion") == "observed":
        # Wait for a positive observation or a configured explicit empty marker.
        # Settling is not considered evidence that pagination has completed.
        deadline = time.monotonic() + 15
        while True:
            count = await items.count()
            empty = page.locator(source["empty"]).first if source.get("empty") else None
            empty_found = bool(empty is not None and await empty.is_visible())
            if empty_found:
                if count:
                    raise SelectorError("Event list shows both records and an empty-state marker")
                return []
            if count:
                break
            if time.monotonic() >= deadline:
                raise SelectorError(
                    "Event list did not show records or a recognized empty state; run scraper inspect if the layout changed"
                )
            await asyncio.sleep(0.2)
    if "expected_count" in source and await items.count() != source["expected_count"]:
        raise SelectorError(
            "Event count differs from the inspected first-sync profile; re-inspect the list"
        )
    if "expected_count" in source:
        await page.locator(source["container"]).wait_for(state="visible")
    if await items.count() == 0 and (
        not source.get("empty") or not await page.locator(source["empty"]).first.is_visible()
    ):
        raise SelectorError("Neither records nor explicit empty marker found")
    result = []
    for item in await items.all():
        if traffic.restricted(page.context):
            raise SelectorError("Account access restriction encountered; stopping")
        if not source.get("detail_link"):
            result.append(await parse_item(item, source))
            continue
        from urllib.parse import urljoin

        link = item.locator(source["detail_link"])
        if await link.count() != 1:
            raise SelectorError("Detail link selector changed")
        url = urljoin(page.url, await link.get_attribute("href") or "")
        https_url(url, couchsurfing=True)
        from urllib.parse import urlsplit

        cache_key = (
            urlsplit(url)._replace(query="", fragment="").geturl()
            if source.get("event_json_ld")
            else url
        )
        if seen is not None and cache_key in seen:
            record = seen[cache_key]
            if source.get("event_json_ld"):
                from .event_data import relationship_record

                record = relationship_record(record, source["category"])
            result.append(record)
            continue
        if source.get("detail_navigation") == "same_tab":
            record = await detail_in_same_tab(page, link, url, source, auth_marker)
            result.append(record)
            if seen is not None:
                seen[cache_key] = record
            continue
        detail = await page.context.new_page()
        try:
            await asyncio.sleep(1)
            await navigate(detail, url)
            await detail.locator(auth_marker).wait_for(state="visible")
            container = detail.locator(source["detail_container"])
            await container.wait_for(state="visible")
            record = await parse_item(container, source)
            result.append(record)
            if seen is not None:
                seen[cache_key] = record
        finally:
            await detail.close()
    return result


async def detail_in_same_tab(page, link, url, source, auth_marker):
    """Use ordinary event links and browser Back to preserve the loaded app shell."""
    from urllib.parse import urlsplit

    intended_path = urlsplit(url).path
    if not intended_path.startswith("/c/events/") or intended_path.endswith("my-events"):
        raise SelectorError("Expected a read-only event detail link")
    await asyncio.sleep(1)
    await link.click()
    await page.wait_for_url(lambda current: urlsplit(current).path == intended_path)
    https_url(page.url, couchsurfing=True)
    await page.locator(auth_marker).wait_for(state="visible")
    container = page.locator(source["detail_container"])
    await container.wait_for(state="visible")
    if source.get("event_json_ld"):
        # Script elements do not expose rendered innerText. Read textContent directly,
        # waiting for metadata identity rather than relying on a rendered-text assertion.
        import json
        from .event_data import event_record

        meta = container.locator(source["event_json_ld"])
        deadline = time.monotonic() + 15
        while True:
            raw = await meta.text_content() or ""
            try:
                candidate = json.loads(raw)
            except ValueError:
                candidate = None
            canonical = candidate.get("url") if isinstance(candidate, dict) else None
            if isinstance(canonical, str) and urlsplit(canonical).path == intended_path:
                record = event_record(raw, source["category"])
                break
            if time.monotonic() >= deadline:
                raise SelectorError("Event metadata did not match the selected detail page")
            await asyncio.sleep(0.1)
    else:
        record = await parse_item(container, source)
    if source.get("event_json_ld") and urlsplit(record.url).path != intended_path:
        raise SelectorError("Event detail identity differs from the selected link")
    await page.go_back(wait_until="domcontentloaded")
    https_url(page.url, couchsurfing=True)
    await page.locator(source["container"]).wait_for(state="visible")
    return record


async def open_source(page, source, auth_marker):
    from urllib.parse import urlsplit

    current, intended = urlsplit(page.url), urlsplit(source["url"])
    same_list = (current.scheme, current.netloc, current.path) == (
        intended.scheme,
        intended.netloc,
        intended.path,
    )
    if not same_list or not source.get("tab_label"):
        await navigate(page, source["url"])
    if source.get("tab_label"):
        await page.locator(auth_marker).wait_for(state="visible")
        # Wait for the known tab bar before deciding an optional view is absent.
        await page.get_by_role("tab", name="Going", exact=True).wait_for(state="visible")
        tab = page.get_by_role("tab", name=source["tab_label"], exact=True)
        if not await tab.count() and source.get("optional"):
            return False
        await tab.click()
        await expect(tab).to_have_attribute("aria-selected", "true", timeout=15000)
        await page.locator(source["container"]).wait_for(state="visible")
    return True


async def scrape(cfg, session) -> tuple[list, dict]:
    adapter = load(cfg.selectors, cfg.categories)
    started = time.monotonic()
    requests = 0
    records = []
    counts = {}
    source_notes = {}
    observed_only = any(s.get("completion") == "observed" for s in adapter["sources"])
    async with browser(session.load()) as context:

        def count_request(_):
            nonlocal requests
            requests += 1

        context.on("request", count_request)
        blocked = []

        def account_response(response):
            from urllib.parse import urlsplit

            if response.status in {401, 403, 429} and urlsplit(response.url).hostname in {
                "www.couchsurfing.com",
                "couchsurfing.com",
            }:
                blocked.append(True)

        context.on("response", account_response)
        page = await context.new_page()
        shared_details = {}
        for source in adapter["sources"]:
            if source.get("adapter") == "messages_stays":
                from .hosting import collect_hosting

                batch, note = await collect_hosting(page, source, adapter["auth_marker"])
                counts[source["category"]] = len(batch)
                if note:
                    source_notes[source["category"]] = note
                records.extend(batch)
                continue
            if not await open_source(page, source, adapter["auth_marker"]):
                counts[source["category"]] = 0
                source_notes[source["category"]] = (
                    "View not present in this layout; no absence-based changes made"
                )
                continue
            source_records = {}
            detail_seen = shared_details if source.get("event_json_ld") else {}
            finished = False
            for _ in range(source.get("max_pages", 50)):
                await asyncio.sleep(1)
                if blocked:
                    raise SelectorError("Account access restriction encountered; stopping")
                https_url(page.url, couchsurfing=True)
                batch = await collect_page(page, source, adapter["auth_marker"], detail_seen)
                if blocked:
                    raise SelectorError("Account access restriction encountered; stopping")
                for record in batch:
                    source_records[record.key] = record
                if source.get("completion") == "observed":
                    if len(source_records) != len(batch):
                        raise SelectorError("Observed event identities are not unique")
                    if await page.locator(source["item"]).count() != len(batch):
                        raise SelectorError("Event list changed while extracting details")
                    finished = True  # Observation batch verified; source completeness stays false.
                    break
                if "expected_count" in source:
                    if (
                        len(batch) != source["expected_count"]
                        or len(source_records) != source["expected_count"]
                    ):
                        raise SelectorError("Inspected event count or source identities changed")
                    if await page.locator(source["item"]).count() != source["expected_count"]:
                        raise SelectorError("Event list changed while extracting details")
                    finished = True
                    break
                if await page.locator(source["end"]).is_visible():
                    finished = True
                    break
                if source.get("next") and await page.locator(source["next"]).is_visible():
                    await page.locator(source["next"]).click()
                elif source.get("scroll"):
                    await page.locator(source["container"]).evaluate(
                        "el => el.scrollIntoView({block: 'end'})"
                    )
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                else:
                    raise SelectorError("Pagination not complete")
            if not finished:
                raise SelectorError("Pagination limit reached; refusing incomplete results")
            counts[source["category"]] = len(source_records)
            records.extend(source_records.values())
        measured = traffic.summary(context)
        await session_save(session, context)
    return deduplicate(records), {
        "requests": requests,
        **measured,
        "duration_seconds": round(time.monotonic() - started, 2),
        "sources": counts,
        "source_notes": source_notes,
        "layout": adapter.get("layout_version", "custom"),
        "complete": not observed_only,
        "observations_only": observed_only,
        "coverage": "verified observed records; full-list coverage unverified"
        if observed_only
        else (
            "inspected-count event lists"
            if any("expected_count" in s for s in adapter["sources"])
            else "explicit end markers"
        ),
    }
