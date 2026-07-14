"""In web (sandboxed) mode, BUG/COMMENTAAR and the / tester are disabled and write nothing."""
from engine.game import new_game
from engine.io import ScriptedIO
from engine.i18n import AVAILABLE_LANGUAGES


def test_sandboxed_bug_shows_notice_and_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    io = ScriptedIO([])
    eng = new_game(io, explore=True, sandboxed=True)
    eng.do_bug(None)
    assert eng.lex.ui("WEB_DISABLED") in io.text
    assert not (tmp_path / "DRACULA.BUG").exists()


def test_sandboxed_tester_shows_notice_and_writes_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    io = ScriptedIO([])
    eng = new_game(io, explore=True, sandboxed=True)
    eng.do_tester(None)
    assert eng.lex.ui("WEB_DISABLED") in io.text
    assert not (tmp_path / "TESTER").exists()


def test_non_sandboxed_bug_still_works(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    io = ScriptedIO(["Piet", "een bug", "."])   # name, one line, end
    eng = new_game(io, explore=True)             # default: not sandboxed
    eng.do_bug(None)
    assert (tmp_path / "DRACULA.BUG").exists()


def test_web_disabled_string_available_in_every_language():
    for lang in AVAILABLE_LANGUAGES:
        eng = new_game(ScriptedIO([]), explore=True, lang=lang, sandboxed=True)
        assert eng.lex.ui("WEB_DISABLED").strip(), f"{lang}: WEB_DISABLED is empty"
