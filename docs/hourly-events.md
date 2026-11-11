# From the first successful calendar to background event updates

For the complete user sequence, use [guided setup](setup-macos.md).
New installs already use observation mode; no upgrade or initial inspection is needed.
This page explains update limits and the optional migration for older custom profiles.
Commands below with `events-first.toml` apply only to those existing profiles; new users
use the plain commands in the quick start.
If both services already report active and the feed returns HTTP 200, do not reinstall;
[verify the next unattended run](setup-macos.md#6-check-the-hourly-run).

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

A list with no cards requires a recognized explicit empty-state marker.
Without one, the run stops rather than accepting a failed selector as an empty account.
This means an empty tab may need further adapter inspection. Full pagination and missing-RSVP
verification remain unverified. Bundled invitation and incoming-hosting assumptions still
need live validation; optional unavailable views are reported rather than blocking events. Do not describe this as
complete Couchsurfing synchronization. Hourly use is limited to these observation semantics.

## Older fixed-count profiles: update and test once

After updating the project, activate its existing `.venv`:

```sh
source .venv/bin/activate
python -m pip install --no-deps --no-build-isolation -e .
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" scraper upgrade-events
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" sync
```

Run one command at a time. Installation should end with `Successfully installed couchsync`.
The final dot in `-e .` is required; `-e` by itself is incomplete. If `sync` says `not_due`,
wait until the normal interval has elapsed instead of rerunning it immediately.

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
A user-reported updated live run verified the same six events with 799 attempts,
241 allowed and 558 blocked requests in 20.8 seconds, compared with the earlier 1,446
attempts in 28.58 seconds. These are results from one account/run, not a guaranteed traffic
budget. The run reported `updated_observations`, `complete: false` and limited coverage.
Synthetic tests independently verify fewer full-page loads and blocked transfers.

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
project environment's Python interpreter and config path. The successful HEAD response is 200, and
the existing On My Mac Apple Calendar subscription stays the same. No new scrape is
triggered by serving or checking the feed. Keep the project and `.venv` at stable paths.

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
leaving the publisher running. One user has now verified native macOS install/start/status
for both jobs and HTTP 200 from the managed publisher. This proves startup and availability,
not a later scheduled scrape. Confirm `last_success` advances after a full interval while
the Mac is logged in/awake. Sleep/wake behavior, Windows runtime and hosted CI results
have not been verified by those local startup checks.
