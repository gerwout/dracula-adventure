"""Save / load — BEWAAR SPEL & LAAD SPEL (see docs/savegame.md).

The original serializes the object-location array + current room + the DGROUP state
flags to DRACULA.SAV. The old Engine._state() saved self.flags (the unused bool dict)
and dropped self.state (the real flags) — these tests pin the corrected round-trip.
"""
import json

import pytest

from engine import savegame
from engine.data.loader import load_file
from engine.data.model import CARRIED
from engine.game import Engine
from engine.io import ScriptedIO


def _eng():
    return Engine(load_file(), ScriptedIO([]))


def test_serialize_restore_round_trips_the_full_state():
    eng = _eng()
    eng.room = 24
    eng.obj_loc[6] = CARRIED               # ladder carried
    eng.obj_loc[15] = 99                   # a consumed object
    eng.state["dde"] = 257                 # Dracula defeated  (the flag the old save DROPPED)
    eng.state["e48"] = 1                   # sesam door opened
    eng.state["e96"] = 1
    eng.fail_counter = 2

    blob = savegame.serialize(eng)
    fresh = _eng()                         # a pristine engine (dde=255, e48=0, room 0)
    assert fresh.state["dde"] == 255 and fresh.room == 0
    savegame.restore(fresh, blob)

    assert fresh.room == 24
    assert fresh.obj_loc[6] == CARRIED
    assert fresh.obj_loc[15] == 99
    assert fresh.state["dde"] == 257       # <-- the bug fix: DGROUP flags survive
    assert fresh.state["e48"] == 1
    assert fresh.state["e96"] == 1
    assert fresh.fail_counter == 2


def test_save_and_load_via_file(tmp_path):
    path = tmp_path / "DRACULA.SAV.json"
    eng = _eng()
    eng.room = 30
    eng.state["e40"] = 1
    savegame.save(eng, path)
    assert path.exists()
    other = _eng()
    assert savegame.load(other, path) is True
    assert other.room == 30 and other.state["e40"] == 1


def test_load_missing_file_returns_false():
    eng = _eng()
    assert savegame.load(eng, "does-not-exist-12345.json") is False


def test_bewaar_then_laad_commands_restore_state(tmp_path, monkeypatch):
    # BEWAAR SPEL writes, LAAD SPEL reads back, with the faithful DRACULA.SAV messages.
    import engine.game as game
    monkeypatch.setattr(game, "SAVE_PATH", tmp_path / "DRACULA.SAV.json")
    w = load_file()

    eng = Engine(w, ScriptedIO([]))
    eng.room = 22
    eng.state["dde"] = 22                  # mid-fight state
    eng.io = ScriptedIO([]); eng.submit("bewaar spel")
    assert w.message_text(185) in eng.io.text            # "Ik zet nu alle gegevens in DRACULA.SAV..."

    later = Engine(w, ScriptedIO([]))      # a fresh game
    later.io = ScriptedIO([]); later.submit("laad spel")
    assert w.message_text(186) in later.io.text          # "Ik haal nu alle gegevens uit DRACULA.SAV..."
    assert later.room == 22
    assert later.state["dde"] == 22


def test_laad_without_a_save_gives_the_vtoc_error(tmp_path, monkeypatch):
    import engine.game as game
    monkeypatch.setattr(game, "SAVE_PATH", tmp_path / "nope.json")
    w = load_file()
    eng = Engine(w, ScriptedIO([]))
    eng.io = ScriptedIO([]); eng.submit("laad spel")
    assert w.message_text(188) in eng.io.text            # the "Vtoc error" easter egg


# -- hardening: a hostile/corrupt client-supplied save must never crash the worker ------

def test_restore_tolerates_malformed_data_without_raising():
    eng = _eng()
    savegame.restore(eng, "not a dict")                      # non-dict -> no-op
    savegame.restore(eng, {"room": "nope", "state": "x",     # wrong-typed fields ignored
                           "obj_loc": {"notanint": 5}})      # unparseable key skipped
    assert eng.room == 0                                      # non-int room left untouched
    assert isinstance(eng.obj_loc, dict) and "notanint" not in eng.obj_loc
    # a valid partial dict still applies
    savegame.restore(eng, {"room": 24, "obj_loc": {"6": 99}})
    assert eng.room == 24 and eng.obj_loc[6] == 99


def test_is_valid_save():
    w = load_file()
    assert savegame.is_valid_save({"room": 0}, w) is True
    assert savegame.is_valid_save({"room": 24, "obj_loc": {}, "state": {}}, w) is True
    assert savegame.is_valid_save(savegame.serialize(_eng()), w) is True   # a real save
    assert savegame.is_valid_save(None, w) is False
    assert savegame.is_valid_save("x", w) is False
    assert savegame.is_valid_save({"room": 99999}, w) is False        # room not in world
    assert savegame.is_valid_save({"room": "0"}, w) is False          # wrong type
    assert savegame.is_valid_save({"room": True}, w) is False         # bool is not a room id
    assert savegame.is_valid_save({"room": 0, "obj_loc": "x"}, w) is False  # obj_loc not a dict
    # CONTENT, not just structure — these are the crafted saves that crash describe_room:
    assert savegame.is_valid_save({"room": 0, "obj_loc": {"999999": 0}}, w) is False  # bogus obj id
    assert savegame.is_valid_save({"room": 0, "obj_loc": {"6": "x"}}, w) is False      # loc not int
    assert savegame.is_valid_save({"room": 20, "state": {"dee": "x"}}, w) is False     # flag not int
    assert savegame.is_valid_save({"room": 0, "state": {"dde": True}}, w) is False      # bool not int


@pytest.mark.parametrize("hostile", [
    {"obj_loc": {"x": 1}},                      # no valid room
    {"room": 0, "obj_loc": {"999999": 0}},      # valid room + bogus object id -> would KeyError
    {"room": 20, "state": {"dee": "x"}},        # valid room + non-int flag -> would TypeError
    "not even a dict",
    None,
])
def test_do_laad_rejects_hostile_saves_without_crashing(hostile):
    w = load_file()
    eng = Engine(w, ScriptedIO([]))

    class JunkStore:                            # mimics a hostile client 'loaded' payload
        def load(self): return hostile
        def save(self, data): pass

    eng.store = JunkStore()
    eng.io = ScriptedIO([])
    eng.do_laad(None)                           # must not raise (would crash the web worker)
    assert w.message_text(188) in eng.io.text   # the load-fail message
    assert eng.room == 0                        # engine state untouched


def test_do_bewaar_skips_confirmation_when_store_declines():
    from engine.game import Engine
    from engine.io import ScriptedIO

    class DeclineStore:
        def save(self, data): return False
        def load(self): return None

    w = load_file()
    io = ScriptedIO([])
    eng = Engine(w, io, store=DeclineStore(), sandboxed=True)
    eng.do_bewaar(None)
    assert w.message_text(185) not in eng.io.text   # no false "saved" line
