"""Save / load — BEWAAR SPEL & LAAD SPEL (see docs/savegame.md).

The original serializes the object-location array + current room + the DGROUP state
flags to DRACULA.SAV. The old Engine._state() saved self.flags (the unused bool dict)
and dropped self.state (the real flags) — these tests pin the corrected round-trip.
"""
import json

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
