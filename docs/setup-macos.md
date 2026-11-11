# macOS quick start

Run commands from the project folder. Use the same Terminal unless a step says otherwise.
Stop if a command fails. [Troubleshooting](troubleshooting.md).

## Already installed?

- Correct preview? Skip to [Calendar](#6-subscribe-in-apple-calendar).
- Calendar works? Continue with [profile upgrade](#7-upgrade-fixed-counts-if-needed).
- Both services active and HTTP 200? Skip to [the hourly check](#9-check-the-next-hourly-run).

## 1. Install

```sh
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes -r requirements.lock
python -m pip install setuptools wheel
python -m pip install --no-deps --no-build-isolation -e .
python -m playwright install chromium
```

**Look for:** `Successfully installed couchsync`. Keep the final dot in `-e .`.
For later updates, activate the existing `.venv` instead of recreating it.

## 2. Log in

```sh
couchsync setup
```

- **Chrome opens:** log into Couchsurfing, including any MFA.
- **Terminal:** type `SAVE` at the login prompt and press Return. Chrome closes.
- If you skipped login during setup, run `couchsync login` to open it.

**Look for:** the Terminal prompt returning without an error. This saves an encrypted session.

## 3. Inspect in Chrome

```sh
couchsync scraper inspect
```

Two windows open. Terminal waiting is normal.

| Window | What to do |
|---|---|
| **Chrome** | Open **Events → View Your Events → Going**, then an event's details. Repeat for Interested and Organizing. |
| **Playwright Inspector** | Leave paused while the maintainer inspects. Click **Resume ▶** only when finished. |
| **Terminal** | Wait for the command to finish; do not type `SAVE` during inspection. |

- If asked for a locator: **Pick Locator → click the requested element in Chrome → copy the Inspector field**.
  Turn the picker off to navigate normally. [More detail](selectors.md).
- For hosting, show an existing request **from someone asking to stay with you**.
  “Your Request” / “View Your Trip” indicates an outgoing request, which is excluded.
- No incoming example or Invited tab? Tell the maintainer; do not create test requests.
- When finished, click **Resume ▶ in Inspector**. It saves the session and closes Chrome.

**Look for:** Terminal's prompt returning. Inspection alone does not configure the scraper.

## 4. Get the account profile

**Stop until a maintainer supplies and checks these private files:**

- `$HOME/Library/Application Support/couchsync/events-first.toml`
- The selector file referenced by that configuration.

These filenames describe the event-first setup used here. `setup` does not create them;
`upgrade-events` cannot create a missing initial profile. Use the actual path supplied
for your account. [Maintainer instructions](selectors.md#maintainer-profile-creation-is-a-manual-prerequisite).

The currently tested scope is Going, Interested and Organizing. Hosting, invitations
and full-list completeness remain unverified.

## 5. Sync and preview

```sh
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" sync
```

| Result | Next action |
|---|---|
| `success` | Guarded first sync passed. Preview below. |
| `updated_observations`, `complete: false` | Successful verified-event update with incomplete list coverage. Preview below. |
| `not_due` | Wait until an hour after the last attempt; do not keep retrying. |
| Error | Stop and [troubleshoot](troubleshooting.md). |

Checks, dry-runs and syncs share the hourly guard, including failures. Choose **one** live
command at a time; do not run `scraper check`, `sync --dry-run` and `sync` as a sequence.

```sh
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" preview
```

**Look for:** expected titles and dates. Preview is local and uses UTC: November 13,
2026 at `00:00+00:00` is November 12 at 7 PM in New York. Check local end times in Calendar.

## 6. Subscribe in Apple Calendar

**Terminal A — leave this running:**

```sh
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" serve
```

It holds the Terminal open; older versions may print nothing. If the managed publisher
is already active, skip this manual server.

**Terminal B — check the feed:**

```sh
curl --noproxy '*' -I http://127.0.0.1:8765/couchsurfing.ics
```

**Look for:** `200 OK` and `Content-Type: text/calendar`. Connection refused means the
server is unavailable; check Terminal A before retrying Calendar.

**In Apple Calendar:**

1. **File → New Calendar Subscription**.
2. Enter `http://127.0.0.1:8765/couchsurfing.ics` and click Subscribe.
3. Choose **On My Mac**, a name, and Auto-refresh.
4. Confirm local start/end times and multi-day spans.

Keep Terminal A open for now. A local HTTP permission prompt does not start the server.
[Calendar troubleshooting and other devices](apple-calendar.md).

## 7. Upgrade fixed counts if needed

After the first Calendar check, open Terminal B in the project folder and run:

```sh
source .venv/bin/activate
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" scraper upgrade-events
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" sync
```

**Look for:** `upgraded` (or `already_upgraded`), then `updated_observations` once the hourly
guard permits. `complete: false` is expected: verified records update; missing entries stay.
Already tested this upgraded mode? Skip this step. [Coverage limits](hourly-events.md).

## 8. Start background services

Already active? Skip install/start and verify the feed.

First press **Ctrl-C** in Terminal A to stop the manual `serve` command. Then run:

```sh
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" service install
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" service start
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" service status
curl --noproxy '*' -I http://127.0.0.1:8765/couchsurfing.ics
```

**Look for:** `sync: active`, `serve: active`, and HTTP `200 OK`. You can now close the
terminals and keep the existing Calendar subscription. Do not add a duplicate.
Install is needed once; start loads the jobs. Active means loaded, not proof of an hourly sync.

## 9. Check the next hourly run

Leave the Mac logged in and awake for a full interval. Then open Terminal in the project:

```sh
source .venv/bin/activate
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" status
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" logs
```

**Look for:** a newer `last_success`, plausible event counts, and no later failure.
These commands do not scrape. The publisher keeps the feed available; the worker exits
between hourly attempts. Sleep/wake timing is best effort.

[Service reference](installation-macos.md) · [Troubleshooting](troubleshooting.md)
