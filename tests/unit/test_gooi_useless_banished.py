"""GOOI KNOF at a re-present Dracula after the banish -> msg 150 (audit A5, EXE 0x4bce).

The else of the garlic-throw combat: e70==1 (already banished) and e76==0 (coffin
not yet opened) -> 'Dracula ontwijkt met gemak alle aanvallen.'
"""
from engine.data.loader import load_file
from engine.game import CARRIED, Engine
from engine.io import ScriptedIO
from engine.parser import parse_line
from engine.verb_events import KNOFLOOK


def test_gooi_knoflook_useless_after_banish():
    eng = Engine(load_file(), ScriptedIO([]))
    eng.room = 24
    eng.state["dde"] = 24            # Dracula present
    eng.state["e70"] = 1            # already banished once
    eng.state["e76"] = 0            # coffin not opened
    eng.obj_loc[KNOFLOOK] = CARRIED
    io = eng.io = ScriptedIO([])
    for cmd in parse_line("gooi knoflook"):
        eng.dispatch(cmd)
    assert eng.world.message_text(150) in io.text
