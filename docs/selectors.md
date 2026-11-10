# Authenticated website validation

No production selectors or undocumented API endpoints are invented here. Public pages
and Couchsurfing's current host guide were inspected on November 10, 2026. The host guide
(updated November 4) describes Your Guests → chat → View Request, with confirmation from
both host and traveler. An accepted chat or host-only acceptance must not be interpreted
as a mutually confirmed stay.

Source: https://support.couchsurfing.org/hc/en-us/articles/50055202137115-How-Do-I-Receive-and-Manage-Stay-Requests-A-Guide-for-Hosts

1. Run `couchsync login`. A visible isolated Chromium opens. Complete login/social login/
   MFA manually, then type SAVE at the terminal. No password is collected by Couchsync.
2. Run `couchsync scraper inspect`. Playwright Inspector opens on the saved session.
   Navigate normally. Do not use automation to accept chats/stays or send messages.
3. Inspect each enabled list: organized/co-organized, Going, Interested, Invited and all
   incoming hosting states. Establish an authenticated-only marker and incoming-only scope.
4. Place `selectors.toml` next to the non-secret configuration. Use the structural format
   in `tests/fixtures/selectors.synthetic.toml` as a contract reference, **not as live
   selectors**. Create one `[[sources]]` per enabled category. Set `validated_on` to the
   inspection date, actual observed `url`, `container`, `item`, explicit `empty`, explicit
   `end` marker, and `incoming_marker` for hosting. `auth_marker` is global.
5. `fields` map Record field names to a relative CSS/Playwright selector and optional
   `attribute`. Use `pattern` only for a full-match extraction with group 1 (e.g. immutable
   source ID from a link). Never derive an ID from a title/date. IDs must identify the
   same source across lists. `format` converts observed date strings via strptime into
   ISO dates/times. Without format, dates must already be ISO. Timed values need an
   offset or a `timezone` field. Missing date elements can use `optional = true`.
6. `statuses` maps exact **observed account-specific state text** to internal organizing,
   going, interested, invited, pending, confirmed, declined, withdrawn, canceled, expired,
   completed. Do not map a general event's public status to the user's RSVP. Preserve
   raw status. Inspect all intermediate hosting confirmation states; map unfinished
   confirmation to pending. Confirmed means the observed website's confirmed stay state.
7. For pagination set `next` (including load-more) or `scroll = true`, `max_pages` (default
   50), and a reliable explicit end marker. No-next alone is never completion. For detail
   pages set `detail_link` (relative link selector on each item) and `detail_container`;
   fields are then extracted from that container on the linked Couchsurfing page. Avoid
   selectors spanning private message bodies. Select only required event/stay fields.
8. `scraper check` performs one rate-limited, locked dry-run including rendering and
   reconciliation checks. It outputs only request counts, source counts and duration.
   An incomplete source aborts the entire batch. Wait an hour before the next live run.
9. Validate known empty lists, multi-page/infinite lists, all status transitions, event
   detail pages, missing dates and authentication expiration. Document findings locally.
   Only then enable services.

Selectors are user-maintained configuration; this release does not automate discovery or
prove correctness of a user-entered completeness marker. A maintainer must review observed
DOM before shipping a production adapter. The browser fixture tests detect parser
regressions, not changes to a site whose authenticated DOM we have not accessed.

Do not commit raw authenticated HTML or screenshots. Use fictional replacement fixtures.
The inspection tool intentionally captures no raw data. No artifacts are uploaded.
