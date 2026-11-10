# Google Calendar

Google fetches the URL from Google's servers. A 127.0.0.1 URL or private LAN hostname will
not work. Provision externally reachable HTTPS static feeds using remote-publishing.md.
The secret URL must allow GET without an interactive login, cookie or custom header.

On Google Calendar **on the web**, use the + beside Other calendars → From URL, paste
`couchsync calendar url` output, and Add calendar. Enable the calendar in compatible Google
Calendar clients. The URL is a bearer credential shared with Google: anyone obtaining it
may read the selected feed. This is URL access, not public directory listing or publication.

Google controls subscription refresh frequency. Couchsync cannot force Google to refresh
every hour; delays are possible. Verify the HTTPS URL returns text/calendar with a valid
certificate, an updated ETag and no redirect to login. Removing/re-adding is a subscription
replacement, not a refresh guarantee. To replace after token rotation, remove the old
calendar in its settings and add the new URL. Remove duplicate imported files/subscriptions.

Subscriptions are read-only. Google client round-trip testing remains pending.
Google guidance: https://support.google.com/calendar/answer/37100
