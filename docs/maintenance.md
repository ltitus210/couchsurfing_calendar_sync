# Maintenance


`backup PATH` uses SQLite backup under the synchronization lock. Backups contain private
plaintext records; encrypt them using OS storage encryption. `restore PATH` retains a
pre-restore backup. Session encryption keys are never included. `logout` removes local
session state; revoke Couchsurfing sessions on the website if compromise is suspected.

Before upgrading: stop services, back up, update dependencies/package, run tests/doctor,
then reinstall services if the interpreter moved. Schema v1 initializes transactionally;
newer unsupported schemas are rejected. No destructive migrations ship in v0.1.

Uninstall: `service stop`, `service uninstall`, `logout`, `calendar revoke` for each remote
feed, remove subscriptions, then uninstall the package/venv. Feed tokens and publishing
credentials can be removed from OS credential storage under `couchsync:<installation-id>`.
Remove application config/data/log directories only after preserving desired backups.

