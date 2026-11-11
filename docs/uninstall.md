# Uninstall Couchsync

Run from the project folder. These steps remove Couchsync without deleting your source
code or saved calendar data. Optional data removal is below.

**Custom configuration:** keep using the same `--config` argument as your running services
on every `couchsync` command. For example:

```sh
couchsync --config "$HOME/Library/Application Support/couchsync/events-first.toml" service stop
```

## 1. Remove background services

**macOS:**

```sh
source .venv/bin/activate
couchsync service stop
couchsync service uninstall
```

**Windows PowerShell:**

```powershell
.\.venv\Scripts\couchsync service stop
.\.venv\Scripts\couchsync service uninstall
```

Stop any manually running `serve`, sync or Inspector session too; press Ctrl-C in its
Terminal. If services were already stopped, skip `service stop`.

**Look for:** no Couchsync jobs in Windows Task Scheduler, or no
`org.couchsync.sync.plist` / `org.couchsync.serve.plist` in `~/Library/LaunchAgents` on macOS.
The macOS uninstall command can print `active` when unloading succeeded; this message
is not a post-uninstall status check. `service status` should then report inactive.

## 2. Remove subscriptions and remote feeds

- **Apple Calendar:** select the Couchsync subscription in the sidebar → Edit → Delete.
- **Google Calendar:** open the subscription's Settings → Remove calendar → Unsubscribe.
- **Local-only publication:** skip the command below.
- **Remote HTTPS publication:** revoke each published feed before removing credentials:

```sh
couchsync calendar revoke --feed all
```

On Windows, use `.\.venv\Scripts\couchsync calendar revoke --feed all`.
Repeat with the names of any other published feeds: `organized`, `events`, `hosting`,
`stays`, `confirmed`. Use the same custom configuration argument if applicable.
**Look for:** `Revoked`. If it fails, resolve remote deletion before removing credentials;
uninstalling locally does not delete the server's calendar files or cached copies.

## 3. Remove the local login

**macOS:**

```sh
couchsync logout
```

**Windows PowerShell:**

```powershell
.\.venv\Scripts\couchsync logout
```

**Look for:** `Local session removed`. This removes the saved session and its encryption
key; it does not sign you out of Couchsurfing in your everyday browser.

## 4. Optional: remove saved data

Keep these files if you plan to reinstall. For a complete removal:

- **macOS:** move `~/Library/Application Support/couchsync` and `~/Library/Logs/couchsync`
  to Trash. Check any custom `data` / `logs` paths in your configuration first.
- **Windows:** check the `couchsync` application folder under `%LOCALAPPDATA%`, including
  its configuration, database, snapshots and logs; also check custom `data` / `logs` paths.
- Remove only this installation's remaining `couchsync:<installation-id>` entries from
  **Keychain Access** (macOS) or **Credential Manager** (Windows), after remote revocation.
- Delete unwanted backups and remote files separately. Keep anything you want to recover;
  deleting the database loses saved event identities and history.

## 5. Remove the package

**macOS:**

```sh
python -m pip uninstall couchsync
```

**Windows PowerShell:**

```powershell
.\.venv\Scripts\python -m pip uninstall couchsync
```

Confirm pip's removal prompt. You may then delete the project's `.venv` folder if it is
used only for Couchsync. Keep the project/source folder if you want to reinstall later.
Leave shared Playwright browser downloads in place if other projects use them.
