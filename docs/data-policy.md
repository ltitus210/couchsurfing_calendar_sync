# Calendar data and privacy


Events use a single immutable source identity across list memberships; organizing has
precedence over Going, Interested, Invited for the title while relationships preserve
attendance. UUID calendar UIDs survive changes; changes increment SEQUENCE. Explicit
inactive statuses produce CANCELLED tombstones. Missing records are always retained.
Even a complete list does not prove cancellation. A configurable mass-cancellation
threshold blocks suspicious batches (at least three existing active records).

Event states are Going, Interested, Organizing and Invited. Incoming Hosting Requests
and outgoing Stays (surfing) use Pending and Confirmed. Calendar titles and categories
identify the item type; stay entries also carry `X-COUCHSYNC-DIRECTION` outside Busy/Private mode.
Both directions are enabled by the `hosting` source category. Incoming record keys and UIDs
stay unchanged; outgoing stays have distinct keys and stable UIDs.

Pending requests/stays are transparent/free; confirmed requests/stays are opaque/busy. Arrival/departure
are all-day dates with exclusive checkout. Explicit same-day stays occupy one day.
Missing dates remain in database diagnostics and are omitted from calendars. Timed events
require explicit UTC offsets or unambiguous IANA-zone times; no machine-local assumption.
Old events leave feeds after the retention period; database/history retention is separate
and currently persists until the user removes local data.

Default hosting/stay privacy is limited: generic guest/host titles, status, dates and
source page URL; no messages or addresses. Default event privacy includes title/status/dates,
venue/postal address, About text and source page URL. Full hosting/stay mode may
additionally expose names, descriptions and addresses.
The ICS `URL` property links to the event or specific request/stay details; private pages
still require Couchsurfing authentication. Source URLs are identifying metadata.
Generic, Busy and Private modes omit URLs; Busy/Private also strip category/status/direction
metadata. Random UIDs remain so clients can update entries. Privacy filters apply to every
export/preview/feed.

Optional feeds: `events` contains events, `hosting` contains incoming Hosting Requests,
`stays` contains outgoing Stays, and `confirmed` contains confirmed stays in either direction.
The default `all` feed combines everything. Enable additional feeds in configuration, for
example `[feeds.stays]`; it uses the same `hosting_privacy` setting. The combined feed URL
remains unchanged.

Event locations combine the venue name and any postal address supplied in the event's
structured data. About text becomes the ICS `DESCRIPTION`, with HTML converted to readable
plain text; locations use `LOCATION`. No address is inferred or geocoded. Missing source
fields remain empty. Generic/Busy/Private event modes hide locations and descriptions.

Each successful scrape re-reads event details. Address/About changes update the existing
UID, increment `SEQUENCE` and refresh modification timestamps. Unchanged details do not
increment the sequence; explicit removal of details clears those fields. Failed scrapes
preserve the previous good snapshot. The hourly worker and calendar client's own refresh
schedule determine when changes appear; events not observed in a run remain retained.
