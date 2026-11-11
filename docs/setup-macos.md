# macOS quick start

Run commands from the project folder. Stop if one fails. [Troubleshooting](troubleshooting.md).
New installs include shared website defaults; browser inspection is optional repair work.

## Already installed?

- Correct preview? Skip to [Calendar](#4-apple-calendar).
- Calendar works? Enable [background services](#5-background-services).
- Both services active and HTTP 200? Check [the hourly run](#6-check-the-hourly-run).
- Existing custom configuration? Keep [using that profile](#using-an-existing-custom-profile).

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
For updates, activate the existing `.venv` instead of recreating it.

## 2. Set up and log in

```sh
couchsync setup
couchsync login
```

- Accept the setup defaults, or choose categories/privacy settings.
- Skip `login` if you already logged in during setup.
- **Chrome:** log into Couchsurfing, including any MFA.
- **Terminal:** type `SAVE` at the login prompt and press Return. Chrome closes.

**Look for:** the Terminal prompt returning without an error. Your session is encrypted.
No Playwright Inspector, manual page tour or account-specific selector file is needed.

## 3. Sync and preview

```sh
couchsync sync
couchsync preview
```

| Result | What to do |
|---|---|
| `updated_observations`, `complete: false` | Saved observed records; full-list coverage is unverified. Check preview. |
| `source_notes` | Read the notes: an unavailable Invited view or unrecognized hosting layout can be skipped. |
| `not_due` | Wait until an hour after the last attempt. |
| Error | Stop and [troubleshoot](troubleshooting.md). |

**Look for:** expected titles and dates. Preview uses UTC; Calendar shows local times.
Missing records are retained. Event labels refer to Going, Interested, Organizing and Invited events.
Hosting Request labels mean incoming guest requests; Stay labels mean your outgoing requests
to hosts. Both use Pending / Confirmed states. Default event entries include venue/address, About text and a source link; requests/stays
also include source links. Event detail changes refresh on subsequent successful syncs.
Incoming/confirmed stay layouts and empty-state wording await live validation. [Coverage](validation.md).

Sync/check/dry-run share the hourly guard, including failures. They are alternatives,
not three required setup commands. Preview is local and can be repeated.

## 4. Apple Calendar

Leave this running in **Terminal A**:

```sh
couchsync serve
```

In **Terminal B**:

```sh
curl --noproxy '*' -I http://127.0.0.1:8765/couchsurfing.ics
```

**Look for:** `200 OK` and `Content-Type: text/calendar`.
Connection refused? Check that Terminal A is still running.

**In Apple Calendar:**

1. File → New Calendar Subscription.
2. Enter `http://127.0.0.1:8765/couchsurfing.ics` → Subscribe.
3. Choose **On My Mac**, a name and Auto-refresh.
4. Check local start/end times and multi-day spans.

Allowing local HTTP does not start the server. Google Calendar and other devices need
[remote HTTPS publishing](remote-publishing.md). [Calendar help](apple-calendar.md).

## 5. Background services

Press **Ctrl-C** in Terminal A to stop the manual server, then run:

```sh
couchsync service install
couchsync service start
couchsync service status
curl --noproxy '*' -I http://127.0.0.1:8765/couchsurfing.ics
```

**Look for:** `sync: active`, `serve: active`, and HTTP `200 OK`.
You can close the terminals. Keep the same Calendar subscription.
Already active? Skip install/start. Install is needed once, after a successful live sync.

## 6. Check the hourly run

Leave the Mac logged in and awake for a full interval, then run:

```sh
source .venv/bin/activate
couchsync status
couchsync logs
```

**Look for:** a newer `last_success` and no later failure. Active services alone do not
prove a scheduled sync succeeded. Sleep/wake timing is best effort.

## Using an existing custom profile

Keep the same configuration argument on every command, for example:

```sh
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" sync
```

Existing selector files are preserved and take precedence over bundled defaults.
An events-only custom profile still syncs only events. To use shared defaults for hosting
and surfing, back up that profile, remove its `selector_file` setting (and move any default
`selectors.toml` aside), and include `hosting` in the configuration’s `categories`.
The `hosting` category enables both incoming requests and outgoing stays.
Only older fixed-count profiles need [the optional migration](event-first-sync.md)
before installing an hourly worker. New installations do not need it.

## If the website changes

Update Couchsync first. If the layout still fails, use [optional inspection](selectors.md):

```sh
couchsync scraper inspect
```

- **Chrome:** open the failing event tab/details or incoming stay request.
- **Playwright Inspector:** leave paused while checking the page. If asked for a locator,
  use **Pick Locator → click the element → copy the locator**. Turn the picker off to navigate.
- **Finish:** click **Resume ▶ in Inspector**. It saves the session and closes Chrome.
- **Terminal:** waiting is normal; do not type login's `SAVE` during inspection.

Inspection does not automatically rewrite the adapter. A maintainer can update the shared
defaults or help create an override. Do not change RSVPs or requests to obtain examples.
