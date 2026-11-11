# Existing event-first profiles

**New installation?** Use [quick start](setup-macos.md). Built-in defaults need no initial
inspection, supplied profile or fixed-count upgrade.

This page is only for older custom `events-first.toml` configurations. Keep their existing
configuration argument; updating the code does not overwrite private selector files.

## Upgrade an older fixed-count profile

After updating the project, run:

```sh
source .venv/bin/activate
python -m pip install --no-deps --no-build-isolation -e .
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" scraper upgrade-events
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" sync
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" preview
```

**Look for:** `upgraded` or `already_upgraded`, followed by `updated_observations`.
If sync returns `not_due`, wait until an hour after the previous attempt. Preview is local.
The upgrade saves a backup and removes fixed positive counts; missing entries remain retained.
Built-in defaults return `already_current` because no migration is needed.

Check titles and dates, then [subscribe](setup-macos.md#4-apple-calendar) and
[enable services](setup-macos.md#5-background-services), using the same custom configuration
argument throughout. No new inspection or duplicate Calendar subscription is required.

`complete: false` is expected in observation mode. It does not prove full-list coverage.
Do not raise bootstrap counts just to make a run pass. [Update limits](hourly-events.md).
