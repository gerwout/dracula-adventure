"""STOP/QUIT/EIND/OP/HOU -> the save-or-not quit prompt (audit A6, EXE 0x496c).

msg 187 asks whether to save before stopping; 'J' saves then ends, anything else
ends without saving. Both answers end the game.
"""
from engine.data.loader import load_file
from engine.game import Engine
from engine.io import ScriptedIO


def test_stop_prompts_then_quits_without_saving_on_n(monkeypatch, tmp_path):
    import engine.game as gmod
    monkeypatch.setattr(gmod, "SAVE_PATH", tmp_path / "s.json")
    io = ScriptedIO([])
    eng = Engine(load_file(), io)
    eng.io = ScriptedIO(["n"])
    eng.do_stop(None)
    assert eng.world.message_text(187) in eng.io.text
    assert eng.running is False
    assert not (tmp_path / "s.json").exists()      # N -> no save


def test_stop_saves_then_quits_on_j(monkeypatch, tmp_path):
    import engine.game as gmod
    monkeypatch.setattr(gmod, "SAVE_PATH", tmp_path / "s.json")
    eng = Engine(load_file(), ScriptedIO(["j"]))
    eng.do_stop(None)
    assert eng.running is False
    assert (tmp_path / "s.json").exists()          # J -> saved
    assert eng.world.message_text(185) in eng.io.text   # shows the "saving" line
