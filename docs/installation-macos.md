# macOS installation and scheduling

Follow README installation with Python 3.13+ on macOS 15+, Intel or Apple Silicon.
Use a stable venv path. Service command arguments embed the current interpreter and
absolute config path, so reinstall services after moving either. Keychain must be
available to the logged-in account; refuse plaintext/fallback credential backends.

`service install` writes two per-user LaunchAgents under ~/Library/LaunchAgents:
org.couchsync.sync (one-shot) and org.couchsync.serve (KeepAlive loopback server).
`service start` bootstraps both; `stop` boots them out; `status` queries launchctl;
`uninstall` boots out and removes the generated files. No root privileges are needed.
These commands are implemented but registration was not executed during this build.

The local `man launchd.plist` was checked during implementation. StartInterval can miss
firings during sleep or while a job is running; it does not guarantee wake catch-up.
StartCalendarInterval coalesces missed calendar firings on wake. The worker combines
StartInterval=3600, a top-of-hour calendar trigger, and RunAtLoad. A persistent last-attempt
guard limits actual scraping to the configured interval even when triggers overlap.
A filesystem lock prevents concurrent workers. Longer custom intervals are enforced by
the due guard. No sleep prevention or promise of exact wake-time execution is made.

Application logs rotate at 250 KB with three backups. LaunchAgent stdout/stderr files
hold bounded CLI status/error summaries; launchd does not rotate them automatically.
Periodically remove them while services are stopped if needed. No exception payloads,
HTML, cookies, tokens, titles or guest details are logged by the worker.

Manage only one component with `service install/start/stop/status/uninstall --task serve`
or `--task sync`. The default `--task all` preserves earlier behavior. Fixed-count
bootstrap profiles cannot install the hourly worker; see hourly-events.md for migration.
