from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from pathlib import Path

from .models import INACTIVE, Record, deduplicate
from .util import now, private_dir


class Database:
    def __init__(self, path: Path):
        private_dir(path.parent)
        self.path = path
        self.db = sqlite3.connect(path)
        if path.exists():
            path.chmod(0o600)
        self.db.row_factory = sqlite3.Row
        version = self.db.execute("PRAGMA user_version").fetchone()[0]
        if version > 1:
            raise RuntimeError("Database is newer than this application")
        if version == 0:
            self.db.executescript("""
            BEGIN IMMEDIATE;
            CREATE TABLE records (
              key TEXT PRIMARY KEY, uid TEXT NOT NULL, payload TEXT NOT NULL,
              hash TEXT NOT NULL, sequence INTEGER NOT NULL,
              first_seen TEXT NOT NULL, last_seen TEXT NOT NULL,
              verified TEXT NOT NULL, modified TEXT NOT NULL,
              canceled INTEGER NOT NULL, completeness TEXT NOT NULL);
            CREATE TABLE history (key TEXT, at TEXT, payload TEXT, sequence INTEGER);
            CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
            PRAGMA user_version=1;
            COMMIT;
            """)
            self.db.commit()

    def close(self) -> None:
        self.db.close()

    @contextmanager
    def transaction(self):
        try:
            self.db.execute("BEGIN IMMEDIATE")
            yield
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise

    def meta(self, key: str, value: str | None = None) -> str | None:
        if value is not None:
            self.db.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", (key, value))
            return value
        row = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row[0] if row else None

    def apply(self, records: list[Record], complete: bool, threshold: float = 0.5) -> None:
        if not complete:
            raise ValueError("Incomplete scrape; database and snapshots preserved")
        records = deduplicate(records)
        stamp = now()
        active = self.db.execute("SELECT count(*) FROM records WHERE canceled=0").fetchone()[0]
        cancellations = sum(
            r.status in INACTIVE
            and self.db.execute(
                "SELECT 1 FROM records WHERE key=? AND canceled=0", (r.key,)
            ).fetchone()
            is not None
            for r in records
        )
        if active >= 3 and cancellations / active > threshold:
            raise ValueError("Suspicious mass cancellation; inspect before changing threshold")
        for record in records:
            previous = self.db.execute(
                "SELECT * FROM records WHERE key=?", (record.key,)
            ).fetchone()
            digest = record.digest()
            changed = previous is None or previous["hash"] != digest
            seq = previous["sequence"] + int(changed) if previous else 0
            uid = previous["uid"] if previous else f"{uuid.uuid4()}@couchsync.local"
            modified = stamp if changed else previous["modified"]
            self.db.execute(
                "INSERT OR REPLACE INTO records VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    record.key,
                    uid,
                    record.payload(),
                    digest,
                    seq,
                    previous["first_seen"] if previous else stamp,
                    stamp,
                    stamp,
                    modified,
                    int(record.status in INACTIVE),
                    "complete",
                ),
            )
            if changed:
                self.db.execute(
                    "INSERT INTO history VALUES (?,?,?,?)",
                    (record.key, stamp, record.payload(), seq),
                )
        # Missing records are retained even after complete scans: disappearance is not cancellation.
        self.meta("last_success", stamp)

    def rows(self) -> list[dict]:
        return [dict(row) for row in self.db.execute("SELECT * FROM records ORDER BY key")]

    def backup(self, target: Path) -> None:
        if target.exists():
            raise ValueError("Backup destination already exists")
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        target.touch(mode=0o600, exist_ok=False)
        with sqlite3.connect(target) as output:
            self.db.backup(output)
