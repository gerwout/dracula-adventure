"""The hidden '/' tester-feedback logbook (EXE 0x5664) + startup pause/attribution."""
import engine.game as gmod
from engine.game import Engine, new_game
from engine.data.loader import load_file
from engine.io import IO, ScriptedIO


def test_slash_triggers_tester_and_writes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(gmod, "TESTER_PATH", tmp_path / "TESTER")
    monkeypatch.setattr(gmod, "TESTER_OLD_PATH", tmp_path / "TESTER.OLD")
    io = ScriptedIO(["mijn opmerking", "nog een", "."])
    eng = Engine(load_file(), io)
    eng.submit("/")
    assert "Hallo beste tester." in io.text
    assert "commentaar -->" in io.text
    saved = (tmp_path / "TESTER").read_text(encoding="cp437")
    assert "mijn opmerking" in saved and "nog een" in saved


def test_slash_is_parsed_as_tester_verb():
    from engine.parser import parse_line
    assert parse_line("/")[0].verb == "tester"


def test_intro_has_rewrite_attribution_and_original_copyright():
    io = ScriptedIO(["stop", "n"])
    eng = new_game(io)
    eng.play()
    assert "Gerwout van der Veen" in io.text
    assert "originele auteursrechten" in io.text
    assert "(c) 1982 Incore Automatisering" in io.text     # original copyright kept
    assert "Druk een toets om te beginnen" in io.text


def test_play_waits_for_a_keypress_before_the_game():
    calls = {"pause": 0}

    class SpyIO(ScriptedIO):
        def pause(self):
            calls["pause"] += 1

    io = SpyIO(["stop", "n"])
    new_game(io).play()
    assert calls["pause"] == 1                              # press-a-key happened once
