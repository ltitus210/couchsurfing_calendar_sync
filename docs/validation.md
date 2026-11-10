# Validation report — November 10, 2026

## Executed locally

- Python 3.13.5 on Intel macOS: **38 tests passed** (no skips).
- Python 3.14.5: full suite also executed; see delivered implementation report for final count.
- Real Playwright Chromium: synthetic DOM parsing, explicit empty detection, unknown-status
  failure, intercepted website navigation and HTTP 429 stop behavior. No Couchsurfing
  credentials were used and intercepted tests never contact Couchsurfing.
- Local loopback HTTP: feed allowlist, content, HEAD, ETag/304 caching, traversal rejection.
- SQLite: idempotence, UID/sequence transitions, rollback, missing-record retention,
  suspicious mass-cancellation prevention, backup and CLI restore.
- Calendar round-trip through icalendar: organized, Going, Interested, Invited,
  pending/confirmed stays, cancellations, Unicode/folding, offsets/DST validation,
  exclusive checkout and same-day stays, missing dates, separate feeds and privacy.
- Fernet encrypted session round-trip, tampering rejection, logout and rejection of
  unsupported credential backends. Native Keychain/Credential Manager CRUD not exercised.
- WebDAV mocked transport: MKCOL/PUT/MOVE, failure keeps previous remote file, token URL
  revocation and revoked-token publication blocking. No real hosting was provisioned.
- Scheduler definitions: macOS plist round-trip, interval/wake trigger/independent server;
  Windows XML least-privilege user, repetition, catch-up and concurrency settings.
- Ruff lint passed. Wheel and source-distribution build passed.
- Runtime dependencies hash-locked universally for Python 3.13+; Windows backend dependency
  included. pip-audit found **no known vulnerabilities** in the locked dependencies.
- Official checksum-verified Gitleaks 8.30.1 directory scan: **no leaks found**.

## Requires authenticated/manual validation

**The live Couchsurfing adapter is not complete until an account owner inspects and
configures current selectors.** No working production DOM selectors are claimed or shipped.
Scraper inspect provides a visible browser/Inspector; check performs a locked, rate-limited
dry run. Website access restrictions, social login, MFA, full pagination, incoming-only
scope, organizers, all RSVP states, accepted-but-unconfirmed stays and final confirmed
stays must be validated with real account data. See selectors.md. Automation never accepts
requests, sends messages or bypasses access controls.

Apple Calendar macOS/iCloud/iPhone and Google Calendar subscription behavior require manual
client testing. ICS library round-trip and standards-oriented field checks are not a claim
of an independent RFC certification or a successful client integration test.

Native launchd registration/start/stop and sleep/wake execution were not performed.
Windows registration and runtime were not executed locally. Native credential storage
unattended access must be checked under the actual logged-in account. Actual remote HTTPS
WebDAV authorization, atomic MOVE, URL revocation and Google/Apple retrieval are pending.
CI is configured for macOS/Windows and Python 3.13/3.14; it has not run on a hosted repository.

## Deliberate conservative limitations

Missing records never cause cancellation, even after a complete list. Explicit inactive
states are required. This avoids interpreting list filtering or website changes as decline.
Conflicting duplicate details abort the batch. User-provided completeness selectors require
maintainer judgment. Source/history records remain locally until data is removed; feed
retention limits published history, not database retention. Multi-feed file replacements
are atomic per file, not a single transaction across every feed or the remote server.
Local database commits may succeed while publishing fails; calendar publish retries the
last completed snapshot without another scrape. No production-readiness claim is made
before the outstanding authenticated/client/platform checks are completed.

## Follow-up: first live calendar and observation-mode preparation

The user reported a successful exact-count live run on November 10: Going 4, Interested 1,
Organizing 1, 28.58 seconds, 1,446 aggregate browser requests. The user also confirmed the
local ICS subscription and event display in Apple Calendar. This validates that narrow
bootstrap flow, not every source state, account, device or client.

The follow-up implementation adds media blocking, same-tab navigation, shared detail
extraction, changing-count observation updates and a backed-up local profile migration.
It explicitly reports full-list completeness as false; no reliable total/end marker was
found in the inspected live list metadata. Actual optimized request counts, native service
activation, invitations, incoming hosting, Google Calendar and full-list reconciliation
still require validation. Synthetic browser tests do not substitute for those checks.

Latest local follow-up verification: Python 3.13.5 on Intel macOS, **74 tests passed**,
Ruff passed, source/wheel packaging passed, and Gitleaks found no leaks. New tests cover
changing observed counts, preserving missing records and UIDs, explicit cancellation
guards, profile backup/idempotence, SPA navigation/detail reuse, media-transfer blocking,
account restriction handling and query-sensitive generic detail identities. Optimized live
request counts and native service activation are still pending.
