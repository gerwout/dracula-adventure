"""Fidelity fixes derived from real-game screenshots (thatDOSguy / Anonymous GIFs
in C:\\dracdos\\screenshots) cross-checked against the DRACULA.EXE disassembly.

Each behaviour below is proven by a screenshot of the original game AND the EXE:

* Single PAK success prints "Ok" (EXE 0x1e17, string 0x1592) — the "<name> : gepakt."
  form (string 0x159e) is only the per-item line of PAK ALLE.
* KIJK <noun> examines exactly like BEKIJK (EXE dispatch 0x71d); bare KIJK
  redescribes the room (EXE 0x716). BEKIJK/LEES with no noun -> msg 121.
* The generic examine else prints msg 121 when a matching object is present OR no
  noun was given, and msg 122 for a noun that matches nothing (EXE 0x3803/0x3810/0x3819).
* GA BED / GA SLAAP route into the SLAAP handler (EXE 0x1298 -> 0x392a).
"""
from engine.data.loader import load_file
from engine.game import CARRIED, Engine
from engine.io import ScriptedIO
from engine.parser import parse_line


def _engine(room, carrying=(), placed=None):
    eng = Engine(load_file(), ScriptedIO([]))
    eng.room = room
    for oid in carrying:
        eng.obj_loc[oid] = CARRIED
    for oid, loc in (placed or {}).items():
        eng.obj_loc[oid] = loc
    return eng, eng.world


def _run(eng, line):
    eng.io = ScriptedIO([])
    for cmd in parse_line(line):
        eng.dispatch(cmd)
    return eng.io.text


# --------------------------------------------------------------- PAK success = "Ok"
def test_single_pak_prints_ok_not_gepakt():
    # SS-905 (real game): `pak lantaren` -> `Ok`. EXE 0x1e17 prints "Ok" (0x1592);
    # " : gepakt." (0x159e) is only the PAK ALLE per-item suffix.
    eng, w = _engine(1)                       # the lantern (obj0) starts in room 1
    out = _run(eng, "pak lantaarn")
    assert eng.obj_loc[0] == CARRIED
    assert out.strip() == "Ok"
    assert "gepakt" not in out


# ------------------------------------------------------------- KIJK <noun> examines
def test_kijk_noun_examines_present_object():
    # SS-905: `kijk lantaren` -> msg 121 ("Zover ik het kan beoordelen...").
    eng, w = _engine(1)
    out = _run(eng, "kijk lantaarn")
    assert w.message_text(121) in out


def test_kijk_unmatched_noun_says_niets_bijzonders_aan():
    # SS-6010: `kijk door` -> msg 122 ("Ik zie er niets bijzonders aan.").
    eng, w = _engine(0)
    out = _run(eng, "kijk zwaard")
    assert w.message_text(122) in out


def test_bare_kijk_redescribes_the_room():
    # EXE 0x716: bare KIJK (no noun) redescribes the current room, NOT msg 121.
    eng, w = _engine(0)
    out = _run(eng, "kijk")
    assert w.rooms[0].lines[0] in out


# ---------------------------------------------------- bare BEKIJK / LEES -> msg 121
def test_bare_bekijk_says_niets_bijzonders_mee():
    # SS-906: bare `bekijk` -> msg 121 (NOT a room redescription).
    eng, w = _engine(0)
    out = _run(eng, "bekijk")
    assert w.message_text(121) in out
    assert w.rooms[0].lines[0] not in out


def test_bare_lees_says_niets_bijzonders_mee():
    # SS-6010: bare `lees` -> msg 121.
    eng, w = _engine(0)
    out = _run(eng, "lees")
    assert w.message_text(121) in out
    assert w.rooms[0].lines[0] not in out


# ------------------------------------------------------------- GA BED / GA SLAAP
def test_ga_bed_in_bedroom_sleeps():
    # SS-905: `ga bed` in the bedroom (room 1) -> msg 124 (wake up fit). EXE 0x1298
    # routes GA BED into the SLAAP handler (0x392a).
    eng, w = _engine(1)
    out = _run(eng, "ga bed")
    assert w.message_text(124) in out


def test_ga_slapen_in_bedroom_sleeps():
    # EXE 0x1277/0x1298: GA SLAPEN also routes into the SLAAP handler. The EXE token is
    # "SLAP" (the 4-char prefix of SLAPEN), so GA SLAP/SLAPEN match but GA SLAAP does not.
    eng, w = _engine(1)
    out = _run(eng, "ga slapen")
    assert w.message_text(124) in out
