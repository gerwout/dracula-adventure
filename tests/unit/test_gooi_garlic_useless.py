"""Repeated / endgame GOOI KNOF at Dracula -> msg 258 (unseen-message audit A5, EXE 0x4b84).

Once Dracula's coffin has been opened (e76!=0), throwing garlic at him no longer
works -- "Deze pogingen halen niets meer uit. Dracula lijkt verveeld...".
"""
from engine.data.loader import load_file
from engine.game import CARRIED, Engine
from engine.io import ScriptedIO
from engine.parser import parse_line
from engine.verb_events import KNOFLOOK


def _run(eng, line):
    eng.io = ScriptedIO([])
    for cmd in parse_line(line):
        eng.dispatch(cmd)
    return eng.io.text


def test_gooi_knoflook_useless_once_coffin_opened():
    eng = Engine(load_file(), ScriptedIO([]))
    eng.room = 24
    eng.state["dde"] = 24            # Dracula present
    eng.state["e76"] = 1            # his coffin has been opened
    eng.obj_loc[KNOFLOOK] = CARRIED
    out = _run(eng, "gooi knoflook")
    assert eng.world.message_text(258) in out


def test_gooi_knoflook_still_banishes_midgame():
    # Regression: with the coffin unopened (e76==0), the mid-game banish still fires.
    eng = Engine(load_file(), ScriptedIO([]))
    eng.room = 24
    eng.state["dde"] = 24
    eng.state["e74"] = 2
    eng.obj_loc[KNOFLOOK] = CARRIED
    _run(eng, "gooi knoflook")
    assert eng.state["e74"] == 0     # drove him back
