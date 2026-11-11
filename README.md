# Couchsync

Private Couchsurfing calendar feeds for Apple Calendar and Google Calendar.
Python 3.13+; macOS first, with Windows support under development.

## Quick start — macOS

Open Terminal in the project folder. Run each command in order; stop if one fails.

```sh
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install --require-hashes -r requirements.lock
python -m pip install setuptools wheel
python -m pip install --no-deps --no-build-isolation -e .
python -m playwright install chromium
couchsync setup
couchsync login
```

**In Chrome:** log into Couchsurfing. **In Terminal:** type `SAVE` and press Return.
Skip the separate login command if you already logged in during setup.
Built-in website defaults are included; no initial inspection or custom profile is required.

```sh
couchsync sync
couchsync preview
couchsync serve
```

**Look for:** `updated_observations`, expected titles/dates in preview, then a running server.
`complete: false` means full-list coverage is unverified; missing entries are retained.
`not_due` means wait until an hour after the last attempt.

**In Apple Calendar:** File → New Calendar Subscription →
`http://127.0.0.1:8765/couchsurfing.ics` → **On My Mac**.
Keep the server Terminal open until you [enable background services](docs/setup-macos.md#5-background-services).

## Already installed?

- [Sync and preview](docs/setup-macos.md#3-sync-and-preview)
- [Check the feed and subscribe](docs/setup-macos.md#4-apple-calendar)
- [Enable background services](docs/setup-macos.md#5-background-services)
- [Troubleshoot an error](docs/troubleshooting.md)

## What is synchronized?

| Calendar label | Couchsurfing item |
|---|---|
| Event: Going / Interested / Organizing / Invited | Events you attend, follow, organize or are invited to |
| Hosting Request: Pending / Confirmed | Incoming requests from guests staying with you |
| Stay: Pending / Confirmed | Outgoing requests you sent to hosts; you are surfing |

Event entries include the venue/postal address, About text and source page URL with
the default Limited or Full privacy settings. These details refresh on successful syncs
of the event; the same calendar entry is updated. Requests/stays also include source links.
Generic, Busy and Private settings hide links. Opening a private request/stay link requires
Couchsurfing login. Pending stays are free; confirmed stays are busy by default.

**Coverage:** events use the observed shared layout. Invited is included when that tab exists.
Hosting requests and outgoing stays use the guarded shared stays layout; unrecognized panels
produce `source_notes`. Incoming/confirmed layouts, invitations and English empty captions
still need live validation. Existing selector overrides take precedence.
[Validation details](docs/validation.md).

## Reference

- [Windows installation](docs/installation-windows.md)
- [Optional inspection and layout repairs](docs/selectors.md)
- [Hourly update limits and traffic counters](docs/hourly-events.md)
- [Apple Calendar](docs/apple-calendar.md) · [Google Calendar](docs/google-calendar.md)
- [Remote HTTPS publishing](docs/remote-publishing.md)
- [Calendar data and privacy](docs/data-policy.md) · [Security](docs/security.md)
- [Uninstall](docs/uninstall.md) · [Maintenance](docs/maintenance.md) · [Contributing](CONTRIBUTING.md)

The local feed serves saved snapshots; feed requests never scrape Couchsurfing.
Subscriptions are read-only. Google Calendar and other devices need a reachable HTTPS URL.
