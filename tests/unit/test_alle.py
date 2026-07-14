"""PAK/LEG/GOOI ALLE -> take-all / drop-all (EXE 0x2a47 re-dispatches per object).

The walkthrough's "Gooi alle voorwerpen die je bij je hebt weg" uses drop-all.
"""
from engine.data.loader import load_file
from engine.game import CARRIED, Engine
from engine.io import ScriptedIO
from engine.parser import parse_line


def _run(eng, line):
    eng.io = ScriptedIO([])
    for cmd in parse_line(line):
        eng.dispatch(cmd)
    return eng.io.text


def test_leg_alle_drops_every_carried_object():
    eng = Engine(load_file(), ScriptedIO([]))
    eng.room = 5
    for oid in (0, 1, 2):                            # carry lamp, touw, wig
        eng.obj_loc[oid] = CARRIED
    _run(eng, "leg alle")
    for oid in (0, 1, 2):
        assert eng.obj_loc[oid] == 5, f"obj {oid} should be dropped in room 5"


def test_gooi_alle_also_drops_everything():
    eng = Engine(load_file(), ScriptedIO([]))
    eng.room = 5
    eng.obj_loc[0] = CARRIED
    eng.obj_loc[1] = CARRIED
    _run(eng, "gooi alles")
    assert eng.obj_loc[0] == 5 and eng.obj_loc[1] == 5


def test_pak_alle_takes_takeable_room_objects():
    eng = Engine(load_file(), ScriptedIO([]))
    eng.room = 1                                     # the lantern (obj0) starts here
    _run(eng, "pak alle")
    assert eng.obj_loc[0] == CARRIED
