from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from platformdirs import PlatformDirs

from .util import https_url, private_dir

FEEDS = {"all", "organized", "events", "hosting", "stays", "confirmed"}
MODES = {"full", "limited", "generic", "busy", "private"}


@dataclass
class Config:
    data: Path
    config: Path
    logs: Path
    interval: int = 3600
    retention_days: int = 90
    max_cancellations: float = 0.5
    selector_file: str = "selectors.toml"
    name: str = "Couchsurfing"
    port: int = 8765
    feeds: dict = field(default_factory=lambda: {"all": {}})
    event_privacy: str = "limited"
    hosting_privacy: str = "limited"
    prefixes: dict = field(default_factory=dict)
    busy: dict = field(
        default_factory=lambda: {
            "organizing": True,
            "going": True,
            "interested": False,
            "invited": False,
            "pending": False,
            "confirmed": True,
        }
    )
    remote: dict = field(default_factory=dict)
    categories: list[str] = field(
        default_factory=lambda: ["organized", "going", "interested", "invited", "hosting"]
    )

    @classmethod
    def load(cls, path: Path | None = None) -> Config:
        dirs = PlatformDirs("couchsync", appauthor=False)
        path = path or Path(dirs.user_config_dir) / "config.toml"
        raw = tomllib.loads(path.read_text()) if path.exists() else {}
        cfg = cls(Path(dirs.user_data_dir), path, Path(dirs.user_log_dir))
        # Path overrides are useful for portable installs and isolated tests.
        for key in ("data", "logs"):
            if key in raw:
                setattr(cfg, key, Path(raw.pop(key)).expanduser().resolve())
        allowed = set(cls.__dataclass_fields__) - {"data", "config", "logs"}
        if set(raw) - allowed:
            raise ValueError("Unknown configuration option")
        for key, value in raw.items():
            if key in {"busy", "prefixes"}:
                getattr(cfg, key).update(value)
            else:
                setattr(cfg, key, value)
        cfg.validate()
        return cfg

    def validate(self) -> None:
        if not isinstance(self.selector_file, str) or not self.selector_file.endswith(".toml"):
            raise ValueError("selector_file must name a TOML selector profile")
        if not 3600 <= self.interval <= 604800:
            raise ValueError("interval must be 3600..604800 seconds")
        if not 1 <= self.port <= 65535 or self.retention_days < 1:
            raise ValueError("Invalid port or retention")
        if not 0 < self.max_cancellations <= 1:
            raise ValueError("max_cancellations must be in (0,1]")
        if not self.feeds or set(self.feeds) - FEEDS:
            raise ValueError("Unknown feed name")
        if set(self.categories) - {"organized", "going", "interested", "invited", "hosting"}:
            raise ValueError("Unknown source category")
        if self.event_privacy not in MODES or self.hosting_privacy not in MODES:
            raise ValueError("Unknown privacy mode")
        for settings in self.feeds.values():
            if set(settings) - {"event_privacy", "hosting_privacy"}:
                raise ValueError("Unknown per-feed option")
            if any(v not in MODES for v in settings.values()):
                raise ValueError("Unknown per-feed privacy mode")
        if self.remote:
            if set(self.remote) - {"base_url", "atomic_move"}:
                raise ValueError("Unknown remote option")
            https_url(self.remote["base_url"])
            from urllib.parse import urlsplit

            if urlsplit(self.remote["base_url"]).query:
                raise ValueError("Remote base URL must not contain query tokens")

    @property
    def selectors(self) -> Path:
        return self.config.parent / self.selector_file

    def initialize(self) -> None:
        for path in (self.data, self.logs, self.config.parent):
            private_dir(path)
