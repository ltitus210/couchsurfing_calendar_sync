# macOS installation, updates and background services

**First installation:** use [the guided setup](setup-macos.md), which includes the installation
commands, virtual environment, login, first sync,
HTTP check, Calendar subscription and background-service checkpoints. Shared website defaults are included; inspection is only needed for repairs.

Requirements: Python 3.13+, macOS 15+, Intel or Apple Silicon. The primary live setup was
checked on Intel macOS with Python 3.13.5. Keep the project's `.venv` and config
path stable: service definitions embed both absolute paths.

## Which command does what?

Use the same `--config` argument as your successful sync. For the staged event profile:

```sh
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" service status
```

| Action | Effect | When to use it |
|---|---|---|
| `service install` | Writes per-user LaunchAgent files | Once, after live validation; again only when definitions need replacement |
| `service start` | Loads the installed jobs with launchctl | After initial install or a previous stop |
| `service status` | Checks whether definitions are loaded | Readiness/troubleshooting; `active` is not proof of a successful scheduled sync |
| `service stop` | Unloads jobs while preserving definitions/data | Before updating the running environment or pausing work |
| `service uninstall` | Unloads jobs and removes their definitions | Removing services or replacing interpreter/config paths; data is retained |

Default actions target both jobs. Add `--task serve` for only the publisher or `--task sync`
for only the worker. These are actual examples, not slash-separated command syntax:

```sh
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" service status --task serve
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" service status --task sync
```

The files under `~/Library/LaunchAgents` are `org.couchsync.sync.plist` (one-shot worker)
and `org.couchsync.serve.plist` (KeepAlive loopback publisher). No root privileges are needed.
Keychain must be available to the logged-in account; insecure credential backends are refused.

## First start and the manual-server handoff

After one successful observation-mode live run, follow [setup stage 5](setup-macos.md#5-background-services).
Stop the manually running `serve` command with Ctrl-C before starting the managed publisher,
so two processes do not compete for port 8765. Confirm both jobs report active and check:

```sh
curl --noproxy '*' -I http://127.0.0.1:8765/couchsurfing.ics
```

HTTP 200 proves feed availability. Once that works, terminals can be closed and the existing
Apple Calendar subscription stays the same. Do not reinstall/start already-active jobs.
The worker normally exits between runs; a continuously running browser is not expected.
Fixed-count bootstrap profiles are rejected for worker installation; use the documented
[profile upgrade](hourly-events.md) first. Observation mode still has limited coverage.

Native install/start/status and managed-feed HTTP 200 have been reported successfully in
one user setup. The next unattended run and sleep/wake behavior still need verification.
After a full configured interval awake/logged in, inspect `status` and `logs` for a new
successful run. `active` or HTTP 200 alone does not prove that source data is current.

## Later code updates

After updating the project, stop services before changing its environment. Reinstall using the complete `python -m pip install --no-deps --no-build-isolation
-e .` command, then start the services again so the publisher loads the new code. Follow
[dependency update guidance](dependencies.md) when the lock/dependencies changed.

Do not rerun `setup`/login/inspection or add a new Calendar subscription for every ordinary
code update. If the interpreter/config path moved, stop and uninstall the old definitions,
then install/start from the new intended environment. Uninstallation preserves account data;
back it up separately before migrations or destructive maintenance.

## Timing and logs

The local `man launchd.plist` was consulted during implementation. StartInterval can miss
firings during sleep or while a job is running; it does not guarantee wake catch-up.
StartCalendarInterval coalesces missed calendar firings on wake. The worker combines
StartInterval=3600, a top-of-hour calendar trigger and RunAtLoad. A persistent last-attempt
guard limits actual scraping to the configured interval even when triggers overlap;
`not_due` immediately after start can be expected. A filesystem lock prevents overlap.
Longer custom intervals are enforced by the guard. No wake or exact-time execution is promised.

Application logs rotate at 250 KB with three backups. LaunchAgent stdout/stderr files hold
small CLI summaries but are not automatically rotated by launchd. Inspect them locally and
remove old files while services are stopped if necessary. Worker logs omit third-party
exception payloads, HTML, cookies, tokens, event titles and guest details.
