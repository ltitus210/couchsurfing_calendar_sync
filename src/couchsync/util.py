from __future__ import annotations

import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit


def now() -> str:
    return datetime.now(UTC).isoformat()


def private_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != "nt":
        path.chmod(0o700)
    return path


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".couchsync-")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def clean(value: str) -> str:
    # Keep newlines for the calendar library, strip terminal control characters.
    return re.sub(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]", "", str(value))[:20000]


def https_url(value: str, couchsurfing: bool = False) -> str:
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.fragment
    ):
        raise ValueError("An HTTPS URL without credentials or fragments is required")
    if couchsurfing and parsed.hostname not in {"www.couchsurfing.com", "couchsurfing.com"}:
        raise ValueError("Only Couchsurfing website URLs are allowed")
    return value
