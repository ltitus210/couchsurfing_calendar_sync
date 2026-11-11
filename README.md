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
```

1. **If setup opens Chrome:** log into Couchsurfing, then type **SAVE** in Terminal.
2. **If you skipped login:** run `couchsync login` and do the same.
3. Run:

   ```sh
   couchsync scraper inspect
   ```

4. **In Chrome:** open **Events → View Your Events → Going**, then an event's details.
   Show Interested and Organizing too. Leave Inspector paused while a maintainer checks the pages.
5. **When inspection is finished:** click **Resume ▶ in Playwright Inspector**. Chrome closes.

**Stop here until a maintainer supplies your account's configuration and selector files.**
Opening Inspector does not create them automatically. Do not copy the synthetic test selectors.

Then follow the [short command-by-command guide](docs/setup-macos.md#4-get-the-account-profile)
for syncing, subscribing and starting background services.

## Already installed?

- [First sync and preview](docs/setup-macos.md#5-sync-and-preview)
- [Serve the feed and subscribe in Calendar](docs/setup-macos.md#6-subscribe-in-apple-calendar)
- [Enable background services](docs/setup-macos.md#8-start-background-services)
- [Troubleshoot an error](docs/troubleshooting.md)

**Tested scope:** Going, Interested and Organizing on one account, local Apple Calendar,
and macOS service startup. Full-list coverage, invitations, incoming hosting, Windows
runtime and Google/remote publishing remain unverified. [Validation details](docs/validation.md).

## Reference

- [Windows installation](docs/installation-windows.md)
- [Chrome/Inspector and maintainer configuration](docs/selectors.md)
- [Event update limits and traffic counters](docs/hourly-events.md)
- [Apple Calendar](docs/apple-calendar.md) · [Google Calendar](docs/google-calendar.md)
- [Remote HTTPS publishing](docs/remote-publishing.md)
- [Calendar data and privacy](docs/data-policy.md) · [Security](docs/security.md)
- [Maintenance](docs/maintenance.md) · [Contributing](CONTRIBUTING.md)

The local feed serves saved snapshots; feed requests never scrape Couchsurfing.
Subscriptions are read-only. Google Calendar and other devices need a reachable HTTPS URL.
