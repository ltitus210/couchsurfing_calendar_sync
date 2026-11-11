# Optional inspection and website-layout repairs

New installs use built-in shared defaults after login. No initial inspection or
account-specific profile is required. Existing `selectors.toml` or configured selector
files take precedence and are never overwritten by setup or an update.

## When to inspect

Update Couchsync first if scraping starts failing after a website change. If it still
fails, run:

```sh
couchsync scraper inspect
```

| Window | Action |
|---|---|
| Chrome | Open the failing event tab, event details or incoming stay request. |
| Playwright Inspector | Leave paused while inspecting. **Pick Locator → click the element → copy the locator** if requested. Turn the picker off to navigate. |
| Terminal | Wait. Finish by clicking **Resume ▶ in Inspector**; Chrome closes and the prompt returns. |

`login` is different: authenticate in Chrome, then type `SAVE` in Terminal.
Use your existing `--config` argument for either command when applicable.
Inspection saves the session but does not automatically rewrite selectors. Do not change
RSVPs, send messages or accept/decline requests to obtain examples.

## Shared defaults and coverage

The versioned defaults in `couchsync.scraper.defaults` use the November 2026 English layout:

- Going, Interested and Organizing tabs, scoped event cards and structured Event JSON-LD.
- Invited, when that tab is available; otherwise a diagnostic note and preserved data.
- Messages → Chats / Chat Requests → Stays → Pending / Confirmed. Hosting uses assumed
  incoming panel labels/controls with positive host-direction checks. “Your Request” and
  “View Your Trip” are excluded. Host acceptance alone remains pending.
- Explicit English empty-state captions; no timeout is interpreted as an empty list.

Incoming hosting, invitation/empty states and other languages still need live validation.
Unrecognized hosting panels are skipped with `source_notes`; event sources can still update.
The adapter never reads private conversation bodies for calendar data or clicks request actions.
All defaults use observation mode: missing records stay and full-list coverage is unverified.
Hosting checks at most 20 observed chats per run; this is not complete inbox traversal.

## Maintainer: apply a repair

Prefer updating shared defaults and fictional regression fixtures so every user benefits.
For a local override only, export an editable profile:

```sh
couchsync scraper export-defaults
```

This creates a private selector file and refuses to overwrite one. It does not inspect
or discover selectors. Edit it against the failing page, then choose **one** live sync,
check or dry-run after the hourly guard permits. Remove an exported override only when you
intend to return to package defaults. A missing explicitly named custom file is an error;
an absent default `selectors.toml` selects the bundled profile.

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
| `completion = "observed"` for structured events / guarded incoming stays | `complete: false`, `observations_only: true`; individual observed records can update | Retained; list completeness and absence-based changes are unverified |
| Validated generic explicit end markers | Complete under that source's inspected paging policy | Retained unless an inactive state is explicitly verified |

Observation mode removes fixed positive-count restrictions but does not turn a stable
rendered list into proof of completeness. An empty tab still requires a verified explicit
empty marker; contradictory empty/record states fail. Required event/auth/parser failures abort
the batch; unrecognized optional hosting panels are reported and skipped. Complete-source checks remain necessary for sources claiming
full coverage. [Upgrade behavior and limits](hourly-events.md) explain observation mode.

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
