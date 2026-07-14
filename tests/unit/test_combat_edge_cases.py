"""Combat / examine edge cases from the unseen-message audit (Section A5).

* SCHIJN with no lamp in hand -> msg 175, checked BEFORE any Dracula logic (EXE 0x4cc7).
* SCHIJN DRACULA when he is already banished (e70!=0) -> the bored taunt msg 258 (0x4cfd).
* TOON KRUIS out of context -> msg 259 "Er gebeurt niets." (EXE 0x4eec); at Dracula
  without the cross in hand -> msg 23 (0x4eff).
* SLA / DOOD the spider in its room -> it dodges, msg 272 (EXE 0x3b3d / 0x3c6b).
"""
from engine.data.loader import load_file
from engine.game import CARRIED, Engine
from engine.io import ScriptedIO
from engine.parser import parse_line
from engine.verb_events import KRUIS, LAMP, SPIN


def _engine(room, carrying=(), **flags):
    eng = Engine(load_file(), ScriptedIO([]))
    eng.room = room
    for oid in carrying:
        eng.obj_loc[oid] = CARRIED
    eng.state.update(flags)
    return eng, eng.world


def _run(eng, line):
    eng.io = ScriptedIO([])
    for cmd in parse_line(line):
        eng.dispatch(cmd)
    return eng.io.text


def test_schijn_without_lamp_is_msg175():
    eng, w = _engine(24, dde=24)                 # Dracula present, but no lamp in hand
    out = _run(eng, "schijn dracula")
    assert w.message_text(175) in out


def test_schijn_dracula_already_banished_is_msg258():
    eng, w = _engine(24, carrying=[LAMP], dde=24, e70=1)   # banished once already
    out = _run(eng, "schijn dracula")
    assert w.message_text(258) in out


def test_toon_kruis_out_of_context_is_msg259():
    eng, w = _engine(0, carrying=[KRUIS])
    out = _run(eng, "toon kruis")
    assert w.message_text(259) in out


def test_toon_kruis_at_dracula_without_cross_is_msg23():
    eng, w = _engine(24, dde=24)                 # Dracula here, but the cross not in hand
    out = _run(eng, "toon kruis")
    assert w.message_text(23) in out


def test_sla_spider_in_its_room_dodges_msg272():
    eng, w = _engine(34)
    eng.obj_loc[SPIN] = 34                        # the spider sits in room 34
    out = _run(eng, "sla spin")
    assert w.message_text(272) in out


def test_dood_spider_in_its_room_dodges_msg272():
    eng, w = _engine(34)
    eng.obj_loc[SPIN] = 34
    out = _run(eng, "dood spin")
    assert w.message_text(272) in out
