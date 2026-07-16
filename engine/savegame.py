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
    """Apply a snapshot (or a partial scenario dict) onto `eng`.

    Defensive: tolerates a malformed/partial dict without raising — a non-dict input is a
    no-op, wrong-typed fields are ignored, and an unparseable obj_loc key is skipped. So a
    hostile client-supplied save (the LAAD SPEL path) can never crash the engine worker;
    ``is_valid_save`` is the stronger gate the load handler uses to reject junk outright."""
    if not isinstance(data, dict):
        return
    if isinstance(data.get("room"), int):
        eng.room = data["room"]
    obj_loc = data.get("obj_loc")
    if isinstance(obj_loc, dict):
        parsed: dict[int, object] = {}
        for k, v in obj_loc.items():
            try:
                parsed[int(k)] = v
            except (ValueError, TypeError):
                continue
        eng.obj_loc = parsed
    if isinstance(data.get("state"), dict):
        eng.state = dict(data["state"])
    if isinstance(data.get("fail_counter"), int):
        eng.fail_counter = data["fail_counter"]


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)   # bool is a subclass of int


def is_valid_save(data, world) -> bool:
    """Whether ``data`` is a plausible save for ``world`` — content, not just structure:
    a dict whose ``room`` is a real room id, whose ``obj_loc`` (if present) maps *real*
    object ids to int locations, and whose ``state`` (if present) has int values. This is
    checked so a crafted save can never reach ``restore``/``describe_room`` and crash the
    engine worker (a bogus object id -> KeyError in the room lister; a non-int flag ->
    TypeError in the describe-time room events). Rejects a hostile or corrupt
    client-supplied save BEFORE it is restored. (The web resume path restores
    server-written snapshots and does not need this.)"""
    if not isinstance(data, dict):
        return False
    room = data.get("room")
    if not _is_int(room) or room not in world.rooms:
        return False
    obj_loc = data.get("obj_loc", {})
    if not isinstance(obj_loc, dict):
        return False
    for k, v in obj_loc.items():
        try:
            oid = int(k)
        except (ValueError, TypeError):
            return False
        if oid not in world.objects or not _is_int(v):
            return False
    state = data.get("state", {})
    if not isinstance(state, dict):
        return False
    if not all(_is_int(v) for v in state.values()):
        return False
    return _is_int(data.get("fail_counter", 0))


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
    """Where a saved game is written to / read from. `save` returns True when the
    save was persisted, False when it was declined/cancelled (so the caller does not
    print a false confirmation)."""
    def save(self, data: dict) -> bool: ...
    def load(self) -> dict | None: ...


class FileSaveStore:
    """The default store: one JSON save file (the CLI/GUI behaviour)."""
    def __init__(self, path):
        self.path = Path(path)

    def save(self, data: dict) -> bool:
        self.path.write_text(json.dumps(data), encoding="utf-8")
        return True

    def load(self) -> dict | None:
        if not self.path.exists():
            return None
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
