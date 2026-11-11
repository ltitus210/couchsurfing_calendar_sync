# Chrome and Playwright inspection: user handoff and maintainer reference

## If you are setting up your own account

Use [the browser walkthrough](setup-macos.md#3-inspect-the-website-in-chrome-and-playwright-inspector)
for the exact actions in each window. Opening `scraper inspect` is not an automatic setup step.
It pauses the program so a maintainer can inspect the real website while you are logged in.
You are not expected to invent or program selectors yourself.

| Command | What happens | How you finish it |
|---|---|---|
| `couchsync login` | Chrome opens for normal interactive login | Return to Terminal, type `SAVE`, press Return |
| `couchsync scraper inspect` | Chrome and Playwright Inspector open; Terminal waits | Leave Inspector paused during the inspection, then click its **Resume ▶** button |

For an existing event-first profile, place
`--config "$HOME/Library/Application Support/couchsync/events-first.toml"` before either command.
Do not substitute your everyday browser: the isolated Playwright browser has the session
being inspected. If support cannot connect to it, the optional Pick Locator workflow is
explained in the walkthrough. A URL alone is not enough to validate the authenticated DOM.

Open **Events → View Your Events → Going**, an event's details, then Interested and
Organizing. Confirm which tab is actually selected; the page title or URL can lag during
navigation. Report missing tabs and explicit empty states rather than guessing. Do not
change RSVPs, send messages or accept/cancel requests to obtain fixtures.

For incoming-hosting validation, the account owner must be the prospective host.
**Pending Stay** can describe an outgoing request too. “Your Request,” “View Your Trip,”
or “Waiting on [another person] to accept” identified the outgoing example in this setup.
If no incoming example exists, record that limitation and continue only with an agreed,
explicitly limited event profile. No fabricated request is needed.

**The handoff is complete only when a maintainer has supplied/checked the account's
configuration and selector file.** Pressing Resume saves the session and closes Chrome;
it does not create selectors. Stop at [the configuration handoff](setup-macos.md#4-stop-for-the-configuration-handoff)
if those files do not exist. Synthetic test files are not settings for a real account.

## Maintainer: observations from the inspected website

No undocumented API endpoints or unobserved website selectors are asserted here. On
November 10, 2026 the account's event tabs included Going, Organizing, Interested and Past;
an Invited tab was not found in that view. Event details exposed
`script[data-testid="hangout-json-ld"]` with structured Event data, including a canonical
stable identifier and explicit UTC start/end timestamps. The narrow event profile has now
been exercised by the user; this is not evidence for all accounts or every state.

Couchsurfing's current host guide describes Home → Your Guests → the traveler chat →
View Request. Host acceptance is followed by traveler confirmation. An accepted chat or
host-only acceptance must not be interpreted as a mutually confirmed stay. Incoming pending
and confirmed stays still lack a live sample in this account's validation.

[Official host-request guidance](https://support.couchsurfing.org/hc/en-us/articles/50055202137115-How-Do-I-Receive-and-Manage-Stay-Requests-A-Guide-for-Hosts).

## Maintainer: profile creation is a manual prerequisite

`setup` creates general `config.toml` settings. It does not create `selectors.toml`,
`events-first.toml`, or `events-first.selectors.toml`. `upgrade-events` only migrates an
existing compatible event profile. There is no command in this release that discovers
selectors and completes this handoff automatically.

1. Inspect the authenticated-only navigation and each enabled account list. Determine
   incoming-only hosting scope separately. Collect only fields required for the calendar.
2. Create a non-secret configuration selecting only verified categories. For the staged
   event workflow, use a separate `events-first.toml` beside the main config, sharing the
   established session/data locations, and leave remote publication unconfigured during
   initial testing. Do not silently change the main configuration's requested scope.
3. Point `selector_file` at the chosen selector profile. It is relative to the configuration
   directory unless absolute; its default is `selectors.toml`.
4. Author the profile below and validate it against observed pages. A positive first-sync
   count must come from inspection, never a number selected to make a run pass.
5. Give the account owner the exact configuration path, categories, privacy settings,
   coverage policy and **one** next live command. They should not have to infer a sequence
   from `setup`'s terse list of possible commands.

### Generic selector-profile contract

Use the structure of `tests/fixtures/selectors.synthetic.toml` only as a schema reference.
Its selectors are deliberately fictional. Never copy them as a production adapter.

| Setting | Meaning |
|---|---|
| `validated_on`, `auth_marker` | Inspection note/date and a marker establishing the required logged-in page context |
| One `[[sources]]` per enabled category | Actual observed `url`, `category` and `kind` |
| `container`, `item` | Expected page scope and record selector; scope to the intended list, not nearby/public events |
| `incoming_marker` for hosting | Evidence that this is an incoming-hosting source |
| `fields` and `statuses` | Exact observed field extraction and raw-status → internal-status mapping |
| `empty`, `end` for complete generic sources | Explicit empty and completion evidence; missing pagination controls are not proof of completion |
| `next` or `scroll`, `max_pages` | Inspected paging behavior and a bounded traversal limit |
| `detail_link`, `detail_container` | Inspected relative link and scope for required detail-page fields |

Field specifications use a relative `selector`, optional `attribute`, optional full-match
`pattern` with capture group 1, and optional `format` for observed date text. `date_only`
produces an ISO date. Missing date elements can be `optional = true`; without adequate
dates, the record stays in diagnostics rather than receiving an invented calendar date.
Timed dates require explicit offsets or valid IANA timezone handling. Use immutable source
IDs, not titles or dates. Map account RSVP/host states, not a public event lifecycle label.

### Structured event profiles and completeness policies

For the inspected event-detail route, `event_json_ld` selects the structured Event script
instead of a `fields`/`statuses` map. The parser verifies canonical identity, lifecycle and
dates. Same-tab navigation checks metadata identity after clicking a normal event link;
`tab_label` identifies an inspected in-app tab. These features are not an API client.

| Policy | What may be reported | Missing entries |
|---|---|---|
| Inspected positive `expected_count` | Guarded bootstrap batch matching a manually inspected count; exact count changes stop it | Retained; this is not universal pagination proof |
| `completion = "observed"` for structured events | `complete: false`, `observations_only: true`; individual observed records can update | Retained; list completeness and absence-based changes are unverified |
| Validated generic explicit end markers | Complete under that source's inspected paging policy | Retained unless an inactive state is explicitly verified |

Observation mode removes fixed positive-count restrictions but does not turn a stable
rendered list into proof of completeness. An empty tab still requires a verified explicit
empty marker; contradictory empty/record states fail. A page/auth/parser failure aborts
the batch in all modes. Complete-source checks remain necessary for sources claiming
full coverage. [Upgrade behavior and limits](hourly-events.md) explain the event-only mode.

## Validation and safe reports

Choose **one** of `scraper check`, `sync --dry-run`, or `sync` for a live validation attempt.
Check and dry-run validate without writing a calendar snapshot; `sync` writes snapshots on
success. They all share the hourly guard, including failed attempts. Preview is local and
can be repeated without another website request.

Validate real empty lists, paging/infinite scrolling, all intended states and transitions,
source identity, dates and expired authentication before claiming that coverage. Current
synthetic browser tests test mechanisms, not uninspected live selectors. Do not infer
confirmed hosting from conversation text or scrape unnecessary private messages.

Keep profiles and any debugging artifacts local with restrictive permissions. No raw HTML,
screenshots or sessions are automatically uploaded. Public issues should contain sanitized
counts, version/platform and the failing component, not names, cookies, private URLs,
conversations, raw HTML, calendars or databases. Use fictional regression fixtures.
