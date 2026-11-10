# Dependency maintenance

requirements.lock pins runtime dependency versions and hashes across supported platforms.
It is generated with uv pip compile --universal --python-version 3.13 --generate-hashes.
Use Python 3.13+; pip chooses compatible platform artifacts. Build/dev tools are separately
listed in pyproject and CI. The lock records runtime versions, not a promise that every
third-party wheel exists on every future Python version.

To update deliberately:

```sh
python -m pip install uv
uv pip compile pyproject.toml --universal --python-version 3.13 --generate-hashes -o requirements.lock
python -m pip install --require-hashes -r requirements.lock
python -m pip install -e '.[dev]'
python -m playwright install chromium
pytest -q
ruff check .
pip-audit -r requirements.lock
```

Review changelogs, hashes and upstream advisories. Test on macOS Intel/Apple Silicon and
Windows with supported Python versions. Regenerate browser binaries after Playwright
updates. Do not commit local runtime state. Schema upgrades must take a backup and execute
inside a transaction, with rollback tests; v0.1 only includes schema v1 initialization.
