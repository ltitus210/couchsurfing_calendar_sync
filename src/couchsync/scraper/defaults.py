"""Versioned shared layout, based on the November 2026 Couchsurfing interface.

No account IDs, coordinates, cookies or account-specific counts are bundled.
"""

from __future__ import annotations

from copy import deepcopy

LAYOUT_VERSION = "2026-11-10"
EVENTS = {
    "going": ("going", "Going"),
    "interested": ("interested", "Interested"),
    "organized": ("organizing", "Organizing"),
    "invited": (None, "Invited"),
}


def profile(categories: list[str]) -> dict:
    sources = []
    for category in categories:
        if category == "hosting":
            sources.append(
                {
                    "category": "hosting",
                    "kind": "hosting",
                    "adapter": "messages_stays",
                    "url": "https://www.couchsurfing.com/c/home",
                    "completion": "observed",
                    "optional": True,
                    "max_items": 20,
                }
            )
            continue
        if category not in EVENTS:
            raise ValueError("Unknown built-in source category")
        tab, label = EVENTS[category]
        panel = f'role=tabpanel[name="{label}"]'
        source = {
            "category": category,
            "kind": "event",
            "url": "https://www.couchsurfing.com/c/events/my-events"
            + (f"?tab={tab}" if tab else ""),
            "container": panel,
            "item": panel + " >> [data-couch-crash][data-user-created]",
            "event_json_ld": 'script[data-testid="hangout-json-ld"]',
            "detail_link": 'a[href^="/c/events/"]',
            "detail_container": 'body:has(script[data-testid="hangout-json-ld"])',
            "completion": "observed",
            "max_pages": 1,
            "tab_label": label,
            "detail_navigation": "same_tab",
        }
        # English empty-state wording is an explicit layout assumption. These markers
        # are scoped to the selected panel and exclude event-card descendants.
        words = r"^(no (upcoming )?(events|invitations)|nothing (here|to (show|see))|you (haven.t|have not|aren.t|are not|don.t|do not).*(events|invited|going|organizing|interested))"
        source["empty"] = panel + f' >> :text-matches("{words}", "i"):not([data-couch-crash] *)'
        if category == "invited":
            source["optional"] = True
        sources.append(source)
    return deepcopy(
        {
            "layout_version": LAYOUT_VERSION,
            "validated_on": "Shared event layout observed 2026-11-10; hosting incoming controls/date layout assumed",
            "auth_marker": 'role=button[name="Profile"]',
            "sources": sources,
        }
    )
