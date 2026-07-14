"""GA STEE / GAT grave-stone crossing (unseen-message audit A2, EXE 0x1690).

Crossing 39->37 with the stone rotated (e42==1) prints msg 16 and does NOT
redescribe room 37 (EXE jmp 0x261, not the post-move describe). From room 37,
GA STEE/GAT prints msg 17 (the stone has closed behind you); no move.
"""
from engine.data.loader import load_file
from engine.game import Engine
from engine.io import ScriptedIO
from engine.parser import parse_line


def _run(eng, line):
    eng.io = ScriptedIO([])
    for cmd in parse_line(line):
        eng.dispatch(cmd)
    return eng.io.text


def test_ga_steen_39_to_37_prints_msg16_no_redescribe():
    eng = Engine(load_file(), ScriptedIO([]))
    eng.room = 39
    eng.state["e42"] = 1
    out = _run(eng, "ga steen")
    assert eng.room == 37
    assert eng.world.message_text(16) in out
    assert eng.world.rooms[37].lines[0] not in out     # NO room redescribe


def test_ga_steen_at_37_prints_msg17_no_move():
    eng = Engine(load_file(), ScriptedIO([]))
    eng.room = 37
    out = _run(eng, "ga steen")
    assert eng.room == 37
    assert eng.world.message_text(17) in out
