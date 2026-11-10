# Private HTTPS static publication using WebDAV

This optional publisher uploads snapshots without exposing the user's computer. Use an
HTTPS server you control with WebDAV MKCOL/PUT/MOVE/DELETE support and a valid TLS
certificate. Give a separate publishing account write access only to the calendar tree.
The read endpoint permits GET/HEAD on unguessable token paths; disable directory listing,
disable access logging there, disallow caching in public intermediaries, and never expose
this tree through a public repository, GitHub Pages or public bucket.

One practical deployment is nginx built with the standard DAV module. Provision an HTTPS
virtual host (certificate/hostname/firewall depend on your infrastructure). Within it:

```nginx
location /private/ {
    root /srv/couchsync;
    autoindex off;
    access_log off;
    dav_methods PUT DELETE MKCOL COPY MOVE;
    dav_access user:rw;
    create_full_put_path on;
    client_max_body_size 10m;
    add_header Cache-Control "private, no-store" always;
    types { text/calendar ics; }
    limit_except GET HEAD {
        auth_basic "Calendar publisher";
        auth_basic_user_file /etc/nginx/couchsync.htpasswd;
    }
}
```

Create /srv/couchsync/private owned by the nginx worker and mode 0700. Create the password
file with htpasswd; only the publishing account should know its password. Protect backups
and temporary uploads with the same server filesystem permissions. Ensure DAV MOVE stays
within this tree; restrict all other server locations. This is an infrastructure example,
not an automatically deployed server. Confirm nginx DAV availability and configuration
with your administrator. Use a dedicated host to reduce exposure from unrelated sites.

Set `[remote] base_url = "https://your-host.example/private"` and `atomic_move = true` in
TOML. Run `couchsync calendar credentials` to collect the publishing username/password into
the OS vault, then `calendar publish`, then `calendar url`. Each enabled feed has an
independent 32-byte random token. All feeds use the same publishing account but independent
privacy configuration and tokens. The publisher MKCOLs a token directory, uploads a random
temporary name, then MOVEs over the feed. Failed uploads/MOVEs retain the old remote file.
TLS certificate checks stay enabled and redirects are rejected, preventing credentials
from following arbitrary endpoints. Leave atomic_move enabled for last-known-good safety.

Use `calendar rotate-token --feed all` to publish to a new random path, DELETE the old feed,
and update the vault. The old token is considered revoked only after DELETE succeeds.
If revocation fails, no success is claimed; investigate server permissions. Use `calendar
revoke` to delete the current remote feed and block automatic republishing until rotation.
DELETE cannot erase copies a calendar provider already cached. To revoke all leaked copies,
change privacy/details too. Backups, provider caches and historical URLs need their own
retention policy. URLs must be treated as credentials and should never be pasted in issues.

Validation: request flow, atomic publication failure behavior and revocation are tested
with an HTTP mock transport. Actual TLS/WebDAV infrastructure and calendar-provider GET
must be checked after deploying a server. No remote server was provisioned during this build.
