# Troubleshooting

Run `doctor`, `status`, and `scraper diagnostics`. These are safe readiness summaries,
not proof of a valid online login. `auth status` proves only local decryptability.
`auth refresh` opens a new interactive login; unattended workers never request a password.

- No selectors configured: use scraper inspect and docs/selectors.md. Synthetic selectors
  intentionally do not represent Couchsurfing. There is no automatic guessed fallback.
- Missing/changed field, unknown status, missing empty/end marker: stop and inspect. Every
  relevant source must be complete before changes are applied. Never weaken checks merely
  to obtain a green result. Unknown statuses are failures, not cancellations.
- Hosting request has no arrival/checkout: retained in diagnostics counts, omitted from ICS.
- Ambiguous or nonexistent DST time: extract a source UTC offset. Machine-local time is not used.
- Expired login, access restriction, MFA, CAPTCHA, HTTP 401/403/429: stop; reauthenticate
  interactively or follow the website's restrictions. Do not bypass protection.
- Transient HTTP 5xx navigation: at most two retries with 2s and 4s backoff. Other network
  failures abort and preserve data. The persistent attempt guard prevents rapid retries.
- `not_due`: an attempt (including failed runs/check/dry-run) happened within the configured
  interval. Wait before trying again. Do not delete the guard to poll the website.
- Lock timeout: another worker/backup/restore is running. Lock files may remain after exit;
  filelock releases the OS lock on crash. Do not run multiple installations for one account.
- WebDAV failure: local snapshots remain available. A later `calendar publish` retries the
  completed file without scraping. Atomic MOVE is required by default. Verify server rights.
- Client lag/duplicates: check server ETag, publication and client subscription refresh;
  remove duplicate imports/old subscriptions. Google/Apple refresh timing is independent.
- Keychain unavailable: run while logged in and unlock your native store. Insecure keyring
  backends are rejected. Never work around this by writing keys or passwords to disk.

For public issues include version, OS/Python version, aggregate diagnostics and the failure
component. No page HTML, screenshots, source URLs, guest names, databases, cookies or feed
URLs. For additional debugging use Inspector locally; no raw captures are uploaded.
