# Troubleshooting: find the failed checkpoint

If you are unsure what to do next, use the [setup stage finder](setup-macos.md#already-installed).
Do not restart the whole installation for a later-stage error. Use the same config file
for sync, preview, serving and services; new installations use the built-in profile.

## Installation

| Symptom | Meaning / next action |
|---|---|
| `-e option requires 1 argument` | Use the whole command `python -m pip install --no-deps --no-build-isolation -e .`; the dot names the project folder |
| Reinstall succeeds but a new command is missing | Update the project and reinstall in its active `.venv` |
| `couchsync` not found or wrong code appears to run | Activate the project's `.venv`; check `python -c 'import sys; print(sys.executable)'` |
| Both `(.venv)` and `(base)` appear | That alone is not an error; verify the interpreter path rather than the prompt decoration |

## Chrome, Inspector and login

| Symptom | Meaning / next action |
|---|---|
| Chrome and Playwright Inspector opened and nothing happens | Normal: inspection is paused. Navigate in Chrome; follow [the browser walkthrough](setup-macos.md#if-the-website-changes) |
| Unsure where to type `SAVE` | Only at the Terminal prompt for `couchsync login`, after website authentication |
| Need to finish `scraper inspect` | Click **Resume ▶ in Inspector**; it saves the session, closes Chrome and returns Terminal's prompt |
| Resume closes Chrome unexpectedly | Expected behavior: it finishes inspection, not just the current website action |
| Clicking an element picks it rather than navigating | Turn off Pick Locator to use the website normally |
| Logged into everyday Chrome but inspection asks for login | The Playwright browser uses an isolated session; complete the normal login flow there |
| No incoming hosting example exists | No initial inspection is required; the guarded shared layout can be used, with live hosting validation still outstanding. Do not manufacture a request |
| Pending Stay says Your Request / View Your Trip | That is an outgoing accommodation request, excluded from incoming-hosting scope |

If live support cannot read the open window, the maintainer may need normal screen/accessibility
permission for the support tool. Completing that permission does not configure Couchsync or
change the scraper's selectors. Keep the requested Chrome page open while support retries.

## Missing configuration and live-run results

| Symptom | Meaning / next action |
|---|---|
| No selectors configured / selector file missing | An absent default `selectors.toml` uses built-in defaults. A missing custom file must be restored, or remove the custom `selector_file` setting to use defaults |
| `events-first.toml` does not exist | That is a legacy custom profile, not wizard output. New installs can use `couchsync sync` without it |
| `upgrade-events` cannot find/upgrade a profile | Only older custom event profiles need migration. New defaults are already current |
| `not_due` | A sync/check/dry-run, including a failed one, happened within the configured interval. Wait normally one hour from that attempt; do not reset timestamps |
| `updated_observations`, `complete: false` | Expected successful observation update with unverified full-list coverage; missing records remain preserved |
| Event count differs from inspected profile | Fixed-count bootstrap safety check. Re-inspect if unexpected; after a validated first run, use the documented profile upgrade rather than guessing counts |
| Empty tab without a verified empty marker | Stop and ask for adapter inspection. A missing selector cannot be accepted as an empty account |
| Unknown status, wrong detail identity, missing fields, incomplete pagination | Required validation failed. Preserve the good feed and inspect the failed component; do not weaken checks just to pass |
| High request total | Includes browser assets. Review attempted/allowed/blocked counts and types; do not repeatedly scrape to measure |

Choose one live validation command: `scraper check`, `sync --dry-run`, or `sync`. They
are not consecutive required setup steps. Checks and dry-runs do not write snapshots;
`sync` does on success. Local preview, status, logs and serving can be used without another
Couchsurfing visit.

## Preview, calendar dates and HTTP availability

- `+00:00` in preview is UTC. For example, November 13, 2026 at 00:00 UTC is November 12
  at 7 PM in America/New_York. Verify local start/end times and multi-day spans in Calendar.
- HTTP `Date`/`Last-Modified` are GMT/UTC, so a next-day header date can be correct locally.
- A valid snapshot and a successful preview do not mean the HTTP publisher is running.

For “The request for http://127.0.0.1:8765/couchsurfing.ics failed,” first run:

```sh
curl --noproxy '*' -I http://127.0.0.1:8765/couchsurfing.ics
```

| Result | What to check |
|---|---|
| Connection refused | Start `serve` with the same profile in another terminal and leave it running, or check/start the managed publisher |
| HTTP 200 + text/calendar | Feed is available; retry the subscription using the plain URL and On My Mac location |
| HTTP 503, no completed snapshot | Ensure a successful `sync` produced the configured data snapshot; a dry-run alone is not enough |
| HTTP 404 | Use `/couchsurfing.ics` for the enabled combined feed; check configured feed selection and URL |
| Port/address already in use | A manual server or managed publisher may already own port 8765. Use the existing valid publisher instead of starting another |

If a manual server is used, it normally holds the terminal without returning a prompt;
older versions print nothing. If it exits, read the error. Confirming Calendar's local HTTP
permission prompt does not start or repair the server. See [Apple Calendar](apple-calendar.md).
Do not disable TLS/certificate checks as a general troubleshooting step.

## Background services and freshness

`service install` writes definitions; `service start` loads them; `service status` queries
them. Do not repeatedly install/start already-loaded jobs. If both say active, check HTTP
200 for the publisher and saved `status`/`logs` after an hour for the worker.

“Active” means loaded in launchd, not that the one-shot worker is constantly scraping or
that a scheduled sync succeeded. Keep a manual server open only until its managed publisher
replaces it. Stop manual `serve` with Ctrl-C before starting the managed publisher; after
both jobs are loaded and HTTP 200 works, terminals can be closed.

Use `--task serve` to manage only the publisher or `--task sync` for only the worker.
The default is both. If the interpreter/config path moved, stop/uninstall the affected
job, reinstall it from the intended working environment and start it again. This is not
necessary for every code update. For ordinary code updates, stop jobs before reinstalling
and start them afterward so the persistent publisher uses the updated code too.

## Other failures and safe reports

- Expired login, MFA/CAPTCHA, HTTP 401/403/429: stop and reauthenticate normally or follow
  website restrictions. Do not bypass protection. Previous data/snapshots are retained.
- Native Keychain/Credential Manager unavailable: run as the logged-in user with the store
  available. Insecure fallback keyrings are refused; do not move secrets into TOML.
- HTTP 5xx navigation gets at most two bounded retries. Other network failures abort.
- Lock timeout: another worker/backup/restore may be running. Lock files can remain after
  exit while the OS lock has been released. Do not run competing installs for one account.
- Missing hosting dates remain in diagnostics; do not invent arrival/checkout dates.
- Ambiguous/nonexistent DST times require an explicit source offset, not machine-local guessing.
- Remote WebDAV failure: `calendar publish` can retry a completed snapshot without scraping.
- Client refresh delays are separate from worker timing. Check publisher availability and
  last successful sync before replacing subscriptions. Remove duplicate imports/old URLs.

`doctor`, `status` and `scraper diagnostics` summarize readiness; `auth status` proves only
local session decryptability, not online authentication. Review output before posting.
Public reports should contain version/OS/Python, sanitized counts and the failure component,
not cookies, tokens, names, private URLs/messages, raw HTML, screenshots, databases or feeds.
