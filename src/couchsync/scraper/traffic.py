"""Aggregate browser traffic counters. No URLs, headers or cookies are retained."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from weakref import WeakKeyDictionary


@dataclass
class Traffic:
    access_restricted: bool = False
    attempted: int = 0
    allowed: int = 0
    blocked: int = 0
    by_type: Counter = field(default_factory=Counter)

    async def route(self, route):
        resource_type = route.request.resource_type
        if self.access_restricted or resource_type in {"image", "media", "font"}:
            self.blocked += 1
            await route.abort("blockedbyclient")
        else:
            self.allowed += 1
            await route.continue_()

    def response(self, response):
        from urllib.parse import urlsplit

        if response.status in {401, 403, 429} and urlsplit(response.url).hostname in {
            "www.couchsurfing.com",
            "couchsurfing.com",
        }:
            self.access_restricted = True

    def request(self, request):
        self.attempted += 1
        self.by_type[request.resource_type] += 1

    def summary(self) -> dict:
        return {
            "requests_attempted": self.attempted,
            "requests_allowed": self.allowed,
            "requests_blocked": self.blocked,
            "requests_by_type": dict(self.by_type),
        }


COUNTERS: WeakKeyDictionary = WeakKeyDictionary()


async def install(context) -> None:
    counter = Traffic()
    COUNTERS[context] = counter
    context.on("request", counter.request)
    context.on("response", counter.response)
    await context.route("**/*", counter.route)


def summary(context) -> dict:
    counter = COUNTERS.get(context)
    return counter.summary() if counter else {}


def restricted(context) -> bool:
    counter = COUNTERS.get(context)
    return bool(counter and counter.access_restricted)
