# From the first successful calendar to background event updates

Use `/Users/ltitus/git/couchsurfing_calendar_sync/` for source changes and GitHub pushes.
Use `/Users/ltitus/scripts/couchsurfing/couchsurfing_calendar_sync/` as the installed working
checkout. Do not install from the source repository if you intend to run the other checkout.
Commit/push and transfer changes through your normal Git workflow; this guide does not
publish a repository or overwrite either checkout automatically.

## What the new mode verifies

`upgrade-events` replaces the exact bootstrap counts with **observed-event updates** for
Going, Interested and Organizing. New list sizes are allowed. Every imported record still
requires a valid event identity, a matching structured Event detail page and explicit-offset
dates. Authentication failure, unexpected structure, a detail mismatch, a changing list,
rate limiting or a parser error aborts the whole run and preserves previous snapshots.

The inspected live list did not expose a reliable total/end marker. This mode does **not**
claim full-list completeness: successful output says `updated_observations`,
`observations_only: true`, `complete: false`. It can add and update individually verified
records. Missing records remain untouched; absence never cancels an event. Explicit
structured EventCancelled states can cancel known entries, with the same mass-cancellation
safeguard as before. Previously known organizer membership is retained when an incomplete
organizer list cannot disprove it. Attendance statuses can update when observed in a list.

A list with no cards requires an actually inspected, configured explicit empty-state marker.
Without one, the run stops rather than accepting a failed selector as an empty account.
This means an empty tab may need further adapter inspection. Full pagination, missing-RSVP
verification, invitations and incoming hosting remain unfinished. Do not describe this as
complete Couchsurfing synchronization. Hourly use is limited to these observation semantics.

## Update the working checkout and test once

After bringing the source changes into the working checkout, activate its existing `.venv`:

```sh
cd /Users/ltitus/scripts/couchsurfing/couchsurfing_calendar_sync
source .venv/bin/activate
python -m pip install --no-deps --no-build-isolation -e .
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" scraper upgrade-events
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" sync
```

The upgrade is local and does not open a browser or access credentials. It backs up the
exact old selector file with a `.before-observations-<random>.bak` suffix, then atomically
replaces only that selector profile. The original main config, session, database and
calendar subscriptions are preserved. Repeating it is harmless. To reverse it, stop the
worker and replace the selector file with the backup. Fixed-count profiles are blocked
from hourly-worker installation because count changes would stop them.

If the Inspector is still open, press Resume there first to save the session and return
to the terminal. Do not run another sync merely to measure again: successful and failed
attempts are limited to the configured interval. `not_due` means the existing guard worked.
Preview/status/serve and profile upgrades do not request Couchsurfing data.

## Traffic changes and measurement

Background Chromium blocks image, media and font transfers. Login and visible inspection
retain normal resources. Scripts, stylesheets, fetch/XHR, normal authentication and all TLS
checks remain enabled. Service workers are blocked only inside the ephemeral headless
context so they cannot hide requests from resource filtering. No OS/browser account
security setting is changed.

The worker uses normal in-app tabs, event links and browser Back to reuse the loaded app
instead of loading the entire application for every event. It checks the selected event's
canonical identity before reading metadata and reuses details for duplicate list memberships
within one run. Interactive browser restrictions and rate limits are still respected.

Metrics distinguish `requests_attempted`, `requests_allowed` and `requests_blocked`, plus
aggregate resource types. `requests` retains the older attempted-request meaning. Allowed
means the resource policy permitted the request, not proof it reached the network or bypassed
all browser caches. No URLs, cookies or headers are saved in these counters. Enabling
Playwright routing disables HTTP caching, so the net effect must be measured on the real
site. See https://playwright.dev/python/docs/api/class-browsercontext#browser-context-route.
The synthetic tests verify fewer full-page loads and blocked transfers; no live reduction
from the earlier 1,446-request run is claimed until the updated application is tried.

## Keep the local feed available without a terminal

After updating, the publisher can be managed independently from the scraper. Stop the
manually running `serve` command with Ctrl-C before starting its replacement, to free port
8765. Then run:

```sh
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" service install --task serve
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" service start --task serve
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" service status --task serve
curl --noproxy '*' -I http://127.0.0.1:8765/couchsurfing.ics
```

On macOS this writes/loads a per-user `org.couchsync.serve` LaunchAgent using the working
checkout's Python interpreter and config path. The successful HEAD response is 200, and
the existing On My Mac Apple Calendar subscription stays the same. No new scrape is
triggered by serving or checking the feed. Keep the working checkout/venv at a stable path.

## Hourly observation worker

Only after one successful updated live run, review its counts/coverage/traffic. If those
limited semantics meet your immediate needs, install and start the separate worker:

```sh
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" service install --task sync
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" service start --task sync
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" service status --task sync
```

The worker is one-shot, respects the persisted hourly attempt guard and exits. macOS uses
StartInterval, RunAtLoad and a calendar wake trigger; Windows uses a least-privilege logged-in
Task Scheduler task. No credentials or browsers are embedded in the scheduler definition.
Use `service stop --task sync` and `service uninstall --task sync` to stop/remove it while
leaving the publisher running. This build's native registration/start/wake behavior still
requires validation under the real user account. Do not claim hosted CI or Windows runtime
success from locally generated service definitions.
