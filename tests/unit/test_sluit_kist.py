"""SLUIT KIST per-room replies (unseen-message audit A4, EXE 0x3d90).

The engine fell back to the generic msg 165 for every SLUIT KIST; the original has
four distinct replies by room and coffin state.
"""
from engine.data.loader import load_file
from engine.game import Engine
from engine.io import ScriptedIO
from engine.parser import parse_line
from engine.verb_events import DOODSKIST


def _engine(room, **flags):
    eng = Engine(load_file(), ScriptedIO([]))
    eng.room = room
    eng.state.update(flags)
    return eng, eng.world


def _run(eng, line):
    eng.io = ScriptedIO([])
    for cmd in parse_line(line):
        eng.dispatch(cmd)
    return eng.io.text


def test_sluit_kist_room2_is_msg206():
    eng, w = _engine(2)
    assert w.message_text(206) in _run(eng, "sluit kist")


def test_sluit_kist_room14_is_msg159():
    eng, w = _engine(14)
    assert w.message_text(159) in _run(eng, "sluit kist")


def test_sluit_kist_at_coffin_unopened_is_msg240():
    eng, w = _engine(37, e76=0)                  # Dracula's closed coffin sits in room 37
    assert w.message_text(240) in _run(eng, "sluit kist")


def test_sluit_kist_at_coffin_opened_is_msg241():
    eng, w = _engine(37, e76=1)
    assert w.message_text(241) in _run(eng, "sluit kist")


def test_sluit_kist_elsewhere_is_msg160():
    eng, w = _engine(0)                          # no chest here
    assert w.message_text(160) in _run(eng, "sluit kist")
