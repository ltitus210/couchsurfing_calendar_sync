# Apple Calendar: verify the server, then subscribe

For the complete sequence, see [guided setup, stage 4](setup-macos.md#4-apple-calendar).
The local On My Mac subscription has been exercised successfully in one user setup;
iCloud, iPhone/iPad and remote HTTPS behavior still require their own validation.

## 1. Keep a publisher running

In the project's activated environment, start the saved-feed server with the
same configuration used for sync (add your usual `--config` if using a custom profile):

```sh
couchsync serve
```

It keeps this terminal busy. Leave it running. Current versions print a serving message;
older versions can be silent. Do not close that terminal or press Ctrl-C until a managed
publisher replaces it. A successful sync or preview does not automatically start a server.
If the managed publisher service is already active, skip this manual command to avoid a
second server competing for port 8765.

## 2. Test in a second terminal

```sh
curl --noproxy '*' -I http://127.0.0.1:8765/couchsurfing.ics
```

Proceed only after `200 OK` and `Content-Type: text/calendar; charset=utf-8`. HTTP/1.0 is
normal. GMT timestamps in HTTP headers can show a different date from your local timezone.
This checks the saved feed without requesting Couchsurfing data.

If connection is refused, check that `serve` is still running, using the same config/port.
If it exited, read the error in its terminal. If it reports no completed snapshot, return
to the first sync stage. Do not repeat live scraping to fix a stopped publisher.

## 3. Add the subscription

1. Open Calendar and choose **File → New Calendar Subscription**.
2. Enter `http://127.0.0.1:8765/couchsurfing.ics` and click Subscribe.
3. Choose the name/color and **On My Mac** for this loopback URL.
4. Select an Auto-refresh interval and finish the subscription.
5. Verify expected local start/end times and multi-day events.

[Apple's subscription instructions](https://support.apple.com/guide/calendar/subscribe-to-calendars-icl1022/mac).
If Calendar asks about the local HTTP connection, permission does not itself make the
server available. If “The request … failed” appears, repeat the HTTP check in stage 2
before changing calendar settings. Do not globally disable certificate/security checks.

A subscription receives provider updates and is read-only. Repeated file imports or
keeping old/new subscriptions at the same time can cause duplicates. Calendar uses its
selected timezone; the CLI preview uses UTC. A next-day UTC timestamp can represent the
correct previous-evening local event.

## 4. Replace the manual terminal with a service

After the validated setup reaches [background services](setup-macos.md#5-background-services),
stop manual `serve` with Ctrl-C, start the managed publisher, then confirm HTTP 200 again.
Keep the existing subscription URL; do not add another calendar. Once the publisher is
loaded and the feed works, terminals can be closed.

Apple controls client refresh timing separately from Couchsync's worker schedule.
Use Calendar's refresh option if checking a newly published snapshot, and verify server
availability/current sync status before assuming a client display issue.

## Other devices and iCloud

Another device, iCloud's servers and Google Calendar cannot retrieve this Mac's
`127.0.0.1` endpoint. Provision [remote HTTPS publication](remote-publishing.md) before
using a subscription across devices. Choose an iCloud location where supported for that
remote URL, and verify that each device displays/enables the subscription. This has not
been validated by the local On My Mac test.

After remote token rotation, remove the old subscription and add the new URL. Removing
and replacing a subscription is different from repeatedly importing an ICS file.
