# Apple Calendar

For the same Mac, start `couchsync serve` or the separate managed publisher, then in
Calendar choose File → New Calendar Subscription and paste
http://127.0.0.1:8765/couchsurfing.ics. Choose an auto-refresh interval and calendar name.
Use subscription, not file import, to receive updates without duplicates.

For iPhone/iPad or other devices, provision the remote HTTPS publisher first. Subscribe
to the remote URL and choose an iCloud location where your OS/account supports it. A
localhost subscription cannot be fetched by another device or iCloud's servers. Check
that the subscribed calendar is enabled in the device calendar list; if iCloud does not
propagate that subscription, add the remote subscription directly on the device.

Couchsync publishes hourly while awake; Apple controls fetching. To replace a URL after
rotation, remove the old subscribed calendar and add the new one. Duplicate imports or
simultaneous old/new subscriptions can cause duplicate entries. Try Calendar refresh,
verify the completed snapshot exists and the publisher is running. Read-only edits do
not update Couchsurfing. Manual Apple Calendar/iCloud/device testing remains pending.

Apple guidance: https://support.apple.com/guide/calendar/subscribe-to-calendars-icl1022/mac
