"""SaveStore implementation for the web: drives the client name+PIN+slot dialog and
persists to a server-side PlayerSaveStore. Reused by engine.do_bewaar/do_laad, so
both the menu buttons and the typed BEWAAR/LAAD commands go through it. See spec §4-§5.
"""
from __future__ import annotations

import time

from . import savevalidate as v


class NamedWebSaveStore:
    def __init__(self, channel, player_store, limiter, ip,
                 on_identity, hint_fn, lang_fn):
        self.ch = channel
        self.ps = player_store
        self.limiter = limiter
        self.ip = ip
        self.on_identity = on_identity      # (name, pin, slot) -> None, on success
        self.hint_fn = hint_fn              # () -> str, current-room hint
        self.lang_fn = lang_fn              # () -> str, current language code

    # -- BEWAAR ------------------------------------------------------------- #
    def save(self, data: dict) -> bool:
        self.ch.send({"t": "save-dialog"})
        while True:
            ev = self.ch.get()
            kind = ev.get("kind")
            if kind in ("eof", "cancel"):
                return False
            if kind != "save-submit":
                continue
            name, pin, slot = ev.get("name", ""), ev.get("pin", ""), ev.get("slot", "")
            if not (v.valid_name(name) and v.valid_pin(pin) and v.valid_slot(slot)):
                self.ch.send({"t": "save-result", "status": "invalid"})
                continue
            if self.ps.has_slot(name, pin, slot) and not ev.get("confirm"):
                self.ch.send({"t": "save-result", "status": "exists"})
                continue
            status = self.ps.save(name, pin, slot, data, self.lang_fn(), self.hint_fn())
            if status == "full":
                self.ch.send({"t": "save-result", "status": "full"})
                continue
            self.on_identity(name, pin, slot)
            self.ch.send({"t": "save-result", "status": "ok", "slot": v.normalize_slot(slot)})
            return True

    # -- LAAD --------------------------------------------------------------- #
    def load(self) -> dict | None:
        self.ch.send({"t": "load-dialog"})
        while True:
            ev = self.ch.get()
            kind = ev.get("kind")
            if kind in ("eof", "cancel"):
                return None
            if kind == "list-submit":
                self._list(ev.get("name", ""), ev.get("pin", ""))
                continue
            if kind == "load-pick":
                state = self._pick(ev.get("name", ""), ev.get("pin", ""), ev.get("slot", ""))
                if state is not None:
                    return state
                continue

    def _list(self, name, pin) -> None:
        if not (v.valid_name(name) and v.valid_pin(pin)):
            self.ch.send({"t": "load-result", "status": "invalid"})
            return
        key = self.ps._key(name, pin)
        wait = self.limiter.locked_for(key, self.ip, time.time())
        if wait > 0:
            self.ch.send({"t": "load-result", "status": "locked", "secs": int(wait)})
            return
        slots = self.ps.list_slots(name, pin)
        if slots is None:
            self.limiter.record_failure(key, self.ip, time.time())
            self.ch.send({"t": "load-result", "status": "auth-fail"})
            return
        self.limiter.record_success(key)
        self.ch.send({"t": "slots", "slots": [{"name": s, "hint": h} for s, h in slots]})

    def _pick(self, name, pin, slot):
        if not (v.valid_name(name) and v.valid_pin(pin) and v.valid_slot(slot)):
            self.ch.send({"t": "load-result", "status": "invalid"})
            return None
        state = self.ps.load(name, pin, slot)
        if not isinstance(state, dict):
            self.ch.send({"t": "load-result", "status": "no-slot"})
            return None
        self.on_identity(name, pin, slot)
        self.ch.send({"t": "clear"})
        self.ch.send({"t": "screen", "kind": "game"})
        self.ch.send({"t": "load-result", "status": "ok"})
        return state
