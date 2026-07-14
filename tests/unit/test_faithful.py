"""Tests pinning behaviour reconstructed from the EXE (docs/exe-map.md).

These assert the exact hardcoded EXE responses and the tricky parser rules that
distinguish this reconstruction from a naive one.
"""
from engine.game import new_game
from engine.io import ScriptedIO
from engine.parser import match_verb


def run(cmds):
    io = ScriptedIO(cmds + ["stop"])
    new_game(io).play()
    return io.text


def test_single_letter_verbs_do_not_shadow_longer_verbs():
    # K = KIJK, but KAP/KLIM/KNOOP must still resolve to themselves.
    assert match_verb("k") == "kijk"
    assert match_verb("kap") == "hak"
    assert match_verb("klim") == "ga"
    assert match_verb("i") == "inventaris"
    assert match_verb("ik") is None      # not a verb; must not match I


def test_take_message_is_exact_exe_string():
    # A single PAK success prints "Ok" (EXE 0x1e17, string 0x1592); "<name> : gepakt."
    # is only the PAK ALLE per-item line. Verified against the real game (SS-905).
    out = run(["ga zuid", "pak lantaarn"])
    assert "Ok" in out
    assert "gepakt" not in out


def test_drop_message_is_exact_exe_string():
    out = run(["ga zuid", "pak lamp", "drop lamp"])
    assert "kleine brandende lantaren : laten vallen." in out


def test_drop_synonyms_leg_zet():
    for verb in ("leg", "zet", "drop"):
        out = run(["ga zuid", "pak lamp", f"{verb} lamp"])
        assert "laten vallen." in out


def test_inventory_headers():
    assert "Je hebt niets bij je." in run(["i"])          # empty at start
    out = run(["ga zuid", "pak lamp", "i"])
    assert "Je draagt:" in out
    assert "kleine brandende lantaren" in out


def test_absent_object_message():
    out = run(["pak zwaard"])
    assert "Ik zie geen zwaard hier." in out


def test_blocked_movement_message():
    out = run(["ga noord"])                                # no north exit from house
    assert "Daar kan je niet heen." in out


def test_laat_is_not_a_verb():
    # "laten vallen" is only the drop *response*; LAAT is not a command word.
    assert match_verb("laat") is None
