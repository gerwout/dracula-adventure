"""tkinter desktop frontend for Dracula.

A single scrolling text pane + an input line, driving the pure engine one command
at a time, with a faithful DOS look (black background, light-grey text, green
prompt). The game's own title screen is shown first; press any key (or click) to
begin.

Run:  python -m frontends.desktop_tk
"""
from __future__ import annotations

import sys
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine.game import new_game        # noqa: E402
from engine.i18n import AVAILABLE_LANGUAGES  # noqa: E402
from engine.io import IO                 # noqa: E402

# A faithful DOS look.
THEME = {
    "bg": "#000000", "fg": "#c8c8c8", "prompt": "#00c000",
    "input_bg": "#000000", "input_fg": "#00c000",
    "font": ("Consolas", 14), "cursor": "#00c000",
}


class TkIO(IO):
    def __init__(self, text_widget: tk.Text, read_line=None, read_key=None):
        self.text = text_widget
        # A callable that blocks for the next line of input (set by the app), used by
        # interactive commands that read follow-up lines (BUG / COMMENTAAR / the '/'
        # tester logbook).
        self._read_line = read_line
        # A callable that blocks for a single keypress (no Enter), used by the J/N
        # prompts: the STOP save-or-not prompt and the death reincarnation prompt.
        self._read_key = read_key

    def write(self, text: str) -> None:
        self.text.configure(state="normal")
        self.text.insert("end", text)
        self.text.see("end")
        self.text.configure(state="disabled")

    def read_command(self) -> str:
        return self._read_line() if self._read_line else ""

    def read_key(self) -> str:
        if self._read_key:
            return self._read_key()
        return self._read_line() if self._read_line else ""

    def clear(self) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")


class DraculaApp:
    def __init__(self, root: tk.Tk, txt_path=None, lang: str | None = "nl"):
        # lang=None shows the startup language picker (press 1/2, no Enter); a code plays
        # directly in that language. The default "nl" keeps headless/test construction
        # deterministic; main() passes None so a normal launch always asks.
        self.root = root
        root.title("Dracula Avontuur")
        root.geometry("860x620")
        self._set_window_icon()

        self.entry = tk.Entry(root, borderwidth=0)
        self.entry.pack(side="bottom", fill="x", ipady=6)

        self.scroll = tk.Scrollbar(root)
        self.scroll.pack(side="right", fill="y")
        self.text = tk.Text(root, wrap="word", state="disabled",
                            borderwidth=0, padx=10, pady=8,
                            yscrollcommand=self.scroll.set)
        self.text.pack(side="top", fill="both", expand=True)
        self.scroll.config(command=self.text.yview)
        self.entry.bind("<Return>", self.on_enter)

        self.txt_path = txt_path
        self.lang = lang or "nl"
        self._lang_var = tk.StringVar(value=self.lang)
        self._input_var = tk.StringVar()
        self._key_var = tk.StringVar()
        self._waiting = False       # True while an engine command is reading a line
        self.io = TkIO(self.text, read_line=self._read_line, read_key=self._read_key)
        self.apply_theme()
        if lang is None:
            self._choose_language()     # pick a language (single key) before the game
        else:
            self._start_game(lang)

    def _start_game(self, code: str):
        """Create the engine in `code`'s language and show the title screen."""
        self.lang = code
        self._lang_var.set(code)
        self.io.clear()
        self.engine = new_game(self.io, self.txt_path, explore=True, lang=code)
        self._build_menu()
        self._build_entry_menu()
        self._show_intro()

    # -- startup language picker (single key 1/2, no Enter) ---------------- #
    def _choose_language(self):
        """Show the language picker: press a single number key to choose, then play.
        No Enter needed — the same one-key selection the CLI uses."""
        self._lang_codes = list(AVAILABLE_LANGUAGES)
        self.io.clear()
        self.text.configure(state="normal")
        self.text.tag_configure("intro", justify="center")
        lines = ["Choose a language / Kies een taal:", ""]
        lines += [f"{n}.   {AVAILABLE_LANGUAGES[c]}" for n, c in enumerate(self._lang_codes, 1)]
        lines += ["", f"(press 1-{len(self._lang_codes)})"]
        for line in lines:
            self.text.insert("end", line + "\n", ("intro",))
        self.text.configure(state="disabled")
        self._choosing_lang = True
        self.entry.configure(state="disabled")
        self.root.bind("<Key>", self._on_language_key)
        self.text.focus_set()

    def _on_language_key(self, event):
        if not getattr(self, "_choosing_lang", False):
            return "break"
        ch = event.char
        if ch and ch.isdigit() and 1 <= int(ch) <= len(self._lang_codes):
            self._choosing_lang = False
            self.root.unbind("<Key>")
            self._start_game(self._lang_codes[int(ch) - 1])
        return "break"

    def _set_window_icon(self):
        """Use icon/vampire as the window (and taskbar) icon instead of the default
        Python/Tk feather. On Windows the multi-size .ico gives a crisp taskbar icon;
        elsewhere (and as a fallback) the 512x512 PNG is used via iconphoto."""
        icon_dir = Path(__file__).resolve().parents[1] / "icon"
        if sys.platform == "win32":
            try:
                self.root.iconbitmap(default=str(icon_dir / "vampire.ico"))
                return
            except Exception:
                pass
        try:
            # Keep a reference on self so Tk doesn't garbage-collect the image.
            self._icon_img = tk.PhotoImage(file=str(icon_dir / "vampire.png"))
            self.root.iconphoto(True, self._icon_img)
        except Exception:
            pass

    def _build_menu(self):
        # Build the menubar STRUCTURE once and keep references; the language-dependent
        # labels are set (and re-set on a language switch) by _relabel_menu via
        # entryconfigure. Rebuilding + re-assigning the whole menubar with
        # root.config(menu=...) does not reliably refresh on Windows, which left the
        # Save/Load/Help labels stuck in the launch language.
        menubar = tk.Menu(self.root)
        self._game_menu = tk.Menu(menubar, tearoff=0)
        self._game_menu.add_command(command=self.new_game)       # labels via _relabel_menu
        self._new_index = self._game_menu.index("end")
        self._game_menu.add_separator()
        self._game_menu.add_command(command=self._menu_save)
        self._game_menu.add_command(command=self._menu_load)
        self._save_index = self._game_menu.index("end") - 1
        self._load_index = self._game_menu.index("end")
        self._game_menu.add_separator()
        self._game_menu.add_command(command=self.root.destroy)
        self._quit_index = self._game_menu.index("end")
        menubar.add_cascade(menu=self._game_menu)
        self._game_cascade = menubar.index("end")
        # Language selector: pick a language between games. Choosing one starts a fresh
        # game in that language (re-showing the title screen). The radio entries stay in
        # each language's OWN name (endonym), the way a language picker should.
        lang_menu = tk.Menu(menubar, tearoff=0)
        for code, name in AVAILABLE_LANGUAGES.items():
            lang_menu.add_radiobutton(label=name, value=code, variable=self._lang_var,
                                      command=lambda c=code: self._set_language(c))
        menubar.add_cascade(menu=lang_menu)
        self._lang_cascade = menubar.index("end")
        self._help_menu = tk.Menu(menubar, tearoff=0)
        self._help_menu.add_command(command=self._show_commands)
        menubar.add_cascade(menu=self._help_menu)
        self._help_cascade = menubar.index("end")
        self.menubar = menubar
        self.root.config(menu=menubar)
        self._relabel_menu()

    def _relabel_menu(self):
        """Set every language-dependent menu label from the current engine's lexicon, so
        the whole menu follows the active language after a switch (updated in place, which
        refreshes reliably, rather than swapping the whole menubar)."""
        lex = self.engine.lex
        self._game_menu.entryconfigure(self._new_index, label=lex.ui("MENU_NEW_GAME"))
        self._game_menu.entryconfigure(self._save_index, label=lex.ui("MENU_SAVE_GAME"))
        self._game_menu.entryconfigure(self._load_index, label=lex.ui("MENU_LOAD_GAME"))
        self._game_menu.entryconfigure(self._quit_index, label=lex.ui("MENU_QUIT"))
        self._help_menu.entryconfigure(0, label=lex.ui("HELP_TITLE"))
        self.menubar.entryconfigure(self._game_cascade, label=lex.ui("MENU_GAME"))
        self.menubar.entryconfigure(self._lang_cascade, label=lex.ui("MENU_LANGUAGE"))
        self.menubar.entryconfigure(self._help_cascade, label=lex.ui("MENU_HELP"))

    def _build_entry_menu(self):
        """A right-click Cut/Copy/Paste/Select-all menu on the input line, so a long
        command can be pasted with the mouse (Ctrl+V still works too). Labels come from
        the lexicon so nothing is hardcoded."""
        lex = self.engine.lex
        m = tk.Menu(self.entry, tearoff=0)
        m.add_command(label=lex.ui("MENU_CUT"),
                      command=lambda: self.entry.event_generate("<<Cut>>"))
        m.add_command(label=lex.ui("MENU_COPY"),
                      command=lambda: self.entry.event_generate("<<Copy>>"))
        m.add_command(label=lex.ui("MENU_PASTE"),
                      command=lambda: self.entry.event_generate("<<Paste>>"))
        m.add_separator()
        m.add_command(label=lex.ui("MENU_SELECT_ALL"),
                      command=lambda: (self.entry.select_range(0, "end"),
                                       self.entry.icursor("end")))
        self._entry_menu = m
        self.entry.bind("<Button-3>", self._popup_entry_menu)

    def _popup_entry_menu(self, event):
        self.entry.focus_set()
        try:
            self._entry_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._entry_menu.grab_release()
        return "break"

    # -- Help: show the player's commands (behind a spoiler warning) ------- #
    def _command_reference_text(self) -> str:
        """The full, human-facing command reference: the intro line followed by the
        curated command list. Both parts come from the lexicon (HELP_INTRO +
        HELP_COMMANDS) so nothing player-facing is hardcoded and it stays
        translatable. The curated list is kept accurate to engine.parser._VERB_TABLE
        (one clear line per meaningful action, plus movement from the directions).
        Factored out so it can be unit-tested without opening the modal window."""
        lex = self.engine.lex
        intro = lex.ui("HELP_INTRO")
        body = lex.ui("HELP_COMMANDS")
        return f"{intro}\n\n{body}" if intro else body

    def _show_commands(self):
        """Warn first (in the original you had to discover the commands yourself),
        and only after the player confirms open a normal scrollable help window with
        the command reference."""
        lex = self.engine.lex
        if not messagebox.askyesno(lex.ui("HELP_WARNING_TITLE"),
                                   lex.ui("HELP_WARNING"), parent=self.root):
            return
        self._open_help_window(lex.ui("HELP_TITLE"),
                               self._command_reference_text())

    def _open_help_window(self, title: str, body: str) -> tk.Toplevel:
        """A normal (non-DOS) read-only, scrollable help window with a Close button --
        a plain light document window rather than the game's black console look."""
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry("660x560")
        win.transient(self.root)
        # Close button along the bottom; the text area fills the rest.
        tk.Button(win, text=self.engine.lex.ui("HELP_CLOSE"),
                  command=win.destroy).pack(side="bottom", pady=8)
        frame = tk.Frame(win)
        frame.pack(side="top", fill="both", expand=True, padx=10, pady=(10, 0))
        scroll = tk.Scrollbar(frame)
        scroll.pack(side="right", fill="y")
        text = tk.Text(frame, wrap="word", relief="solid", borderwidth=1,
                       padx=14, pady=12, bg="white", fg="black",
                       font=("Consolas", 11), yscrollcommand=scroll.set)
        text.pack(side="left", fill="both", expand=True)
        scroll.config(command=text.yview)
        text.insert("end", body)
        text.configure(state="disabled")
        win.bind("<Escape>", lambda _e: win.destroy())
        return win

    def apply_theme(self):
        t = THEME
        self.text.configure(bg=t["bg"], fg=t["fg"], font=t["font"],
                            insertbackground=t["cursor"])
        self.text.tag_configure("prompt", foreground=t["prompt"])
        self.text.tag_configure("cmd", foreground=t["prompt"])
        self.entry.configure(bg=t["input_bg"], fg=t["input_fg"], font=t["font"],
                            insertbackground=t["cursor"])
        self.root.configure(bg=t["bg"])

    # -- startup title screen: press any key (or click) to begin ----------- #
    _MODIFIER_KEYS = {
        "Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R",
        "Caps_Lock", "Num_Lock", "Win_L", "Win_R", "Super_L", "Super_R",
        "Meta_L", "Meta_R", "ISO_Level3_Shift",
    }

    def _show_intro(self):
        # A fresh, cleared screen each time (also on a reincarnation restart), with the
        # title screen horizontally centered in the window: the lexicon lines carry
        # 80-column centring spaces, so we strip them and let Tk centre each line to the
        # actual pane width.
        self.io.clear()
        self.text.configure(state="normal")
        self.text.tag_configure("intro", justify="center")
        for line in self.engine.lex.intro:
            self.text.insert("end", line.strip() + "\n", ("intro",))
        self.text.see("end")
        self.text.configure(state="disabled")
        self._awaiting = True
        self.entry.configure(state="disabled")
        self.root.bind("<Key>", self._begin)      # ANY key continues
        self.text.bind("<Button-1>", self._begin)
        self.text.focus_set()

    def _read_key(self) -> str:
        """Block for a single keypress (no Enter). Used by the J/N prompts — the STOP
        save-or-not prompt and the death reincarnation prompt — so 'J' acts at once."""
        self._key_var.set("")
        self.entry.configure(state="disabled")
        funcid = self.root.bind("<Key>", self._on_key)
        self.text.focus_set()
        self.root.wait_variable(self._key_var)
        try:
            self.root.unbind("<Key>", funcid)
        except Exception:
            pass
        self.entry.configure(state="normal")
        self.entry.focus_set()
        return self._key_var.get()

    def _on_key(self, event):
        # Ignore bare modifier presses; wait for a real key.
        if event.char == "" and event.keysym in self._MODIFIER_KEYS:
            return
        self._key_var.set(event.char or event.keysym)

    def _begin(self, _event=None):
        if not getattr(self, "_awaiting", False):
            return "break"
        self._awaiting = False
        self.root.unbind("<Key>")
        self.text.unbind("<Button-1>")
        self.io.clear()
        self.engine.start()
        self.entry.configure(state="normal")
        self.entry.focus_set()
        # A mouse click on the text pane would otherwise let the Text widget's own
        # default handler re-grab focus (leaving the input line unfocused, so nothing
        # you type shows up); take the focus back after the click is fully processed
        # and swallow the event so the default handler does not run.
        self.entry.after_idle(self.entry.focus_set)
        # During play, a click on the read-only game log must ALSO keep typing focus on
        # the input line (otherwise clicking the black screen -- e.g. after the window
        # regains focus -- leaves you unable to type).
        self.text.bind("<Button-1>", self._keep_entry_focus)
        return "break"

    def _keep_entry_focus(self, _event=None):
        """Clicking the read-only game log keeps focus on the input line (the log is
        output-only, so there is nothing to click into). Swallowing the event stops the
        Text widget's default handler from grabbing focus."""
        self.entry.focus_set()
        return "break"

    def new_game(self):
        self.io.clear()
        self.engine = new_game(self.io, self.txt_path, explore=True, lang=self.lang)
        self._relabel_menu()        # menu labels follow the selected language
        self._show_intro()

    def _set_language(self, code: str):
        """Switch language and start a fresh game in it (title screen shown in the new
        language). No-op if the language is already active."""
        if code == self.lang:
            return
        self.lang = code
        self._lang_var.set(code)
        self.new_game()

    def _read_line(self) -> str:
        """Block for the next input line via a nested event loop — lets interactive
        commands (BUG / COMMENTAAR / '/' tester / STOP J-N) read follow-up lines."""
        self._waiting = True
        self.entry.configure(state="normal")
        self.entry.focus_set()
        self.root.wait_variable(self._input_var)
        self._waiting = False
        return self._input_var.get()

    def on_enter(self, _event):
        line = self.entry.get()
        self.entry.delete(0, "end")
        self._echo(line)
        if self._waiting:                       # feed a command that is reading a line
            self._input_var.set(line)
            return
        self._submit(line)

    def _submit(self, text):
        """Run one game command and handle its outcome (reincarnation restart / game
        over). Shared by the Enter key and the Game > Bewaar/Laad menu items."""
        if self.engine.running:
            self.engine.submit(text)
        if self.engine.restart:                 # reincarnation (J at the death prompt):
            self.engine.restart = False         # a full restart to the opening screen.
            self.entry.configure(state="disabled")
            self.root.after(1200, self._show_intro)   # let the POEFF linger, then title
            return
        if not self.engine.running:
            self.io.write(f"\n{self.engine.lex.ui('GAME_OVER')}\n")

    # -- Game > Save / Load ------------------------------------------------- #
    def _menu_save(self):
        self._menu_action(self.engine.do_bewaar)

    def _menu_load(self):
        self._menu_action(self.engine.do_laad)

    def _menu_action(self, handler):
        """Run a Save/Load engine action from the menu. Calls the engine handler DIRECTLY
        rather than injecting a Dutch command string (which would not parse, or would echo
        Dutch, in a translated game); the handler prints its own save/load message in the
        active language. Only during normal play -- not on the title screen and not while
        an interactive command is reading input."""
        if getattr(self, "_awaiting", False) or self._waiting or not self.engine.running:
            return
        handler(None)

    def _echo(self, line: str):
        self.text.configure(state="normal")
        self.text.insert("end", "\n-> ", ("prompt",))
        self.text.insert("end", line + "\n", ("cmd",))
        self.text.see("end")
        self.text.configure(state="disabled")


def main():
    # Give the app its own taskbar identity (before the window is created) so Windows
    # shows OUR icon rather than grouping the window under python.exe's feather.
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "vanderveen.dracula.avontuur")
        except Exception:
            pass
    # No --lang -> show the startup language picker (press 1/2). --lang <code> skips it.
    lang = None
    argv = sys.argv[1:]
    for i, arg in enumerate(argv):
        if arg == "--lang" and i + 1 < len(argv) and argv[i + 1] in AVAILABLE_LANGUAGES:
            lang = argv[i + 1]
        elif arg.startswith("--lang=") and arg.split("=", 1)[1] in AVAILABLE_LANGUAGES:
            lang = arg.split("=", 1)[1]
    root = tk.Tk()
    DraculaApp(root, lang=lang)
    root.mainloop()


if __name__ == "__main__":
    main()
