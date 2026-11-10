# Couchsync

Private Couchsurfing → Apple Calendar / Google Calendar subscriptions. Python 3.13+,
macOS 15+ (Intel/Apple Silicon); Windows 10/11 scheduler support.

**Implementation status:** calendar, storage, reconciliation, publishing, scheduling and
synthetic browser tests are implemented. **Live Couchsurfing extraction is not yet
validated.** No authenticated selectors ship with this release. An account owner must
inspect the current website and configure the adapter before unattended synchronization
can work. This is a functional application framework, not a claim of production-ready
Couchsurfing integration. See [validation](docs/validation.md). A guarded, manually inspected event-only first-sync
workflow is described in [event-first-sync](docs/event-first-sync.md); it is not a complete
automatic website adapter.

The worker includes organized/co-organized, Going, Interested, Invited and incoming
pending/confirmed stays. It runs at most hourly, then closes Chromium. The separate
loopback server only reads completed ICS snapshots. Website failures never mean deletion.

## Install

From this project directory on macOS:

```sh
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes -r requirements.lock
python -m pip install setuptools wheel
python -m pip install --no-deps --no-build-isolation .
python -m playwright install chromium
couchsync setup
couchsync login
couchsync scraper inspect
```

Install a current setuptools first if your Python environment lacks a build backend:
`python -m pip install setuptools wheel`. For Windows use
[these instructions](docs/installation-windows.md).

Complete the [authenticated selector inspection](docs/selectors.md), then:

```sh
couchsync scraper check
# A live check counts as a scrape attempt; wait the configured interval before another.
couchsync sync --dry-run
couchsync sync
couchsync preview
couchsync service install
couchsync service start
couchsync calendar url
```

Do not install/start background services before the first validated sync. CLI `--config`
is a global option, placed before the command. Non-secret configuration lives in the
platformdirs user configuration directory; data and logs have separate directories.
`couchsync doctor` reports safe readiness booleans. `status` reports counts and last success.

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
not live selectors. CI runs Python 3.13/3.14 on macOS and Windows, secret scanning and
vulnerability auditing. See [dependency updates](docs/dependencies.md).
