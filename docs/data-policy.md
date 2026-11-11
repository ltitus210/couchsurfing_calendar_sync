# Calendar data and privacy


Events use a single immutable source identity across list memberships; organizing has
precedence over Going, Interested, Invited for the title while relationships preserve
attendance. UUID calendar UIDs survive changes; changes increment SEQUENCE. Explicit
inactive statuses produce CANCELLED tombstones. Missing records are always retained.
Even a complete list does not prove cancellation. A configurable mass-cancellation
threshold blocks suspicious batches (at least three existing active records).

Pending hosting is transparent/free; confirmed hosting is opaque/busy. Arrival/departure
are all-day dates with exclusive checkout. Explicit same-day stays occupy one day.
Missing dates remain in database diagnostics and are omitted from calendars. Timed events
require explicit UTC offsets or unambiguous IANA-zone times; no machine-local assumption.
Old events leave feeds after the retention period; database/history retention is separate
and currently persists until the user removes local data.

Default hosting privacy is limited (generic guest title, no messages/addresses/source URLs).
Default event privacy is limited (title/status/dates). Full mode may expose names,
addresses and source URLs. Busy/private mode strips identifying metadata; opaque random
UIDs remain so clients can update entries. Privacy filters apply to every export/preview/feed.

