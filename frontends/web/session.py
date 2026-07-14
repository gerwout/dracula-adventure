"""Per-connection session controller — one engine, driven exactly like the tkinter GUI
(intro -> press-a-key -> play, with reincarnation restart and a menu that calls the
engine handlers directly). Runs in the connection's worker thread. Owns nothing shared."""
from __future__ import annotations

from engine.game import new_game
from engine.i18n import AVAILABLE_LANGUAGES

from .webio import Channel, WebIO, WebSaveStore


class Session:
    def __init__(self, channel: Channel):
        self.ch = channel
        self.io = WebIO(channel)
        self.store = WebSaveStore(channel)
        self.engine = None
        self.lang = "nl"

    # -- entry point (worker thread) --------------------------------------- #
    def run(self) -> None:
        self.ch.send({"t": "langs", "available": AVAILABLE_LANGUAGES})
        pending = self._wait_start()
        while pending is not None:
            self.lang = pending.get("lang") if pending.get("lang") in AVAILABLE_LANGUAGES else "nl"
            pending = self._play_one_game()          # -> next 'start' | None | {"kind":"over"}
            if pending is not None and pending.get("kind") == "over":
                pending = self._wait_start()

    def _wait_start(self):
        """Block until the client picks a language ('start'); None on disconnect."""
        self.ch.send({"t": "await", "mode": "start"})
        while True:
            ev = self.ch.get()
            if ev.get("kind") == "start":
                return ev
            if ev.get("kind") == "eof":
                return None

    def _play_one_game(self):
        self.engine = new_game(self.io, explore=True, lang=self.lang,
                               store=self.store, sandboxed=True)
        self._send_menu_labels()
        while True:                                  # reincarnation restart loop
            self.engine.restart = False
            self.io.clear()
            self.engine.intro()
            ev = self._await_dismiss()               # press a key OR a 'start'
            if ev is None:
                return None
            if ev.get("kind") == "start":
                return ev
            self.io.clear()
            self.engine.start()
            ev = self._command_loop()
            if ev is None:
                return None
            if ev.get("kind") == "start":
                return ev
            if self.engine.restart:
                continue                             # reincarnation -> re-show intro
            self.io.write("\n" + self.engine.lex.ui("GAME_OVER") + "\n")
            return {"kind": "over"}

    def _await_dismiss(self):
        self.ch.send({"t": "await", "mode": "key", "menu": True})
        while True:
            ev = self.ch.get()
            kind = ev.get("kind")
            if kind in ("key", "line"):
                return ev
            if kind == "start":
                return ev
            if kind == "eof":
                return None
            # menu events at the title -> ignored (client keeps New/Language as 'start')

    def _command_loop(self):
        while self.engine.running and not self.engine.restart:
            self.ch.send({"t": "await", "mode": "line", "menu": True})
            ev = self.ch.get()
            kind = ev.get("kind")
            if kind == "line":
                self.engine.submit(ev.get("text", ""))
            elif kind == "menu":
                self._menu(ev.get("action"), ev.get("arg"))
            elif kind == "start":
                return ev
            elif kind == "eof":
                return None
        return {"kind": "ended"}

    # -- menu (top level only, mirrors the GUI's flag-guarded menu) --------- #
    def _menu(self, action, arg=None) -> None:
        if action == "save":
            self.engine.do_bewaar(None)              # calls WebSaveStore.save
        elif action == "load":
            self.engine.do_laad(None)                # calls WebSaveStore.load (blocks for reply)
        elif action == "help":
            lex = self.engine.lex
            intro = lex.ui("HELP_INTRO")
            body = lex.ui("HELP_COMMANDS")
            self.ch.send({"t": "help", "title": lex.ui("HELP_TITLE"),
                          "body": f"{intro}\n\n{body}" if intro else body})
        # "new" / "lang" are the client re-sending 'start' — handled by the loops above.

    def _send_menu_labels(self) -> None:
        lex = self.engine.lex
        self.ch.send({"t": "menu-labels", "labels": {
            "game": lex.ui("MENU_GAME"), "new": lex.ui("MENU_NEW_GAME"),
            "save": lex.ui("MENU_SAVE_GAME"), "load": lex.ui("MENU_LOAD_GAME"),
            "language": lex.ui("MENU_LANGUAGE"), "help": lex.ui("HELP_TITLE"),
        }, "lang": self.lang})
