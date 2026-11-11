# Guided macOS setup: what to do, what to expect, and what comes next

Follow one numbered stage at a time. Stop if its success check does not pass; do not
skip ahead to calendar subscriptions or background services to fix an earlier failure.

**Current limit:** an account-specific scraper profile still needs maintainer setup.
Logging in and opening Inspector do not create that profile automatically. The tested
initial scope is Going, Interested and Organizing. Invitations, incoming hosting and
full-list coverage remain unverified. Google Calendar requires separate HTTPS publishing.

## Find your current stage

| What you already have | Continue here |
|---|---|
| No installed command yet | [1. Install in the working checkout](#1-install-in-the-working-checkout) |
| Installed command, no saved login | [2. Set up and log in](#2-set-up-and-log-in) |
| Chrome and Playwright Inspector open, unsure what to click | [3. Inspect the website](#3-inspect-the-website-in-chrome-and-playwright-inspector) |
| Pages inspected, but no configured selector/profile file | [4. Configuration handoff](#4-stop-for-the-configuration-handoff) |
| Profile supplied by a maintainer | [5. Run one sync and preview](#5-run-one-sync-and-preview-the-calendar) |
| Correct preview, no calendar subscription | [6. Serve and subscribe](#6-serve-the-feed-and-subscribe-in-apple-calendar) |
| First subscription works, still using fixed event counts | [7. Upgrade the event profile](#7-upgrade-the-event-profile-for-changing-lists) |
| Updated live run works, but a terminal must stay open | [8. Start background services](#8-start-background-services) |
| Both services say active and the feed returns 200 | [9. Verify the next unattended run](#9-verify-the-next-unattended-run) |

You do not need to redo login, inspection, installation or subscription after every sync.
If your services and subscription already work, go directly to stage 9.

## 1. Install in the working checkout

### Choose the right directory

One checkout is enough for most users. If you keep separate development and running
checkouts, use them consistently. For the two-checkout workflow used during testing:

| Directory | Purpose |
|---|---|
| `$HOME/git/couchsurfing_calendar_sync` | Codex/code changes, review, commits and GitHub pushes |
| `$HOME/scripts/couchsurfing/couchsurfing_calendar_sync` | Working checkout, its `.venv`, installation and running commands |
| `$HOME/Library/Application Support/couchsync` | Default macOS private settings, session and application data; outside both checkouts |

Bring changes from the source checkout into the working checkout through your normal
Git workflow **before reinstalling there**. Editing source files in one checkout does
not update an installation pointing to the other. Do not copy authentication state,
private settings or calendars into either repository.

Run these commands from your working checkout. Adapt the first path if you chose a
different directory. Run in order and stop if a command reports an error:

```sh
cd "$HOME/scripts/couchsurfing/couchsurfing_calendar_sync"
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes -r requirements.lock
python -m pip install setuptools wheel
python -m pip install --no-deps --no-build-isolation -e .
python -m playwright install chromium
```

The **final dot in `-e .` is required**: it means “install the current directory.”
`-e` alone produces `-e option requires 1 argument`. An editable installation uses
this working checkout's code, not a second source checkout elsewhere.

**Success check:** installation ends with `Successfully installed couchsync` and
`couchsync --help` displays commands. To check which Python is being used:

```sh
python -c 'import sys; print(sys.executable)'
```

It should point inside this working checkout's `.venv/bin/`. A prompt showing both
`(.venv)` and `(base)` is not itself an error; check the actual interpreter path.

**Next:** stage 2. For later updates, reuse `.venv`; do not recreate it each time.

## 2. Set up and log in

In Terminal, run:

```sh
couchsync setup
```

The wizard writes non-secret `config.toml` settings. It does not discover the website's
page structure or create a verified selector profile. If settings already exist, the
command preserves them. The default macOS file is
`$HOME/Library/Application Support/couchsync/config.toml`.

If you answer yes to opening login during setup, complete the following login flow in
that window. Otherwise, open it yourself:

```sh
couchsync login
```

1. **In the Chrome/Google Chrome for Testing window:** log into Couchsurfing normally.
   Complete any social login or MFA yourself. This isolated browser may not already be
   logged in even if your everyday browser is.
2. Confirm you can see your logged-in Couchsurfing account page.
3. **Back in Terminal:** type `SAVE` in uppercase at the login prompt and press Return.
   Do not type it into a website search box or message field.
4. Chrome closes and Terminal returns to its prompt. The browser session is saved encrypted.

If setup already completed and saved login successfully, do not run `login` a second time.

**Success check:** the login command finishes without an error. `couchsync auth status`
can check local session decryptability; it does not prove the session is still valid online.

**Next:** stage 3. No Couchsurfing password belongs in a command, environment variable or TOML file.

## 3. Inspect the website in Chrome and Playwright Inspector

In Terminal, run:

```sh
couchsync scraper inspect
```

If a maintainer has already supplied a separate event profile, use its configuration:

```sh
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" scraper inspect
```

### Understand the windows

| Window | What it is for | What you do there |
|---|---|---|
| Chrome / Google Chrome for Testing | The real Couchsurfing website | Navigate to account event lists and request details |
| Playwright Inspector | A developer inspection tool | Leave paused while inspecting; optionally use Pick Locator; press Resume when finished |
| Terminal | The running command | Wait during inspection; use the returned prompt for the next command |

**Two windows opening is normal.** Inspector is not a setup wizard and will not tell you
which account page to open next. Terminal waiting while the Inspector is paused is also
normal. Keep the windows open during a live support/maintainer inspection.

### What to do in Chrome

1. Check that you are logged in. If not, return to the login flow in stage 2.
2. In the inspected website layout, choose **Events → View Your Events**.
3. Open **Going**. The observed account URL uses `/c/events/my-events?tab=going`;
   additional location query parameters may appear. Inspect the actual account page,
   not the public “all events nearby” results.
4. Open an existing event to see its title, start/end dates, location and your relationship
   to it. Use Back to return to the list. Navigate normally; do not change your RSVP for testing.
5. Repeat for **Interested** and **Organizing**. Report whether a list contains events or
   displays an explicit empty message. Check for more pages or items below the visible area.
6. If an Invited view is not present, report that it is unavailable in this layout. Do not
   assume invitations are included by another tab or claim that category has been tested.

The observed tab group contained Going, Organizing, Interested and Past. Labels and layout
may change. A maintainer must verify the current page instead of guessing selectors.

### Incoming hosting requests versus your outgoing requests

For hosting validation, open an **existing request from a traveler asking to stay with you**
and view its stay details. The label **Pending Stay alone does not establish direction**.

The page inspected during setup showed “Your Request,” “View Your Trip,” and “Waiting on
[the other person] to accept.” That was an **outgoing accommodation request**, excluded
from the current incoming-hosting scope. A request being pending does not make it a hosting request.

If you have no incoming pending or confirmed stay example, say so. There is no need to
create, send, accept or cancel a request to manufacture test data. A maintainer can leave
hosting marked unverified and continue with an explicitly event-only profile.

### What to do in Playwright Inspector

If a maintainer can inspect the browser directly, leave Inspector paused and Chrome on
the requested page. You do not need to write selector code yourself.

If asked to identify a particular element:

1. Click **Pick Locator** in Inspector.
2. Hover over the requested element in Chrome, such as an event title, then click it
   while picker mode is active.
3. Copy the generated locator from the Inspector field beside Pick Locator and send it
   privately to the maintainer. It may contain an event title; redact personal details
   before posting anything publicly.
4. Turn off picker mode to resume normal website navigation. Picking an element is an
   inspection action, not the normal way to open an event. Recording is not required.

[Playwright's locator-picker instructions](https://playwright.dev/python/docs/debug#picking-locators).
Do not copy cookies, tokens, storage-state exports, whole private conversations or raw
account HTML into public issues. No raw captures are automatically saved by this command.

### How to finish inspection

Wait until the maintainer has finished with the open pages. Then click **Resume ▶ in
Playwright Inspector**. The command saves the current session, closes its browser and
returns to the Terminal prompt.

**Do not type `SAVE` for `scraper inspect`.** `SAVE` belongs to the separate login command;
inspection ends with Inspector's Resume button. Do not press Resume midway through a
requested inspection: it finishes the command rather than merely moving to another page.

**Success check:** the pages and relevant statuses were inspected and the command returned.
This does **not** mean the scraper has been configured. Continue to the handoff in stage 4.

## 4. Stop for the configuration handoff

**Do not run `sync` merely because Chrome and Inspector opened successfully.** This release
still requires a maintainer to create or verify account-specific navigation, selectors,
status mappings and completeness policy. Opening Inspector does not write these settings.

For the event-first workflow in this guide, the maintainer must provide and check:

- `events-first.toml`: an event-only configuration in the private application directory.
- The selector file named by its `selector_file` setting, such as `events-first.selectors.toml`.
- The intended categories, privacy settings, session/data locations and coverage limits.

The `events-first` filename is a convention from the tested setup, **not a file that
`couchsync setup` creates automatically**. `scraper upgrade-events` upgrades an existing
compatible profile; it cannot create a missing profile from scratch. Generic setup uses
`config.toml` and, by default, `selectors.toml`. Maintainer details are in
[selectors.md](selectors.md); the synthetic fixture selectors are not production settings.

**Success check:** a maintainer has confirmed which configuration file to use and that its
selector file exists and matches the inspected pages. If that has not happened, stop here
and ask for profile setup. No amount of repeatedly opening Inspector supplies that missing step.

**Next:** stage 5. Use the same `--config` argument for sync, preview, serve and services.
Put the global `--config` option **before** the command name.

## 5. Run one sync and preview the calendar

Using the supplied event-first profile:

```sh
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" sync
```

Choose one live validation command at a time. `scraper check`, `sync --dry-run` and `sync`
all visit Couchsurfing and share the hourly attempt guard. Do **not** run all three in
succession as if they were required setup stages. A check/dry-run does not write calendar
snapshots; a successful `sync` does.

| Result | Meaning | What to do next |
|---|---|---|
| `success` with inspected-count coverage | The guarded first-sync profile passed its exact-count checks | Preview locally, then validate Calendar and upgrade before scheduling |
| `updated_observations`, `observations_only: true`, `complete: false` | Verified observed events updated; full-list completeness is unverified | Preview locally; this is an expected successful result for observation mode |
| `not_due` | An attempt occurred within the configured interval | Wait until the interval has elapsed, normally one hour after the last attempt |
| Error / `Couchsync could not complete` | A required check failed | Stop and use [troubleshooting.md](troubleshooting.md); preserve the last good calendar |

Failed attempts also count toward the hourly guard. Repeating `sync` immediately will not
fix `not_due`; do not delete timestamps or reduce the guard to force repeated requests.

After a successful sync, run the local preview:

```sh
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" preview
```

Preview reads saved data without another website visit. Check the expected event count,
title prefixes and start dates. It currently prints starts in UTC, for example:

```text
[Going] Example event 2026-11-13T00:00:00+00:00
```

That is November 12 at 7 PM in America/New_York on this date. A next-day UTC date is not
necessarily a wrong event date. Calendar should display the selected local timezone;
check end dates and multi-day spans there too.

**Success check:** the saved entries and dates match the inspected events. Browser request
counts include scripts/images and other assets, not just event-page visits. Observation
mode distinguishes allowed and blocked requests; see [hourly-events.md](hourly-events.md).

**Next:** stage 6. Do not scrape again merely to obtain another preview.

## 6. Serve the feed and subscribe in Apple Calendar

### Terminal A: start the feed server and keep it running

```sh
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" serve
```

This command stays running and does **not** return to the prompt. Current versions print
“Serving saved calendars …”; older versions may stay quiet. That is normal. Leave Terminal A
open. Closing it, pressing Ctrl-C or stopping the command makes the feed unavailable.
Serving the calendar does not open Chrome or request more Couchsurfing data.

If the managed publisher service is already active, skip this manual server and verify
its URL below. Do not start two servers on port 8765.

### Terminal B: confirm the URL works before opening Calendar

Open another terminal window/tab and run this plain-text command; it does not need an
activated Python environment:

```sh
curl --noproxy '*' -I http://127.0.0.1:8765/couchsurfing.ics
```

**Required success check:** an HTTP response containing `200 OK` and
`Content-Type: text/calendar; charset=utf-8`. HTTP/1.0 is normal for this local server.
`Date` and `Last-Modified` use GMT/UTC and may show the next calendar day locally.

If the connection is refused, the server is not accepting connections there. Return to
Terminal A and check that `serve` is still running with the same configuration. A saved
calendar file or a successful sync alone does not keep an HTTP server running. If the
command exited, read its error. More cases are in [troubleshooting.md](troubleshooting.md).

### Apple Calendar: add the subscription

1. Choose **File → New Calendar Subscription**.
2. Paste `http://127.0.0.1:8765/couchsurfing.ics` and click Subscribe.
3. Choose a name/color and **On My Mac** for this local URL.
4. Choose an automatic refresh interval and finish the subscription.
5. Check the expected local start/end times and multi-day spans.

The loopback URL uses HTTP. If Calendar asks about that connection, its permission prompt
and the server's availability are separate checks: permission alone does not start `serve`.
If subscription fails, verify HTTP 200 again before changing calendar settings.

Use a subscription rather than repeatedly importing downloaded files, which can create
duplicates. This URL is available on this Mac; iCloud, another device and Google's servers
cannot fetch this Mac's loopback address. See [Apple Calendar](apple-calendar.md) and
[Google Calendar](google-calendar.md) for remote HTTPS publication.

**Success check:** the subscription shows the expected local events. Keep the manual
server terminal open until stage 8 replaces it with the managed publisher.

## 7. Upgrade the event profile for changing lists

Do this after the first guarded sync/Calendar check and after updating your working
checkout's code. If already upgraded, the command returns `already_upgraded` harmlessly.

```sh
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" scraper upgrade-events
```

`upgraded` means the old selector file was backed up and fixed counts were replaced by
observed-event updates. It is a local configuration change, not a live scrape or automatic
discovery of new selectors. It does not enable invitations or hosting. A missing original
profile must be supplied at stage 4 before this command can work.

Once the hourly guard permits, run `sync` once using the same profile and review the result.
Expected output is `updated_observations`, with `complete: false` and
`observations_only: true`. These flags honestly describe limited coverage, not a failed run.
Missing entries stay in the calendar; removed/declined RSVPs are not inferred from absence.
See [hourly-events.md](hourly-events.md) before choosing unattended use of this limited mode.

**Success check:** one updated live run has plausible counts, dates and traffic. Do not
install the worker with the old fixed-count bootstrap profile.

**Next:** stage 8. If already using observations and the run passed, skip the upgrade.

## 8. Start background services

The publisher keeps the feed available; the worker checks Couchsurfing at most hourly and
then exits. They are separate per-user services. The worker does not keep Chrome open.

First stop the manual `serve` command in Terminal A with **Ctrl-C** so port 8765 is free.
Then, in the working checkout's activated environment, run each command and check its result:

```sh
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" service install
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" service start
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" service status
```

| Command | Expected result |
|---|---|
| `service install` | `sync: installed …` and `serve: installed …`; files are written but jobs are not loaded yet |
| `service start` | `sync: active` and `serve: active` |
| `service status` | Both jobs report `active`, meaning their launchd definitions are loaded |

If already installed and active, skip install/start. Do not reinstall on every launch or
ordinary source update. If installation says a service already exists, inspect `service
status` instead of overwriting its definition. Reinstall if the interpreter/config path
moves; see [installation-macos.md](installation-macos.md).

Finally run the same `curl --noproxy '*' -I` check from stage 6. **Both loaded services plus
HTTP 200** establish startup and feed availability. “Active” alone does not prove that an
hourly scrape succeeded; the one-shot worker normally exits between runs. `not_due` just
after starting is expected if the previous attempt was less than an hour ago.

**Success check:** both services are loaded and the feed returns 200. You can now close
the terminals. Keep using the existing Calendar subscription; do not add a duplicate.

## 9. Verify the next unattended run

Leave the Mac logged in, running and awake for at least one full configured interval.
Then activate the working environment and check saved status/logs:

```sh
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" status
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" logs
```

Check that `last_success` advances after a scheduled run and that its counts/coverage are
plausible, with no later sync failure. These commands read saved information without
scraping. The feed still returning 200 proves availability, not freshness of Couchsurfing data.
Apple Calendar's refresh timing is separate from the worker's schedule.

If authentication expires or the site changes, use the reported failure and the
[troubleshooting guide](troubleshooting.md); previous snapshots are preserved. Login/wake
scheduling is best effort and does not wake the Mac or guarantee an exact execution time.

**Setup complete for this limited scope:** a scheduled run succeeds, the feed stays
available, and Calendar shows the expected events. Invitations, incoming hosting, complete
source reconciliation and remote/Google/iCloud behavior need their own validation.
