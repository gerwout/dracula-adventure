"""Per-connection session controller — one engine, driven exactly like the tkinter GUI
(intro -> press-a-key -> play, with reincarnation restart and a menu that calls the
engine handlers directly). Runs in the connection's worker thread. Owns nothing shared."""
from __future__ import annotations

from engine import savegame
from engine.game import new_game
from engine.i18n import AVAILABLE_LANGUAGES

from .webio import Channel, WebIO, WebSaveStore


class Session:
    def __init__(self, channel, token=None, snapshotter=None,
                 resume_state=None, resume_lang=None):
        self.ch = channel
        self.io = WebIO(channel)
        self.store = WebSaveStore(channel)
        self.engine = None
        self.lang = resume_lang or "nl"
        self.token = token
        self._snapshotter = snapshotter
        self._resume_state = resume_state
        self._resume_lang = resume_lang

    # -- entry point (worker thread) --------------------------------------- #
    def run(self) -> None:
        self.ch.send({"t": "langs", "available": AVAILABLE_LANGUAGES})
        if self._resume_state is not None:
            self.lang = self._resume_lang if self._resume_lang in AVAILABLE_LANGUAGES else "nl"
            pending = self._play_one_game(resume_state=self._resume_state)
            if pending is not None and pending.get("kind") == "over":
                pending = self._wait_start()
        else:
            pending = self._wait_start()
        while pending is not None:
            self.lang = pending.get("lang") if pending.get("lang") in AVAILABLE_LANGUAGES else "nl"
            pending = self._play_one_game()          # -> next 'start' | None | {"kind":"over"}
            if pending is not None and pending.get("kind") == "over":
                pending = self._wait_start()

    def _menu_flags(self, playing: bool) -> dict:
        # Save/Load only make sense while a game is being played; Help needs a live engine
        # (its text comes from the lexicon); New/Language are always available.
        has_engine = self.engine is not None
        return {"new": True, "language": True, "help": has_engine,
                "save": playing, "load": playing}

    def _send_help(self) -> None:
        lex = self.engine.lex
        intro = lex.ui("HELP_INTRO")
        body = lex.ui("HELP_COMMANDS")
        self.ch.send({"t": "help", "title": lex.ui("HELP_TITLE"),
                      "body": f"{intro}\n\n{body}" if intro else body})

    def _wait_start(self):
        """Block until the client picks a language ('start'); None on disconnect."""
        self.ch.send({"t": "await", "mode": "start", "menu": self._menu_flags(False)})
        while True:
            ev = self.ch.get()
            kind = ev.get("kind")
            if kind == "start":
                return ev
            if kind == "eof":
                return None
            if kind == "menu" and ev.get("action") == "help" and self.engine is not None:
                self._send_help()
            # save/load/new-as-command are disabled in this state -> ignored

    def _snapshot_now(self) -> None:
        if self._snapshotter and self.engine is not None:
            try:
                self._snapshotter(savegame.serialize(self.engine), self.lang)
            except Exception:
                pass   # snapshotting must never break play

    def _play_one_game(self, resume_state=None):
        self.engine = new_game(self.io, explore=True, lang=self.lang,
                               store=self.store, sandboxed=True)
        self._send_menu_labels()
        first = True
        while True:                                  # reincarnation restart loop
            self.engine.restart = False
            if resume_state is not None and first:
                savegame.restore(self.engine, resume_state)
                self.io.clear()
                self.ch.send({"t": "screen", "kind": "game"})
                self.engine.describe_room()          # cold resume redraws the room
            else:
                self.io.clear()
                self.ch.send({"t": "screen", "kind": "title"})
                self.engine.intro()
                ev = self._await_dismiss()           # press a key OR a 'start'
                if ev is None:
                    return None
                if ev.get("kind") == "start":
                    return ev
                self.io.clear()
                self.ch.send({"t": "screen", "kind": "game"})
                self.engine.start()
            first = False
            ev = self._command_loop()
            if ev is None:
                return None
            if ev.get("kind") == "start":
                return ev
            if self.engine.restart:
                resume_state = None
                continue
            self.io.write("\n" + self.engine.lex.ui("GAME_OVER") + "\n")
            return {"kind": "over"}

    def _await_dismiss(self):
        keys = [{"label": self.engine.lex.ui("BTN_CONTINUE"), "ch": " "}] if self.engine else None
        self.ch.send({"t": "await", "mode": "key", "menu": self._menu_flags(False), "keys": keys})
        while True:
            ev = self.ch.get()
            kind = ev.get("kind")
            if kind in ("key", "line"):
                return ev
            if kind == "start":
                return ev
            if kind == "eof":
                return None
            if kind == "menu" and ev.get("action") == "help":
                self._send_help()
            # save/load are disabled at the title -> ignored

    def _command_loop(self):
        self._snapshot_now()
        while self.engine.running and not self.engine.restart:
            self.ch.send({"t": "await", "mode": "line", "menu": self._menu_flags(True)})
            ev = self.ch.get()
            kind = ev.get("kind")
            if kind == "line":
                self.engine.submit(ev.get("text", "")); self._snapshot_now()
            elif kind == "menu":
                self._menu(ev.get("action"), ev.get("arg")); self._snapshot_now()
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
            self._send_help()
        # "new" / "lang" are the client re-sending 'start' — handled by the loops above.

    def _send_menu_labels(self) -> None:
        lex = self.engine.lex
        self.ch.send({"t": "menu-labels", "labels": {
            "game": lex.ui("MENU_GAME"), "new": lex.ui("MENU_NEW_GAME"),
            "save": lex.ui("MENU_SAVE_GAME"), "load": lex.ui("MENU_LOAD_GAME"),
            "language": lex.ui("MENU_LANGUAGE"), "help": lex.ui("HELP_TITLE"),
        }, "lang": self.lang})
