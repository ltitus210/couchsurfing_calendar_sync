# Windows 10/11

Native Windows runtime still needs validation. Install Python 3.13+ from python.org,
then run in PowerShell in this project:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python -m pip install --require-hashes -r requirements.lock
.\.venv\Scripts\python -m pip install setuptools wheel
.\.venv\Scripts\python -m pip install --no-deps --no-build-isolation .
.\.venv\Scripts\python -m playwright install chromium
.\.venv\Scripts\couchsync setup
.\.venv\Scripts\couchsync login
```

**Chrome:** log in. **PowerShell:** type `SAVE` at the login prompt and press Enter.
Skip `login` if you already logged in during setup. Shared website defaults are included;
no initial inspection or supplied selector profile is needed.

```powershell
.\.venv\Scripts\couchsync sync
.\.venv\Scripts\couchsync preview
.\.venv\Scripts\couchsync serve
```

**Look for:** `updated_observations`, plausible titles/dates, then a running server.
`complete: false` means full-list coverage is unverified; missing records stay.
`not_due` means wait until an hour after the last attempt. Read `source_notes` for
unavailable invitation/hosting views. [Coverage limits](validation.md).

Leave the server running for local clients. Google Calendar requires
[remote HTTPS publication](remote-publishing.md), rather than a loopback URL.

## Task Scheduler

After validating a sync, stop manual `serve` with Ctrl-C, then run:

```powershell
.\.venv\Scripts\couchsync service install
.\.venv\Scripts\couchsync service start
.\.venv\Scripts\couchsync service status
```

**Look for:** both tasks active. Check `status` and `logs` after an hour for a newer
`last_success`; loaded tasks alone do not prove a scheduled scrape succeeded.

Task Scheduler registers Couchsync-sync and Couchsync-serve as the current user,
InteractiveToken, LeastPrivilege. The sync repeats hourly from logon with StartWhenAvailable
and IgnoreNew. The publisher starts at logon and retries failures three times.
Use `--task serve` or `--task sync` to target one task; the default is both.

The user must be logged in and Credential Manager available. Sleep/logoff interrupt
availability. No computer wake or exact timing is promised. Reinstall tasks if the Python
path changes. Windows registration/runtime remains unverified; XML definitions are tested.
Existing custom profiles still take precedence; older fixed-count profiles need
[upgrade](event-first-sync.md) before worker installation.

## If the website changes

Use `scraper inspect` only for troubleshooting. [Browser instructions](selectors.md):
navigate in Chrome; finish with **Resume ▶ in Playwright Inspector**, not `SAVE`.
Inspection does not automatically rewrite settings.

## Uninstall

Follow [the uninstall commands](uninstall.md) to remove services, subscriptions and the
package. Saved data is kept unless you choose the optional cleanup.
