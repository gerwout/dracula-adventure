"""GUI input regressions (frontends/desktop_tk.py):

* clicking (not just a keypress) to dismiss the title screen must start the game AND
  leave focus on the input line -- the click handler returns "break" so the Text
  widget's default handler cannot re-grab focus;
* the input line has a right-click Cut/Copy/Paste/Select-all menu so a long command
  can be pasted with the mouse.

Headless: build the app on a withdrawn Tk root; skip if no display is available.
"""
import tkinter as tk

import pytest


def _app():
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("no display available")
    root.withdraw()
    import frontends.desktop_tk as d
    return root, d.DraculaApp(root)


def test_begin_starts_game_and_swallows_the_event():
    root, app = _app()
    try:
        app._awaiting = True
        assert app._begin() == "break"          # event swallowed so the Text widget's
        assert app._awaiting is False           # default click handler cannot steal focus
        assert str(app.entry["state"]) == "normal"
    finally:
        root.destroy()


def test_game_menu_save_and_load_run_the_commands(tmp_path, monkeypatch):
    # SAVE_PATH must be patched before the app (and its engine) is constructed: the
    # engine's default store captures the path once, at construction time.
    import engine.game as gmod
    monkeypatch.setattr(gmod, "SAVE_PATH", tmp_path / "s.json")
    root, app = _app()
    try:
        app._begin()                                   # dismiss the title -> into the game
        gm = root.nametowidget(app.menubar.entrycget(app._game_cascade, "menu"))
        labels = [gm.entrycget(i, "label") for i in range(gm.index("end") + 1)
                  if gm.type(i) == "command"]
        assert app.engine.lex.ui("MENU_SAVE_GAME") in labels
        assert app.engine.lex.ui("MENU_LOAD_GAME") in labels
        app._menu_save()                               # runs 'bewaar spel'
        assert (tmp_path / "s.json").exists()
        app.engine.room = 2                            # wander off, then load restores
        app._menu_load()                               # runs 'laad spel'
        assert app.engine.room == 0                    # back to the saved (house) room
    finally:
        root.destroy()


def test_clicking_the_game_log_keeps_typing_focus():
    root, app = _app()
    try:
        app._begin()                               # dismiss the title -> into the game
        # during play, clicks on the read-only log are handled (not left to the Text
        # widget's default focus-steal) ...
        assert app.text.bind("<Button-1>")
        # ... and the handler swallows the event ("break") after refocusing the input,
        # so clicking the black screen can't leave you unable to type.
        assert app._keep_entry_focus() == "break"
    finally:
        root.destroy()


def test_entry_has_rightclick_paste_menu():
    root, app = _app()
    try:
        assert app.entry.bind("<Button-3>")     # right-click is bound
        menu = app._entry_menu
        labels = [menu.entrycget(i, "label")
                  for i in range(menu.index("end") + 1)
                  if menu.type(i) == "command"]
        assert app.engine.lex.ui("MENU_PASTE") in labels
        assert app.engine.lex.ui("MENU_COPY") in labels
    finally:
        root.destroy()
