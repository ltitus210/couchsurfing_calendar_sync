# Maintenance


`backup PATH` uses SQLite backup under the synchronization lock. Backups contain private
plaintext records; encrypt them using OS storage encryption. `restore PATH` retains a
pre-restore backup. Session encryption keys are never included. `logout` removes local
session state; revoke Couchsurfing sessions on the website if compromise is suspected.

Before upgrading: stop services, back up, update dependencies/package, run tests/doctor,
then reinstall services if the interpreter moved. Schema v1 initializes transactionally;
newer unsupported schemas are rejected. No destructive migrations ship in v0.1.

For removal, follow [the uninstall guide](uninstall.md): stop/remove services, revoke any
remote feeds, remove subscriptions and local login, then uninstall the package. Saved data
is kept unless you choose optional cleanup.
