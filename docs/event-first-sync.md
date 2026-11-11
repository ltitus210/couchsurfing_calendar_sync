# First event sync: the maintainer handoff and the user's next commands

For a first installation, follow [the guided macOS setup](setup-macos.md). In particular,
[Chrome/Inspector actions](setup-macos.md#3-inspect-the-website-in-chrome-and-playwright-inspector)
and [the configuration handoff](setup-macos.md#4-stop-for-the-configuration-handoff) must be
completed before the commands below. Opening Inspector does not configure synchronization.

## Before running anything here

A maintainer must have supplied `events-first.toml` and its referenced selector file in
the private application directory. These are account-specific files outside Git. The setup
wizard does not create them, and `upgrade-events` cannot create a missing initial profile.
The maintainer must identify the exact path, scope and privacy settings.

The inspected scope is Going, Interested and Organizing. Invitations were not visible in
the inspected tab group, and no incoming-hosting sample was available. Those features remain
unverified. Outgoing “Your Request” stays are excluded. Do not create fake requests for tests.

If Inspector is still paused after the maintainer finishes, click **Resume ▶** there.
That saves the session, closes its Chrome window and returns to the Terminal prompt.
Do not type login's `SAVE` response into an inspection session.

## Install the current code in the working checkout

Bring source changes into this checkout using your normal Git workflow first. In the
existing working checkout and its environment:

```sh
cd "$HOME/scripts/couchsurfing/couchsurfing_calendar_sync"
source .venv/bin/activate
python -m pip install --no-deps --no-build-isolation -e .
```

Copy the full install command, including the dot after `-e`. The source checkout used for
Codex/GitHub edits is separate from this installed checkout; installing the old working
copy does not pick up changes sitting only in the source copy.

## Run one live sync

```sh
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" sync
```

**Expected for the original bootstrap profile:** `result: success`, plausible category
counts, `complete: true` and `coverage: inspected-count event lists`. A positive count
is an operator assertion about a known list, not general proof of pagination completeness.
Changed counts stop that profile; do not raise them blindly or install an hourly worker yet.

**Expected for an already-upgraded profile:** `result: updated_observations`,
`observations_only: true`, `complete: false`. This is a successful update of verified
observations, with missing entries preserved. It does not claim complete source coverage.

**If `not_due`:** wait until the configured interval, normally an hour after the most recent
attempt, has elapsed. Failed attempts/checks/dry-runs count too. Do not run check, dry-run
and sync one after another or reset the guard. If a maintainer asks for a dry-run first,
that is a separate live attempt and does not create the ICS snapshot.

**If an error appears:** stop and use [troubleshooting](troubleshooting.md). Authentication,
page structure, malformed dates or mismatched details must not be interpreted as missing events.

## Preview locally, then check Calendar

```sh
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" preview
```

Preview does not visit Couchsurfing. Verify event counts, prefixes and dates. It prints
starts in UTC: `2026-11-13T00:00:00+00:00` is November 12 at 7 PM in America/New_York.
Check local start/end times and multi-day spans in Calendar too.

**Next:** [serve and subscribe](setup-macos.md#6-serve-the-feed-and-subscribe-in-apple-calendar).
A successful sync saves a file but does not start the HTTP server. `serve` must stay running
in one terminal while a second terminal checks HTTP 200 and Calendar subscribes.

**After the subscription displays correctly:** [upgrade and test once](setup-macos.md#7-upgrade-the-event-profile-for-changing-lists),
then [start background services](setup-macos.md#8-start-background-services). The upgrade
backs up the old selector file, supports changing positive list sizes, and explicitly leaves
full-list completeness unverified. Read [the limits](hourly-events.md) before unattended use.
