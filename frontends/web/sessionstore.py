"""Disk-backed snapshot store for resumable web sessions.

One JSON file per opaque session token: {"state": <serialize(eng)>, "lang": <code>,
"ts": <epoch seconds>}. Writes are atomic (tmp + os.replace). `reap` enforces the TTL and
a hard file-count cap. Token filenames are sanitised so a hostile token can never escape
the directory. All operations tolerate missing/corrupt files (return None / skip)."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

_SAFE = re.compile(r"[^A-Za-z0-9_-]")


def _safe_name(token: str) -> str | None:
    # tokens are secrets.token_urlsafe -> [A-Za-z0-9_-]; reject anything else outright
    if not token or _SAFE.search(token):
        return None
    return token + ".json"


class SessionStore:
    def __init__(self, directory) -> None:
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, token: str) -> Path | None:
        name = _safe_name(token)
        return (self.dir / name) if name else None

    def save(self, token: str, state: dict, lang: str) -> None:
        p = self._path(token)
        if p is None:
            return
        import time
        rec = {"state": state, "lang": lang, "ts": time.time()}
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(rec), encoding="utf-8")
        os.replace(tmp, p)

    def load(self, token: str) -> dict | None:
        p = self._path(token)
        if p is None or not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def exists(self, token: str) -> bool:
        p = self._path(token)
        return bool(p and p.exists())

    def reap(self, ttl: float, max_files: int, now: float) -> int:
        files = []
        for p in self.dir.glob("*.json"):
            try:
                ts = json.loads(p.read_text(encoding="utf-8")).get("ts", 0)
            except (json.JSONDecodeError, OSError):
                ts = 0
            files.append((ts, p))
        deleted = 0
        keep = []
        for ts, p in files:
            if now - ts > ttl:
                try:
                    p.unlink(); deleted += 1
                except OSError:
                    pass
            else:
                keep.append((ts, p))
        if len(keep) > max_files:
            keep.sort()  # oldest ts first
            for ts, p in keep[: len(keep) - max_files]:
                try:
                    p.unlink(); deleted += 1
                except OSError:
                    pass
        return deleted
