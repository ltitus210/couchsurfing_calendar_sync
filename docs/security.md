# Security and privacy

Never put passwords, session cookies, feed tokens or publishing credentials into TOML,
source, shell arguments, environment variables or issue reports. Interactive website
login remains user-controlled; no MFA/CAPTCHA bypass, stealth, proxy rotation or account
actions are implemented. Automated scraping may need maintenance or be restricted by
Couchsurfing. Use only normal access permitted for your account.

Persisted Playwright cookies/localStorage/IndexedDB are encrypted with Fernet authenticated
encryption. The key stays in the native macOS Keychain or Windows Credential Manager via
keyring. Unsupported/plaintext backends are rejected. Decrypted storage state is passed as
an in-memory dictionary, never exported as a plaintext storage_state file. Chromium uses a
temporary isolated profile and cleans it on exit; OS temporary files, process memory, swap
and crash recovery remain realistic exposure paths. This is not protection against a
compromised user account, same-user malware, an unlocked credential store or physical access
to an unlocked computer. Full-disk encryption and a strong login password are recommended.
Social login providers may reject automated browsers; authenticate normally or stop.

Config/data/log directories use 0700 and application-written files use 0600 on POSIX.
Windows inherits the user's application directory ACL; Python chmod does not provide a
complete Windows ACL policy. Verify account ACLs on shared machines. SQLite stores private
source information in plaintext locally. Full-disk encryption and encrypted backups are
needed for stolen-disk/backup protection. Backup excludes credential store/session keys;
logging in again is required on another installation. Revoking a local session does not
revoke the website's server-side session; use the website's account controls too.

Feed privacy applies before serialization. Default event mode includes title/status/dates, venue/postal address, About text and the source page URL;
limited hosting/stays include source page URLs but omit guest/host names and personal fields.
Generic event mode omits URLs, descriptions and locations. Request/stay URLs identify private pages and require website login. Full mode exposes selected source
details. Private/busy mode omits source URLs, descriptions, locations, source identifiers,
status metadata and categories; stable random UUIDs are still present for updates. No mode
scrapes private message bodies by design, but user-defined selectors must be reviewed to
avoid accidentally selecting messages. Availability and dates are inherently disclosed.
CLASS:PRIVATE is a hint, not access control.

Loopback HTTP serves only an explicit allowlist of enabled ICS snapshots; it has no file
browser, arbitrary paths or scrape endpoint. Other local processes can access loopback.
Remote feeds require TLS and unguessable independent bearer tokens. A hosting provider,
Google/Apple or anyone with the URL may see data. Remote hosts and backups must protect
calendar files and suppress URL logging. Rotation revokes old HTTP access, not cached copies.
Do not use public GitHub Pages, public repositories or unprotected/listable buckets.

Diagnostics contain booleans and aggregate counts only. Worker logs record exception types,
counts and duration, not third-party exception strings. CLI suppresses unknown exception
payloads. Terminal control characters from scraped text are stripped. The icalendar library
performs text escaping/folding. Browser TLS validation and Chromium sandbox remain enabled.
Website HTML runs only in the browser; it is never evaluated as Python or shell commands.

Gitignore excludes private runtime artifacts. CI runs Gitleaks and pip-audit. A clean scan
cannot prove absence of all secrets; inspect git diff before publishing and rotate any
secret that entered history. Report vulnerabilities privately to the repository owner;
do not attach private HTML, calendars, database files or feed URLs to public issues.
