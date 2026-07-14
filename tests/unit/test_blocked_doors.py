"""Guard-failed named transitions print the specific closed-door line, not the
generic "Daar kan je niet heen." (unseen-message audit, Section A1).

Each VERIFIED_NAMED transition with a flag guard has a bespoke EXE message for when
the guard fails (the door/gate is shut). The player must stay put and see it.
"""
from engine.data.loader import load_file
from engine.game import Engine
from engine.io import ScriptedIO
from engine.parser import parse_line


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


def test_castle_door_closed_says_msg13():
    eng, w = _engine(20, dee=0)                 # castle outer door slammed shut
    out = _run(eng, "ga kasteel")
    assert w.message_text(13) in out
    assert eng.room == 20                        # blocked, did not move


def test_castle_door_open_moves():
    eng, w = _engine(20, dee=1)
    _run(eng, "ga kasteel")
    assert eng.room == 21                        # guard holds -> move


def test_room30_gat_without_ladder_says_msg15():
    eng, w = _engine(30, e40=0)
    out = _run(eng, "ga gat")
    assert w.message_text(15) in out
    assert eng.room == 30


def test_room30_ladder_without_ladder_says_msg14():
    eng, w = _engine(30, e40=0)
    out = _run(eng, "ga ladder")
    assert w.message_text(14) in out


def test_window_closed_says_msg235():
    eng, w = _engine(0, e3c=1)                   # window shut
    out = _run(eng, "ga raam")
    assert w.message_text(235) in out
    assert eng.room == 0


def test_bedroom_door_locked_says_msg257():
    eng, w = _engine(22, e46=0)                  # bedroom-2 door locked
    out = _run(eng, "ga slaapkamer")
    assert w.message_text(257) in out
    assert eng.room == 22


def test_sesam_door_closed_says_msg268():
    eng, w = _engine(31, e48=0)                  # sesam door not opened
    out = _run(eng, "ga sesam")
    assert w.message_text(268) in out
    assert eng.room == 31
