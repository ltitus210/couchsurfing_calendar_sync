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

Follow docs/selectors.md. After a validated sync run `service install` and `service start`
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
