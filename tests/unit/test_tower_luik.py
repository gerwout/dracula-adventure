"""GA LUIK tower-chest handler (unseen-message audit A2, EXE 0x3f22).

Away from the bedroom (room 1), GA LUIK: at the OPENED tower luik (obj23) descends
to slaapkamer 2 (room 24); at the still-closed tower luik (obj22) -> msg 168; with
no luik present -> msg 169.
"""
from engine.data.loader import load_file
from engine.game import Engine
from engine.io import ScriptedIO
from engine.parser import parse_line
from engine.verb_events import KIST_LUIK_DICHT, KIST_LUIK_OPEN


def _run(eng, line):
    eng.io = ScriptedIO([])
    for cmd in parse_line(line):
        eng.dispatch(cmd)
    return eng.io.text


def test_ga_luik_open_tower_luik_descends_to_24():
    eng = Engine(load_file(), ScriptedIO([]))
    eng.room = 29
    eng.obj_loc[KIST_LUIK_OPEN] = 29                # the opened luik is here
    _run(eng, "ga luik")
    assert eng.room == 24


def test_ga_luik_closed_tower_luik_is_msg168():
    eng = Engine(load_file(), ScriptedIO([]))
    eng.room = 29
    eng.obj_loc[KIST_LUIK_DICHT] = 29              # still-closed luik here
    out = _run(eng, "ga luik")
    assert eng.world.message_text(168) in out
    assert eng.room == 29


def test_ga_luik_no_luik_is_msg169():
    eng = Engine(load_file(), ScriptedIO([]))
    eng.room = 5                                     # no luik anywhere near
    out = _run(eng, "ga luik")
    assert eng.world.message_text(169) in out
