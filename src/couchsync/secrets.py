from __future__ import annotations

import json
import secrets
import sys
from pathlib import Path

import keyring
from cryptography.fernet import Fernet

from .util import atomic_write


class Vault:
    """Reject third-party/plaintext keyring backends; never fall back to files."""

    def __init__(self, identity: str):
        backend = keyring.get_keyring()
        module = type(backend).__module__
        expected = (
            "keyring.backends.macOS" if sys.platform == "darwin" else "keyring.backends.Windows"
        )
        if not module.startswith(expected):
            raise RuntimeError(
                "Supported OS credential store unavailable; refusing insecure fallback"
            )
        self.service = "couchsync:" + identity

    def get(self, name: str) -> str | None:
        return keyring.get_password(self.service, name)

    def set(self, name: str, value: str) -> None:
        keyring.set_password(self.service, name, value)

    def delete(self, name: str) -> None:
        if self.get(name) is not None:
            keyring.delete_password(self.service, name)

    def token(self, feed: str) -> str:
        token = self.get("feed-" + feed)
        if token is None:
            token = secrets.token_urlsafe(32)
            self.set("feed-" + feed, token)
        return token


class Session:
    def __init__(self, path: Path, vault: Vault):
        self.path, self.vault = path, vault

    def save(self, state: dict) -> None:
        key = self.vault.get("session-key")
        if not key:
            key = Fernet.generate_key().decode()
            self.vault.set("session-key", key)
        atomic_write(self.path, Fernet(key.encode()).encrypt(json.dumps(state).encode()))

    def load(self) -> dict:
        key = self.vault.get("session-key")
        if not key or not self.path.exists():
            raise RuntimeError("No session. Run couchsync login")
        return json.loads(Fernet(key.encode()).decrypt(self.path.read_bytes()))

    def clear(self) -> None:
        self.path.unlink(missing_ok=True)
        self.vault.delete("session-key")
