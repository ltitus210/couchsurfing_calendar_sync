# Guarded event-only first sync

The original setup stopped at a developer Inspector without configuring a website
adapter. Opening that window was not enough to make synchronization work.

The November 10 inspection found the Going, Interested and Organizing lists and
`script[data-testid="hangout-json-ld"]` on an event detail page. The structured Event
contains canonical URL, title, explicit UTC start/end timestamps, lifecycle status,
location and description. The new parser selects only these fields and never evaluates
JavaScript. Source identity uses the immutable `_ho` identifier, not the title slug.

A separate local `events-first.toml` profile can point to
`events-first.selectors.toml` with the inspected categories and exact positive list
counts. This preserves the user's main configuration and encrypted session location.
`selector_file` is relative to the configuration directory unless an absolute path is used.
No account-specific selector profile or list counts are committed to the public repository.

This is a narrow bootstrap profile, **not a generally validated automatic scraper**.
An inspected count is an operator assertion about a known list, not proof of pagination
completeness for an arbitrary account. Do not invent or increase counts to make a run pass.
The run requires the selected tab panel, precise count, unique source IDs and all detail
pages to validate. Any mismatch stops the entire batch before calendar snapshots are
replaced. Missing/empty lists are not accepted by this profile. The explicit-empty/end
adapter remains available for fully validated sources. Missing records never cause deletion.

Invitations were not found in the inspected tab group; incoming hosting had no example.
Those categories remain unverified and are omitted only in this separate first-sync
profile, not removed from the main configuration or from application support.

## Operator handoff

After an operator has created the private profile for the account:

1. Press **Resume** in Playwright Inspector. The inspection command saves the current
   session and closes its Chromium window. No account changes are made.
2. In the existing Python environment, reinstall the project with `python -m pip install
   --no-deps --no-build-isolation -e .` so the command uses the updated code.
3. Run `couchsync --config "<actual path to events-first.toml>" sync` once. This is a local
   snapshot run; the bootstrap profile must omit remote publishing configuration.
4. Run `couchsync --config "<actual path to events-first.toml>" preview` to inspect the
   privacy-filtered event titles/dates without another website request.

Report the safe success summary or failure component. Do not share cookies or storage
state. Failed attempts count toward the hourly guard. Do not immediately retry with a new
browser or reset the timestamp to poll the website. A successful live sync still needs
manual Apple/Google client verification. Do not install background services using this
bootstrap profile until list completion, count-change handling, invitations and required
hosting behavior have been validated for the intended scope.

## After a successful first sync

Use [hourly-events.md](hourly-events.md) to upgrade the local selector profile. The new mode
accepts changing positive counts, reports incomplete list coverage explicitly and never
infers deletion from disappearance. It still needs live validation before unattended use.
The separate publisher service can replace a manually open `serve` terminal independently.
