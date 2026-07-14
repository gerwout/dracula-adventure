"""Headless tests for the tkinter GUI Help menu (frontends/desktop_tk.py).

These build a real DraculaApp on a *withdrawn* Tk root (no visible window) and
check the Help menu wiring and the command-reference builder. If no display /
Tcl is available the whole module is skipped, so CI without a display stays green.

The command reference itself lives in the lexicon (engine/data/strings_nl.json:
ui.HELP_* keys); the modal warning dialog is deliberately not exercised here
(it would block), only the pure text builder and window construction are.
"""
from __future__ import annotations

import pytest

tk = pytest.importorskip("tkinter")
from tkinter import TclError  # noqa: E402

from frontends.desktop_tk import DraculaApp  # noqa: E402


@pytest.fixture
def app():
    try:
        root = tk.Tk()
    except TclError as exc:                      # no display available
        pytest.skip(f"no Tk display: {exc}")
    root.withdraw()
    a = DraculaApp(root)
    yield a
    try:
        root.destroy()
    except TclError:
        pass


def _menu_labels(menubar):
    labels = []
    for i in range(menubar.index("end") + 1):
        try:
            labels.append(menubar.entrycget(i, "label"))
        except TclError:                          # system/tearoff entry, no label
            pass
    return labels


def test_run_gui_launcher_exposes_main():
    import run_gui
    assert callable(run_gui.main)


def test_help_menu_present(app):
    assert "Help" in _menu_labels(app.menubar)   # MENU_HELP is "Help" in nl and en


def test_show_commands_callable(app):
    assert callable(app._show_commands)


def test_command_reference_non_empty_and_covers_actions(app):
    ref = app._command_reference_text()
    assert ref.strip()
    # A representative slice of the real verbs (engine.parser._VERB_TABLE) + movement.
    for needle in ("ga", "pak", "leg", "bekijk", "kijk", "gooi",
                   "bewaar spel", "laad spel", "stop"):
        assert needle in ref, needle


def test_command_reference_mentions_chaining(app):
    ref = app._command_reference_text()
    assert "ga noord . pak lamp . i" in ref


def test_command_reference_lists_all_meaningful_verbs(app):
    ref = app._command_reference_text().lower()
    for verb in ["klim", "volg", "draag", "knoop", "vraag", "luister", "slaap"]:
        assert verb in ref, f"Help is missing the '{verb}' command"


def test_help_intro_and_title_come_from_lexicon(app):
    lex = app.engine.lex
    assert lex.ui("HELP_TITLE")
    assert lex.ui("HELP_WARNING")
    assert lex.ui("HELP_WARNING_TITLE")
    # the builder prepends the intro line to the command body
    assert lex.ui("HELP_INTRO") in app._command_reference_text()


def _menu_state(app):
    g, mb, h = app._game_menu, app.menubar, app._help_menu
    return {
        "game": mb.entrycget(app._game_cascade, "label"),
        "lang": mb.entrycget(app._lang_cascade, "label"),
        "help": mb.entrycget(app._help_cascade, "label"),
        "new": g.entrycget(app._new_index, "label"),
        "save": g.entrycget(app._save_index, "label"),
        "load": g.entrycget(app._load_index, "label"),
        "quit": g.entrycget(app._quit_index, "label"),
        "helpcmd": h.entrycget(0, "label"),
    }


def test_every_menu_label_follows_the_language(app):
    # Every menu item (cascades + New/Save/Load/Quit + the Help command) is translated,
    # and a language switch updates them in place (the bug: stuck in the launch language).
    assert _menu_state(app) == {                                     # fixture launches in Dutch
        "game": "Spel", "lang": "Taal", "help": "Help", "new": "Nieuw spel",
        "save": "Bewaar spel", "load": "Laad spel", "quit": "Stoppen",
        "helpcmd": "Commando's"}
    app._set_language("en")
    assert _menu_state(app) == {
        "game": "Game", "lang": "Language", "help": "Help", "new": "New game",
        "save": "Save game", "load": "Load game", "quit": "Quit",
        "helpcmd": "Commands"}
    app._set_language("nl")
    assert _menu_state(app)["save"] == "Bewaar spel"


def test_startup_language_picker_single_key():
    # lang=None shows the one-key picker (no game yet); pressing a number starts the game
    # in that language -- no Enter needed.
    try:
        root = tk.Tk()
    except TclError as exc:
        pytest.skip(f"no Tk display: {exc}")
    root.withdraw()
    try:
        import types
        a = DraculaApp(root, lang=None)
        assert a._choosing_lang and not hasattr(a, "engine")   # waits before making a game
        screen = a.text.get("1.0", "end")
        assert "Nederlands" in screen and "English" in screen
        a._on_language_key(types.SimpleNamespace(char="2"))    # press '2' -> English
        assert a.lang == "en" and a.engine is not None and not a._choosing_lang
    finally:
        try:
            root.destroy()
        except TclError:
            pass


def test_menu_save_load_call_the_engine_directly(app):
    # Save/Load must invoke the engine handlers, NOT inject the Dutch command string
    # "bewaar spel"/"laad spel" (which would echo Dutch and fail to parse in a translation).
    app._begin()                          # leave the title screen so the game is running
    calls = []
    app.engine.do_bewaar = lambda cmd=None: calls.append("save")
    app.engine.do_laad = lambda cmd=None: calls.append("load")
    app._menu_save()
    app._menu_load()
    assert calls == ["save", "load"]
    log = app.text.get("1.0", "end")
    assert "bewaar spel" not in log and "laad spel" not in log


def _find_text(widget):
    """The Text widget, searched recursively (it now lives inside a Frame)."""
    if isinstance(widget, tk.Text):
        return widget
    for child in widget.winfo_children():
        found = _find_text(child)
        if found is not None:
            return found
    return None


def test_open_help_window_is_readonly(app):
    win = app._open_help_window("Commando's", "regel een\nregel twee")
    try:
        text = _find_text(win)
        assert text is not None, "help window has no Text widget"
        assert str(text.cget("state")) == "disabled"
        assert "regel een" in text.get("1.0", "end")
        # it is a normal (light) window, not the DOS console look
        assert str(text.cget("bg")) == "white"
        # and it has a Close button
        assert any(isinstance(w, tk.Button) for w in win.winfo_children())
    finally:
        win.destroy()
