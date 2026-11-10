# Contributing

Use Python 3.13+, install .[dev], Chromium, and run pytest and ruff. Preserve explicit
completeness checks and last-known-good semantics. Never contribute authenticated captures,
real guest information or feed tokens. Fixtures must be synthetic or fully sanitized.
Update docs/selectors.md and add regression fixtures when an authenticated adapter changes.
No production selector should be asserted verified without an actual account inspection.

Status transitions require stable UIDs, correct sequence increments, deduplication and
privacy tests. Review the generated ICS rather than raw string concatenation. CI performs
browser/HTTP fixture tests, package build, secret scanning and dependency vulnerability checks.
