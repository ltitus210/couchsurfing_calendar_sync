# Windows 10/11

Install Python 3.13+ from python.org, then in PowerShell in this project:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python -m pip install --require-hashes -r requirements.lock
.\.venv\Scripts\python -m pip install setuptools wheel
.\.venv\Scripts\python -m pip install --no-deps --no-build-isolation .
.\.venv\Scripts\python -m playwright install chromium
.\.venv\Scripts\couchsync setup
.\.venv\Scripts\couchsync login
.\.venv\Scripts\couchsync scraper inspect
```

## Browser inspection is not automatic configuration

If setup already opened login and saved it, skip the separate login command. For standalone
login, authenticate in Chrome, then type `SAVE` in Terminal. For `scraper inspect`, use
Chrome to navigate and leave Inspector paused; finish with **Resume ▶ in Inspector**,
not `SAVE`. See the shared [Chrome/Inspector walkthrough](setup-macos.md#3-inspect-in-chrome)
for the window roles and page-selection steps; use the Windows executable paths above
rather than copying its macOS shell commands.

Opening Inspector does not generate an account-specific selector/profile file. Stop for
[the maintainer handoff](setup-macos.md#4-get-the-account-profile) before attempting
sync. `events-first.toml` is a supplied profile convention, not automatic setup output.
No incoming hosting sample means that coverage remains unverified; an outgoing “Your Request”
page is not an incoming hosting example. Do not create requests just to test this.

After a profile is supplied, choose one live sync/check/dry-run attempt, then preview locally.
`not_due` means wait for the configured interval. Observation-mode `complete: false` is an
expected coverage limit, not a failed run. See [first-sync outcomes](event-first-sync.md).

## Task Scheduler

After a validated sync run `service install` and `service start`
using the same couchsync executable. Task Scheduler registers Couchsync-sync and
Couchsync-serve as the current user, InteractiveToken, LeastPrivilege. The sync task repeats
hourly from logon with StartWhenAvailable and IgnoreNew. The publisher starts at logon,
runs without a time limit and retries failures three times. `start`, `stop`, `status`,
`uninstall` use schtasks /Run, /End, /Query, /Delete respectively.

The user must be logged in; these are not SYSTEM tasks or Windows Services. Credential
Manager must be unlocked/available. Sleep and logoff interrupt availability. No computer
wake is requested; missed timed work can run later subject to Task Scheduler and the
worker's interval guard. Do not promise exact execution times. Reinstall if the Python
path changes. Native registration/runtime still needs validation on Windows; XML structure
is tested on macOS and CI is configured for Windows.

`service <action> --task serve` and `--task sync` target one scheduled task independently;
`--task all` is the default. Fixed-count bootstrap profiles are rejected for worker installation.
