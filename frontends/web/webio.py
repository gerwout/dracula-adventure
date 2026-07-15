"""Web frontend IO: bridge the synchronous engine to a per-connection message channel.

Everything here is per-connection — a Channel owns one inbound queue, and a WebIO /
WebSaveStore wrap exactly one Channel. Nothing is shared between sessions.
"""
from __future__ import annotations

import queue

from engine.io import IO


class Channel:
    """A per-connection pipe. `send` hands an outbound dict to the transport (thread-safe,
    non-blocking). Inbound client events are `put` by the transport and read (blocking) by
    the engine thread via `get`. `close` unblocks a waiting reader AND is *sticky*: every
    later `get` returns the EOF sentinel, so a nested read (e.g. a menu Load waiting for the
    client's reply) can never leave an outer loop blocked on a now-permanently-empty queue."""

    def __init__(self, send):
        self._send = send                       # callable(dict) -> None
        self._inbox: "queue.Queue[dict]" = queue.Queue()
        self._closed = False

    def send(self, msg: dict) -> None:
        self._send(msg)

    def put(self, msg: dict) -> None:
        self._inbox.put(msg)

    def get(self) -> dict:
        if self._closed:
            return {"kind": "eof"}
        ev = self._inbox.get()
        if ev.get("kind") == "eof":
            self._closed = True
        return ev

    def close(self) -> None:
        self._closed = True
        self._inbox.put({"kind": "eof"})


class WebIO(IO):
    """IO that speaks the JSON protocol over a Channel. Used for the engine's own
    reads (sub-prompts / the title keypress); the Session drives the top-level loop."""

    def __init__(self, channel: Channel):
        self.ch = channel

    def write(self, text: str) -> None:
        self.ch.send({"t": "out", "text": text})

    def clear(self) -> None:
        self.ch.send({"t": "clear"})

    def read_command(self) -> str:
        self.ch.send({"t": "await", "mode": "line"})
        while True:
            ev = self.ch.get()
            kind = ev.get("kind")
            if kind == "line":
                return ev.get("text", "")
            if kind == "eof":
                return "stop"
            # ignore keys / menu / loaded that arrive out of turn

    def read_key(self, keys=None) -> str:
        msg = {"t": "await", "mode": "key"}
        if keys:
            msg["keys"] = keys
        self.ch.send(msg)
        while True:
            ev = self.ch.get()
            kind = ev.get("kind")
            if kind == "key":
                return ev.get("ch", "")
            if kind == "line":
                text = ev.get("text", "")
                return text[:1] if text else ""
            if kind == "eof":
                return "stop"

    def pause(self) -> None:
        self.read_key()


class WebSaveStore:
    """SaveStore backed by the browser: save() ships the blob to the client (localStorage),
    load() requests it and blocks for the reply."""

    def __init__(self, channel: Channel):
        self.ch = channel

    def save(self, data: dict) -> None:
        self.ch.send({"t": "save", "data": data})

    def load(self):
        self.ch.send({"t": "load"})
        while True:
            ev = self.ch.get()
            kind = ev.get("kind")
            if kind == "loaded":
                return ev.get("data")           # dict or None
            if kind == "eof":
                return None
