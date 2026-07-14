"""OPEN LUIK away from any hatch -> msg 77 (unseen-message audit A5, EXE 0x2f20).

The room-1 bedroom hatch (69/70/71) and the tower-chest luik (78/79) are handled
first; anywhere else, OPEN LUIK -> msg 77 'Ik zie geen luik.' (not the generic 82).
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


def test_open_luik_no_hatch_is_msg77():
    eng = Engine(load_file(), ScriptedIO([]))
    eng.room = 5                                     # no hatch here
    out = _run(eng, "open luik")
    assert eng.world.message_text(77) in out
