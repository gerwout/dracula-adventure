"""OPEN BOEK -> the "just read it" quip (unseen-message audit A5, EXE 0x2ece).

When the vampire handbook (obj4) is present, trying to OPEN it prints msg 213
instead of the generic "hoe je dat wilt openen" line (msg 82).
"""
from engine.data.loader import load_file
from engine.game import CARRIED, Engine
from engine.io import ScriptedIO
from engine.parser import parse_line
from engine.verb_events import BOEK


def _run(eng, line):
    eng.io = ScriptedIO([])
    for cmd in parse_line(line):
        eng.dispatch(cmd)
    return eng.io.text


def test_open_boek_when_carried_is_msg213():
    eng = Engine(load_file(), ScriptedIO([]))
    eng.room = 0
    eng.obj_loc[BOEK] = CARRIED
    assert eng.world.message_text(213) in _run(eng, "open boek")


def test_open_boek_absent_falls_through_to_82():
    eng = Engine(load_file(), ScriptedIO([]))
    eng.room = 0                                   # book not here
    assert eng.world.message_text(82) in _run(eng, "open boek")
