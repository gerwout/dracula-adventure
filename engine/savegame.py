"""Save / load of the full game state — BEWAAR SPEL & LAAD SPEL.

Faithful to what the original serializes (docs/savegame.md): the current room, the
object-location array, and the DGROUP state flags. The engine's runtime state is
`eng.room`, `eng.obj_loc` (obj id -> location) and `eng.state` (the DGROUP flag dict);
we round-trip exactly those, plus the consecutive-fail counter.

This is the Python-native JSON form (Python <-> Python). A byte-compatible DRACULA.SAV
reader/writer (so saves interchange with the real DOSBox game) is a documented follow-up
that needs an oracle-generated reference file — see docs/savegame.md.

`serialize`/`restore` are pure (no I/O), so they double as the "scenario" mechanism for
replay testing: any partial state dict can be `restore`d onto a fresh engine.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol


def serialize(eng) -> dict:
    """Snapshot the round-trippable runtime state."""
    return {
        "room": eng.room,
        "obj_loc": {str(k): v for k, v in eng.obj_loc.items()},
        "state": dict(eng.state),
        "fail_counter": eng.fail_counter,
    }


def restore(eng, data: dict) -> None:
    """Apply a snapshot (or a partial scenario dict) onto `eng`."""
    if "room" in data:
        eng.room = data["room"]
    if "obj_loc" in data:
        eng.obj_loc = {int(k): v for k, v in data["obj_loc"].items()}
    if "state" in data:
        eng.state = dict(data["state"])
    if "fail_counter" in data:
        eng.fail_counter = data["fail_counter"]


def save(eng, path) -> None:
    Path(path).write_text(json.dumps(serialize(eng)), encoding="utf-8")


def load(eng, path) -> bool:
    """Restore from `path`; return False (and leave `eng` untouched) if it is missing
    or unreadable — mirrors the original's load-failure branch."""
    p = Path(path)
    if not p.exists():
        return False
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    restore(eng, data)
    return True


class SaveStore(Protocol):
    """Where a saved game is written to / read from. Desktop uses a file; the web
    frontend routes this to the browser's localStorage."""
    def save(self, data: dict) -> None: ...
    def load(self) -> dict | None: ...


class FileSaveStore:
    """The default store: one JSON save file (the CLI/GUI behaviour)."""
    def __init__(self, path):
        self.path = Path(path)

    def save(self, data: dict) -> None:
        self.path.write_text(json.dumps(data), encoding="utf-8")

    def load(self) -> dict | None:
        if not self.path.exists():
            return None
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
