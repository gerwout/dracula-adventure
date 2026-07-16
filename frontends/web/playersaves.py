"""Server-side named-save store: (player name + PIN) -> multiple named slots.

One JSON file per identity, named by an HMAC of the identity (raw input never
becomes a path). Up to MAX_SLOTS slots per identity. reap() enforces the TTL at
the identity-file level (renewed on any save). See spec §1, §2, §9.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import time
import unicodedata
from pathlib import Path

from . import savevalidate as _v

_SAFE = re.compile(r"[^A-Za-z0-9_-]")
MAX_SLOTS = 10


def load_or_create_pepper(state_dir) -> bytes:
    """Server secret for identity-key derivation: env override, else a persisted
    random file under the state dir (generated once, mode 0600)."""
    env = os.environ.get("DRACULA_WEB_SAVE_PEPPER", "").strip()
    if env:
        return env.encode("utf-8")
    p = Path(state_dir) / "pepper"
    try:
        return p.read_bytes()
    except OSError:
        p.parent.mkdir(parents=True, exist_ok=True)
        secret = os.urandom(32)
        tmp = p.with_suffix(".tmp")
        tmp.write_bytes(secret)
        os.replace(tmp, p)
        try:
            os.chmod(p, 0o600)
        except OSError:
            pass
        return secret


class PlayerSaveStore:
    def __init__(self, directory, pepper: bytes, max_slots: int = MAX_SLOTS):
        self.dir = Path(directory) / "players"
        self.dir.mkdir(parents=True, exist_ok=True)
        self._pepper = pepper
        self._max_slots = max_slots

    def _key(self, name: str, pin: str) -> str:
        norm = unicodedata.normalize("NFKC", name).strip().casefold()
        msg = (norm + "\x00" + pin).encode("utf-8")
        return hmac.new(self._pepper, msg, hashlib.sha256).hexdigest()

    def _normalize_slot_key(self, slot: str) -> str:
        """Normalize and case-fold slot for matching (internal use only)."""
        return _v.normalize_slot(slot).casefold()

    def _path(self, key: str) -> Path | None:
        return None if _SAFE.search(key) else self.dir / (key + ".json")

    def _read(self, key: str) -> dict | None:
        p = self._path(key)
        if p is None or not p.exists():
            return None
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        return data if isinstance(data, dict) else None

    def _write(self, key: str, rec: dict) -> None:
        p = self._path(key)
        if p is None:
            return
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(rec), encoding="utf-8")
        os.replace(tmp, p)

    def list_slots(self, name: str, pin: str):
        rec = self._read(self._key(name, pin))
        if not rec or not isinstance(rec.get("slots"), dict):
            return None
        items = sorted(rec["slots"].items(),
                       key=lambda kv: kv[1].get("ts", 0), reverse=True)
        return [(v.get("orig", s), v.get("hint", "")) for s, v in items]

    def load(self, name: str, pin: str, slot: str):
        rec = self._read(self._key(name, pin))
        if not rec:
            return None
        slot_rec = (rec.get("slots") or {}).get(self._normalize_slot_key(slot))
        if not isinstance(slot_rec, dict):
            return None
        state = slot_rec.get("state")
        return state if isinstance(state, dict) else None

    def has_slot(self, name: str, pin: str, slot: str) -> bool:
        rec = self._read(self._key(name, pin))
        return bool(rec) and self._normalize_slot_key(slot) in (rec.get("slots") or {})

    def save(self, name, pin, slot, state, lang, hint="", now=None) -> str:
        now = time.time() if now is None else now
        key = self._key(name, pin)
        rec = self._read(key) or {"slots": {}, "ts": now}
        slots = rec.setdefault("slots", {})
        original_slot = slot
        slot_key = self._normalize_slot_key(slot)
        if slot_key not in slots and len(slots) >= self._max_slots:
            return "full"
        slots[slot_key] = {"state": state, "lang": lang, "ts": now, "hint": hint, "orig": original_slot}
        rec["ts"] = now
        self._write(key, rec)
        return "ok"

    def delete(self, name, pin, slot) -> None:
        key = self._key(name, pin)
        rec = self._read(key)
        if not rec:
            return
        (rec.get("slots") or {}).pop(self._normalize_slot_key(slot), None)
        if rec.get("slots"):
            self._write(key, rec)
        else:
            p = self._path(key)
            if p:
                try:
                    p.unlink()
                except OSError:
                    pass

    def reap(self, ttl: float, now: float) -> int:
        deleted = 0
        for p in self.dir.glob("*.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                ts = data.get("ts", 0) if isinstance(data, dict) else 0
            except (json.JSONDecodeError, OSError):
                ts = 0
            ts = ts if isinstance(ts, (int, float)) else 0
            if now - ts > ttl:
                try:
                    p.unlink()
                    deleted += 1
                except OSError:
                    pass
        return deleted
