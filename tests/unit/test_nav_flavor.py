"""Small GA/KLIM failure-message catch-alls (unseen-message audit A2).

* GA/KLIM BOOM in the forest rooms 7-10 -> msg 12 (the tree is too slippery); EXE
  0x1377 (room>6 AND room<11). Room 17's real boomhut climb is separate.
* GA RAAM in the bedroom (room 1) -> msg 203 (the window is too small); EXE 0x17be.
* GA KIST with no ridable coffin (obj38) present -> msg 18; EXE 0x1b08.
"""
from engine.data.loader import load_file
from engine.game import Engine
from engine.io import ScriptedIO
from engine.parser import parse_line
from engine.verb_events import DOODSKIST_OPEN


def _run(eng, line):
    eng.io = ScriptedIO([])
    for cmd in parse_line(line):
        eng.dispatch(cmd)
    return eng.io.text


def test_klim_boom_forest_room_is_msg12():
    for room in (7, 8, 9, 10):
        eng = Engine(load_file(), ScriptedIO([]))
        eng.room = room
        out = _run(eng, "klim boom")
        assert eng.world.message_text(12) in out, f"room {room}"
        assert eng.room == room


def test_ga_raam_bedroom_is_msg203():
    eng = Engine(load_file(), ScriptedIO([]))
    eng.room = 1
    out = _run(eng, "ga raam")
    assert eng.world.message_text(203) in out


def test_ga_kist_without_coffin_is_msg18():
    eng = Engine(load_file(), ScriptedIO([]))
    eng.room = 5
    eng.obj_loc[DOODSKIST_OPEN] = 99          # coffin nowhere near
    out = _run(eng, "ga kist")
    assert eng.world.message_text(18) in out
