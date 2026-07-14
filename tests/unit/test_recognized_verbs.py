"""Recognized-but-mis-dispatched verbs (unseen-message audit, Section B).

These verbs are all in the parser table but were routed to _UNMAPPED ("Dat gaat
niet.") or to a fabricated handler. Each produces a specific EXE response:

* HELP/HULP -> a context quip (EXE 0x3010): msg 89 in normal play, msg 87 in the
  castle (rooms 21-38) once the door has slammed (dee==0), msg 88 elsewhere with
  dee==0 — NOT the "Spelregels" rules block (that is LEES BRIEFJE only, msg 201).
* BREEK/SCHEU/VERNI -> msg 4 (EXE 0x9e2).
* ZEG -> msg 5 (EXE 0xc83).
* WACHT/RUST -> msg 215 (EXE 0x4ca0).
* GIL/ROEP/SCHRE/BRUL -> bare scream msg 153 (EXE 0x3d3c); with a word it echoes.
* SESAM/HOKUS/HOCUS -> msg 210 (EXE 0xd22) — the room-31 secret word is separate.
"""
from engine.data.loader import load_file
from engine.game import Engine
from engine.io import ScriptedIO
from engine.parser import parse_line


def _engine(room=0):
    eng = Engine(load_file(), ScriptedIO([]))
    eng.room = room
    return eng, eng.world


def _run(eng, line):
    eng.io = ScriptedIO([])
    for cmd in parse_line(line):
        eng.dispatch(cmd)
    return eng.io.text


def test_help_normal_play_is_quip_not_rules():
    eng, w = _engine(0)                        # dee==1 (door open) at start
    out = _run(eng, "help")
    assert w.message_text(89) in out           # "Geen paniek..geen paniek.."
    assert "Spelregels" not in out


def test_help_in_castle_after_door_slam():
    eng, w = _engine(25)                        # castle upper (21..38)
    eng.state["dee"] = 0                         # door slammed shut
    out = _run(eng, "help")
    assert w.message_text(87) in out            # "Pakke wat je pakke kan."


def test_help_outside_castle_after_door_slam():
    eng, w = _engine(5)                          # room < 21
    eng.state["dee"] = 0
    out = _run(eng, "help")
    assert w.message_text(88) in out            # "Heb je geen slaap ..."


def test_breek_is_message_4():
    eng, w = _engine(0)
    assert w.message_text(4) in _run(eng, "breek raam")


def test_zeg_is_message_5():
    eng, w = _engine(0)
    assert w.message_text(5) in _run(eng, "zeg iets")


def test_wacht_is_message_215():
    eng, w = _engine(0)
    assert w.message_text(215) in _run(eng, "wacht")


def test_gil_bare_is_scream_153():
    eng, w = _engine(0)
    assert w.message_text(153) in _run(eng, "gil")


def test_sesam_outside_room31_is_message_210():
    eng, w = _engine(0)
    assert w.message_text(210) in _run(eng, "sesam")


def test_op_quits_the_game():
    # OP and HOU reach the EXE quit handler (0x496c). We route them to STOP; the
    # msg-187 J/N save-prompt itself is deferred.
    eng, w = _engine(0)
    eng.dispatch(next(iter(parse_line("op"))))
    assert eng.running is False


def test_hou_quits_the_game():
    eng, w = _engine(0)
    eng.dispatch(next(iter(parse_line("hou op"))))
    assert eng.running is False
