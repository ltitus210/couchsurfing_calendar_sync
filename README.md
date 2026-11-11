# Couchsync

Private Couchsurfing → Apple Calendar / Google Calendar subscriptions. Python 3.13+,
macOS 15+ (Intel/Apple Silicon); Windows 10/11 scheduler support.

**Start here:** [Guided macOS setup](docs/setup-macos.md). It explains which window to use,
what to click in Chrome/Playwright Inspector, what each command should show, and when to
stop for maintainer help. [Already subscribed? Find your next stage](docs/setup-macos.md#find-your-current-stage).
Windows users should start with [installation-windows.md](docs/installation-windows.md).

**Current status:** one account's Going, Interested and Organizing events have been synced
and checked in Apple Calendar. Native macOS services were loaded and the local feed returned
HTTP 200. A subsequent unattended run still needs confirmation. Invitations, incoming hosting,
full-list completeness, Windows runtime and Google/remote publication remain unverified.
See the [validation record](docs/validation.md) for the scope of each result.

**Fresh installs still need account-specific scraper configuration.** `setup` writes general
settings; `login` saves an encrypted session; `scraper inspect` only opens inspection tools.
None of these automatically creates a working selector profile. The
[configuration handoff](docs/setup-macos.md#4-stop-for-the-configuration-handoff) is a required
checkpoint before the first sync. No universal authenticated selector profile ships here.

## Setup checkpoints

| Stage | Success check | Next step |
|---|---|---|
| Install in your working checkout | `couchsync --help` works; use the complete `-e .` command | [Login](docs/setup-macos.md#2-set-up-and-log-in) |
| Login in the isolated Chrome window | Type `SAVE` in Terminal after authenticating; command finishes | [Browser inspection](docs/setup-macos.md#3-inspect-the-website-in-chrome-and-playwright-inspector) |
| Inspect in Chrome with Inspector paused | Maintainer has inspected the needed pages; Resume finishes inspection | [Profile handoff](docs/setup-macos.md#4-stop-for-the-configuration-handoff) |
| Receive a verified account profile | Its configuration and selector file exist | [One live sync and preview](docs/setup-macos.md#5-run-one-sync-and-preview-the-calendar) |
| Check saved events | Expected titles/dates; UTC preview understood | [Serve and subscribe](docs/setup-macos.md#6-serve-the-feed-and-subscribe-in-apple-calendar) |
| Check Apple Calendar | Subscription displays correct local times | [Upgrade fixed counts](docs/setup-macos.md#7-upgrade-the-event-profile-for-changing-lists) |
| Enable background operation | Both jobs loaded; local URL returns HTTP 200 | [Verify an unattended run](docs/setup-macos.md#9-verify-the-next-unattended-run) |

Do not run `scraper check`, `sync --dry-run` and `sync` in a batch: each is a live website
attempt and shares the hourly guard. `preview`, `serve`, status and logs read local data.
Use the same global `--config` argument before the command throughout a setup.

## Calendars and publishing

- [Apple Calendar](docs/apple-calendar.md): loopback subscription on the same Mac or HTTPS.
- [Google Calendar](docs/google-calendar.md): externally reachable HTTPS is required.
- [Private WebDAV HTTPS publication](docs/remote-publishing.md): optional static snapshots,
  independent 256-bit feed tokens, rotation/revocation, Keychain/Credential Manager credentials.
- [Example configuration](examples/config.example.toml): privacy, availability, feeds and timing.

Feed URL requests never run the scraper. Subscriptions are read-only. The calendar
provider controls refresh timing; hourly scraping does not imply hourly client refresh.

## Data policy

Events use a single immutable source identity across list memberships; organizing has
precedence over Going, Interested, Invited for the title while relationships preserve
attendance. UUID calendar UIDs survive changes; changes increment SEQUENCE. Explicit
inactive statuses produce CANCELLED tombstones. Missing records are always retained.
Even a complete list does not prove cancellation. A configurable mass-cancellation
threshold blocks suspicious batches (at least three existing active records).

Pending hosting is transparent/free; confirmed hosting is opaque/busy. Arrival/departure
are all-day dates with exclusive checkout. Explicit same-day stays occupy one day.
Missing dates remain in database diagnostics and are omitted from calendars. Timed events
require explicit UTC offsets or unambiguous IANA-zone times; no machine-local assumption.
Old events leave feeds after the retention period; database/history retention is separate
and currently persists until the user removes local data.

Default hosting privacy is limited (generic guest title, no messages/addresses/source URLs).
Default event privacy is limited (title/status/dates). Full mode may expose names,
addresses and source URLs. Busy/private mode strips identifying metadata; opaque random
UIDs remain so clients can update entries. Privacy filters apply to every export/preview/feed.

## After the first successful event/calendar test

See [background event updates](docs/hourly-events.md) for a reversible upgrade from fixed
counts to verified event observations, lower-traffic navigation, separate publisher/worker
services and the remaining coverage limits. Missing entries stay in the calendar until
verified inactive or removed by the historical feed-retention policy.

## Maintenance

`backup PATH` uses SQLite backup under the synchronization lock. Backups contain private
plaintext records; encrypt them using OS storage encryption. `restore PATH` retains a
pre-restore backup. Session encryption keys are never included. `logout` removes local
session state; revoke Couchsurfing sessions on the website if compromise is suspected.

Before upgrading: stop services, back up, update dependencies/package, run tests/doctor,
then reinstall services if the interpreter moved. Schema v1 initializes transactionally;
newer unsupported schemas are rejected. No destructive migrations ship in v0.1.

Uninstall: `service stop`, `service uninstall`, `logout`, `calendar revoke` for each remote
feed, remove subscriptions, then uninstall the package/venv. Feed tokens and publishing
credentials can be removed from OS credential storage under `couchsync:<installation-id>`.
Remove application config/data/log directories only after preserving desired backups.

[Security](docs/security.md) · [Troubleshooting](docs/troubleshooting.md) ·
[macOS scheduling](docs/installation-macos.md) · [Contributing](CONTRIBUTING.md)

## Development

```sh
python -m pip install -e '.[dev]'
python -m playwright install chromium
pytest -q
ruff check .
python -m build
pip-audit -r requirements.lock
```

Synthetic fixtures are intentionally fictional; passing them proves adapter mechanics,
not live selectors. CI is configured for Python 3.13/3.14 on macOS and Windows, secret scanning and
vulnerability auditing; hosted execution is not implied by local checks. See [dependency updates](docs/dependencies.md).
