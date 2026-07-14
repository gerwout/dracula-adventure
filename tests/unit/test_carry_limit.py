"""PAK carry limit (unseen-message audit A6/C1, EXE 0x1e00 numcmp vs [0x101c]=7.0).

The original blocks a take with msg 22 once you already hold the limit of items
(the DGROUP constant [0x101c] decodes to MBF 7.0). Verified statically: the object
records carry no small per-item weight field (the only numeric field is the 9..71
'attribute', too large to sum under 7), so [0xe4a] is an item COUNT, limit 7.
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


def test_pak_refused_when_already_carrying_seven():
    eng = Engine(load_file(), ScriptedIO([]))
    eng.room = 1                                   # the lantern (obj0) is here
    for oid in range(3, 10):                        # pre-load 7 carried items
        eng.obj_loc[oid] = CARRIED
    assert sum(1 for v in eng.obj_loc.values() if v == CARRIED) == 7
    out = _run(eng, "pak lantaarn")
    assert eng.world.message_text(22) in out
    assert eng.obj_loc[0] != CARRIED               # not picked up


def test_pak_allowed_below_the_limit():
    eng = Engine(load_file(), ScriptedIO([]))
    eng.room = 1
    for oid in range(3, 9):                          # 6 carried -> a 7th is fine
        eng.obj_loc[oid] = CARRIED
    out = _run(eng, "pak lantaarn")
    assert eng.obj_loc[0] == CARRIED
    assert "Ok" in out
