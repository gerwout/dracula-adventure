"""BUG / COMMENTAAR — append a bug report to DRACULA.BUG (EXE handler 0x3fd6).

Typing BUG (or COMMENTAAR) asks for your name (messages[183]), then for the report
text terminated by a line with just '.' (messages[184]), and appends it to the
DRACULA.BUG file — recreating the original's comment/bug logbook.
"""
from engine.data.loader import load_file
from engine.game import Engine
from engine.io import ScriptedIO


def test_bug_appends_report_to_file(tmp_path, monkeypatch):
    import engine.game as game
    monkeypatch.setattr(game, "BUG_PATH", tmp_path / "DRACULA.BUG")
    w = load_file()
    # io feeds: the name, two report lines, then the '.' terminator.
    eng = Engine(w, ScriptedIO(["Jan de Tester", "de deur klemt", "en het raam ook", "."]))
    eng.submit("bug")

    assert w.message_text(183) in eng.io.text          # "... tiep eerst je naam in..."
    assert w.message_text(184) in eng.io.text          # "Typ nu in wat je op je lever hebt..."
    body = (tmp_path / "DRACULA.BUG").read_text(encoding="cp437")
    assert "Jan de Tester" in body
    assert "de deur klemt" in body
    assert "en het raam ook" in body


def test_bug_creates_file_with_header_when_missing(tmp_path, monkeypatch):
    import engine.game as game
    monkeypatch.setattr(game, "BUG_PATH", tmp_path / "DRACULA.BUG")
    eng = Engine(load_file(), ScriptedIO(["Piet", "iets", "."]))
    eng.submit("bug")
    body = (tmp_path / "DRACULA.BUG").read_text(encoding="cp437")
    assert "Dracula Buglijst" in body                  # the header is created


def test_commentaar_uses_the_same_logbook(tmp_path, monkeypatch):
    # The commentaar verb is invoked by the KOMMA/COMMA token (4-char+ prefix), not
    # by literally typing "commentaar" (which prefix-mismatches COMMA).
    import engine.game as game
    monkeypatch.setattr(game, "BUG_PATH", tmp_path / "DRACULA.BUG")
    eng = Engine(load_file(), ScriptedIO(["Klaas", "leuk spel", "."]))
    eng.submit("komma")
    assert "leuk spel" in (tmp_path / "DRACULA.BUG").read_text(encoding="cp437")
