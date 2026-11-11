# Validation record — November 10, 2026

This record distinguishes automated checks, live inspection and user-reported results.
A working local calendar does not prove every source category, platform or client works.

## Current checkpoints

| Checkpoint | Evidence | What it does not establish |
|---|---|---|
| Account-specific Going/Interested/Organizing extraction | User reported the guarded live sync and an updated observation-mode sync | Other accounts, all RSVP transitions, invitations, full paging/completeness |
| Local Apple Calendar | User confirmed subscription and displayed events/local times | iCloud, iPhone/iPad, remote HTTPS or Google Calendar |
| macOS background service startup | User reported install/start/status for both jobs and managed-feed HTTP 200 | A later unattended scrape, session expiry handling or sleep/wake execution |
| Automated code checks | Event-details follow-up: 134 tests passed on Python 3.13.5 / Intel macOS; Ruff/build/secret scan passed | Native Windows runtime, hosted CI or authenticated site correctness beyond live samples |

## Shared defaults: fixture validation, not a new live account run

New installs now use the observed shared event layout without initial inspection.
Incoming hosting labels/controls, English empty captions and an optional Invited tab are
explicit assumptions. Fictional Chromium fixtures verify populated/empty event tabs,
Invited present/absent, incoming pending/confirmed stays and outgoing classification without
clicking request actions. Database checks verify pending-to-confirmed UID preservation
and retention when a later observation omits the stay. Existing override files take priority.
No additional authenticated live scrape was performed for this change.

## User-reported live sequence

1. The inspected account's Going, Interested and Organizing lists were examined. Event
   detail pages exposed structured Event JSON-LD. No reliable total/end marker was found
   in the inspected list metadata. An Invited tab was not present in that tab group.
2. A supplied guarded profile produced Going 4, Interested 1 and Organizing 1 in 28.58
   seconds with 1,446 aggregate attempted browser requests. Its exact inspected counts
   were a bootstrap safeguard, not universal proof of full-list completeness.
3. Preview displayed six entries in UTC. The user confirmed the local Apple Calendar
   subscription and event display after starting the publisher. The earlier connection
   failure was diagnosed as no server listening on port 8765 while the saved snapshot existed.
4. After profile upgrade, the user reported `updated_observations`, `complete: false`,
   `observations_only: true`, the same category counts, 799 attempts, 241 allowed and 558
   blocked requests in 20.8 seconds. These are one account/run's results, not a guaranteed budget.
5. The user reported `sync: active` / `serve: active` after native macOS install/start/status.
   A HEAD request returned HTTP 200, text/calendar and a 2,456-byte saved feed. This confirms
   loaded definitions and publisher availability. It is not yet evidence of the next hourly run.

The pending-stay sample opened during setup was an outgoing “Your Request” accommodation
request, excluded by the original incoming-only implementation. The November 11 update
now includes outgoing stays using that observed direction evidence. No incoming pending or confirmed stay sample
was available. Those categories remain unverified; no request was created or changed for testing.

## Automated checks actually performed

Initial checks passed on Python 3.13.5 and 3.14.5 with 38 tests; the structured-event follow-up
passed 60 tests on Python 3.13.5. The latest observation/traffic/service follow-up passed
**74 tests on Python 3.13.5 / Intel macOS**. The shared-defaults follow-up passed
**97 tests on the same environment**. The expanded suite has not been claimed
as executed on every supported OS/Python combination.

Coverage includes:

- Real Chromium against synthetic/intercepted pages: parser, empty/unknown-state failure,
  navigation, HTTP 429 stop behavior, same-tab navigation, metadata identity waiting,
  changing observed counts, duplicate detail reuse and blocked media transfers.
- Loopback feed HTTP: allowlisted paths, HEAD, ETag/304 caching and traversal rejection.
- SQLite: UID/sequence/idempotence, rollback, missing-record retention, observation updates,
  organizer-membership preservation, mass-cancellation safeguards and backup/CLI restore.
- ICS round-trip through icalendar: statuses, hosting date policies, Unicode/folding,
  UTC/IANA/DST validation, exclusive checkout, missing dates, feeds and privacy filtering.
- Session encryption/tampering/logout and rejection of unsupported credential backends.
  Live successful syncs demonstrate usable native session/key storage under the logged-in
  macOS account; controlled native-store fault/logout tests and Windows store access are separate.
- Mock-transport WebDAV publication/MOVE/failure/revocation. No live remote host was provisioned.
- Scheduler definitions and an isolated publisher-only install test. Real macOS startup
  evidence is the user report above, not the mocked definition test.
- Reversible/idempotent profile migration and query-sensitive generic detail identities.

Ruff, source-distribution/wheel packaging and checksum-verified Gitleaks scans passed.
The locked runtime dependency audit found no known vulnerabilities when checked during
implementation. Synthetic fixtures are fictional; no private authenticated captures were
committed. Tests that use intercepted pages do not contact the live Couchsurfing account.

## Outstanding validation

- At least one subsequent unattended hourly observation run, followed by saved status/log
  confirmation. Loaded launchd jobs or HTTP 200 alone do not prove that run succeeded.
- macOS sleep/wake timing and unattended native credential-store behavior when locked/expired.
- Invitations, incoming/outgoing stay direction, pending/intermediate/mutually confirmed stay
  statuses, cancellations, missing dates and all intended real account state transitions.
- Complete event-list pagination/infinite scrolling and reliable evidence for missing-RSVP
  reconciliation. Observation mode explicitly leaves full-list completeness unverified.
- Windows task registration/execution and native credential storage; other macOS architectures
  beyond the tested machine; reviewed hosted CI results.
- Actual remote HTTPS WebDAV authorization/atomic publication/revocation and Google Calendar,
  iCloud/iPhone/iPad subscriptions. Local Apple success does not establish these.

## Limits that remain by design

Missing records do not cause cancellation; explicit inactive states are required. Observation
mode can update individually validated records without claiming every source record was retrieved. Empty
tabs need a verified explicit empty marker; failed selectors cannot mean “empty account.”
Source/history records remain locally until data is removed; retention limits feed history.

Snapshots are replaced atomically per file, not in one transaction across all feeds and
remote servers. Database commits may succeed while publishing fails; `calendar publish`
retries a completed snapshot without scraping. ICS library round-trip/field checks are
not independent RFC certification. No general production-readiness claim is made from the
limited live account/client evidence above.

## November 11: surfing, explicit labels and source links

The stays adapter now includes outgoing pending/confirmed stays. Dedicated “Your Request” /
“View Your Trip” metadata identifies surfing; host acceptance alone remains pending.
Calendar entries identify Event, Hosting Request or Stay and include the source URL in
Full/Limited modes. Busy/Private/Generic URL redaction is tested. No new authenticated live
scrape was performed; incoming and confirmed layouts still need live validation.
The full 117-test suite passed on Python 3.13.5 / Intel macOS, including read-only
Chromium fixture navigation for both directions, outgoing accepted/confirmed states,
stable pending-to-confirmed UIDs, distinct direction identities, feed filtering, event
labels, source links and all privacy modes.

## November 11: event postal addresses and About updates

Event `LOCATION` now includes available structured postal fields alongside the venue.
Structured descriptions (About) are converted from HTML to plain text. Both appear in
default Limited event feeds and Full feeds; Generic/Busy/Private modes hide them.
Fixture browser tests verify address/About changes and removal across repeated scrapes,
stable UIDs, sequence updates and unchanged-record idempotence. No additional authenticated
live scrape was performed; structured postal-address variations remain fixture-validated.

The expanded **134-test suite passed on Python 3.13.5 / Intel macOS**. Ruff, packaging,
documentation checks and the secret scan also passed.
