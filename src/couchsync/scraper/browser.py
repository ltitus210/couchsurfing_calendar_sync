from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager

from playwright.async_api import async_playwright

from ..models import deduplicate
from ..util import https_url
from .parser import parse_item
from .selectors import SelectorError, load


@asynccontextmanager
async def browser(state: dict | None = None, visible: bool = False):
    async with async_playwright() as pw:
        instance = await pw.chromium.launch(headless=not visible, chromium_sandbox=True)
        try:
            context = await instance.new_context(storage_state=state, accept_downloads=False)
            context.set_default_timeout(15000)
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
            "Inspect account lists and detail pages in Playwright Inspector. No raw captures are saved."
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
    items = page.locator(source["item"])
    if await items.count() == 0 and not await page.locator(source["empty"]).is_visible():
        raise SelectorError("Neither records nor explicit empty marker found")
    result = []
    for item in await items.all():
        if not source.get("detail_link"):
            result.append(await parse_item(item, source))
            continue
        from urllib.parse import urljoin

        link = item.locator(source["detail_link"])
        if await link.count() != 1:
            raise SelectorError("Detail link selector changed")
        url = urljoin(page.url, await link.get_attribute("href") or "")
        https_url(url, couchsurfing=True)
        if seen is not None and url in seen:
            result.append(seen[url])
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
                seen[url] = record
        finally:
            await detail.close()
    return result


async def scrape(cfg, session) -> tuple[list, dict]:
    adapter = load(cfg.selectors, cfg.categories)
    started = time.monotonic()
    requests = 0
    records = []
    counts = {}
    async with browser(session.load()) as context:

        def count_request(_):
            nonlocal requests
            requests += 1

        context.on("request", count_request)
        blocked = []
        context.on(
            "response",
            lambda response: blocked.append(True) if response.status in {401, 403, 429} else None,
        )
        for source in adapter["sources"]:
            page = await context.new_page()
            await navigate(page, source["url"])
            source_records = {}
            detail_seen = {}
            finished = False
            for _ in range(source.get("max_pages", 50)):
                await asyncio.sleep(1)
                if blocked:
                    raise SelectorError("Account access restriction encountered; stopping")
                https_url(page.url, couchsurfing=True)
                batch = await collect_page(page, source, adapter["auth_marker"], detail_seen)
                for record in batch:
                    source_records[record.key] = record
                if await page.locator(source["end"]).is_visible():
                    finished = True
                    break
                # Explicitly configured paging; absence is never accepted as completion.
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
            await page.close()
        await session_save(session, context)
    return deduplicate(records), {
        "requests": requests,
        "duration_seconds": round(time.monotonic() - started, 2),
        "sources": counts,
        "complete": True,
    }
