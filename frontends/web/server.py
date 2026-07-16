"""Web server: static game page + per-connection WebSocket with resumable sessions.

A Host owns one Session (worker thread + engine + channel) and whichever socket is
attached now. On disconnect the Host is parked for WARM_GRACE seconds so a reconnect
re-attaches to the still-live worker (replaying the current screen from a host-side
buffer). After the grace window the worker is torn down; the per-turn disk snapshot
(SessionStore) still allows a cold resume for RESUME_TTL. An hourly reaper enforces the
TTL + a file cap."""
from __future__ import annotations

import asyncio
import json
import os
import secrets
import threading
import time
from pathlib import Path

import websockets
from websockets.asyncio.server import serve
from websockets.datastructures import Headers
from websockets.http11 import Response

from .authlimiter import AuthLimiter
from .playersaves import PlayerSaveStore, load_or_create_pepper
from .session import Session
from .sessionstore import SessionStore
from .webio import Channel

_STATIC_INDEX = Path(__file__).resolve().parent / "static" / "index.html"

WARM_GRACE = 90.0
MAX_WARM = 200
RESUME_TTL = 3 * 24 * 3600
MAX_SNAPSHOTS = 50_000
REAP_INTERVAL = 3600.0
# Client->server frames are tiny (a command line, a key, a small save blob); cap them well
# below the websockets 1 MB default so a peer can't force large allocations.
MAX_MESSAGE_SIZE = 64 * 1024


def _allowed_origins():
    """The WebSocket Origin allow-list from ``DRACULA_WEB_ORIGINS`` (comma-separated), or
    ``None`` (no Origin check) when unset — so local/dev play still works. Production sets
    it to the site's own origins, which blocks cross-site WebSocket use of the endpoint."""
    raw = os.environ.get("DRACULA_WEB_ORIGINS", "").strip()
    if not raw:
        return None
    return [o.strip() for o in raw.split(",") if o.strip()]


def _process_request(connection, request):
    """Serve the game page for ordinary HTTP GETs; let /ws upgrade to a WebSocket."""
    if request.path.split("?", 1)[0] == "/ws":
        return None                                  # proceed with the WebSocket handshake
    body = _STATIC_INDEX.read_bytes()
    headers = Headers()
    headers["Content-Type"] = "text/html; charset=utf-8"
    headers["Content-Length"] = str(len(body))
    headers["Cache-Control"] = "no-cache"
    return Response(200, "OK", headers, body)


class Host:
    """Owns one Session (worker thread + Channel) and, at most, one attached socket.

    Thread boundary: the worker thread only ever reaches the loop through the thread-safe
    Channel (inbound) and `_emit` -> loop.call_soon_threadsafe (outbound). Everything else
    on this object (outbox, sender_task, ws, expire_handle, the replay buffer) is touched
    solely on the asyncio loop thread."""

    def __init__(self, loop, token, store, *, resume_state, resume_lang,
                 player_store=None, limiter=None, ip=""):
        self.loop = loop
        self.token = token
        self.store = store
        self.ws = None
        self.outbox = None
        self.sender_task = None
        self.expire_handle = None
        self._last_langs = None
        self._last_menu_labels = None
        self._last_await = None
        self._last_screen = None
        self._screen: list[str] = []
        self.channel = Channel(self._emit)
        self.session = Session(self.channel, token=token, snapshotter=self._snapshot,
                               resume_state=resume_state, resume_lang=resume_lang,
                               player_store=player_store, limiter=limiter, ip=ip)
        self.worker = threading.Thread(target=self.session.run,
                                       name=f"dracula-{token[:8]}", daemon=True)

    # worker thread -> loop
    def _emit(self, msg):
        self.loop.call_soon_threadsafe(self._on_msg, msg)

    def _on_msg(self, msg):
        # Runs on the loop thread. Keep the host-side replay buffer current (even while
        # parked, so a warm re-attach can redraw), then forward to the live socket if any.
        t = msg.get("t")
        if t == "langs":
            self._last_langs = msg
        elif t == "menu-labels":
            self._last_menu_labels = msg
        elif t == "await":
            self._last_await = msg
        elif t == "screen":
            self._last_screen = msg
        elif t == "clear":
            self._screen = []
        elif t == "out":
            self._screen.append(msg)          # store the whole message so replay keeps styling (the cmd echo)
        if self.outbox is not None:
            self.outbox.put_nowait(msg)

    def _snapshot(self, state, lang):
        self.store.save(self.token, state, lang)

    def start(self):
        self.worker.start()

    def attach(self, ws, *, replay: bool, redraw: bool):
        self.ws = ws
        self.outbox = asyncio.Queue()
        self.sender_task = asyncio.create_task(self._sender(ws, self.outbox))
        self.outbox.put_nowait({"t": "session", "token": self.token})
        if replay:
            # Warm re-attach: rebuild the client from the host-side buffer without
            # disturbing the still-running worker.
            if self._last_langs:
                self.outbox.put_nowait(self._last_langs)
            if self._last_menu_labels:
                self.outbox.put_nowait(self._last_menu_labels)
            if redraw:
                self.outbox.put_nowait({"t": "clear"})
                self.outbox.put_nowait(self._last_screen or {"t": "screen", "kind": "game"})
                for m in self._screen:
                    self.outbox.put_nowait(m)
            if self._last_await:
                self.outbox.put_nowait(self._last_await)

    async def _sender(self, ws, outbox):
        try:
            while True:
                msg = await outbox.get()
                await ws.send(json.dumps(msg))
        except (websockets.ConnectionClosed, asyncio.CancelledError):
            pass
        except Exception:
            pass

    def detach(self):
        if self.sender_task:
            self.sender_task.cancel()
        self.sender_task = None
        self.outbox = None
        self.ws = None

    def feed(self, msg):
        self.channel.put(msg)

    def close(self):
        self.channel.close()


class Server:
    def __init__(self, store: SessionStore, player_store=None, limiter=None):
        self.store = store
        self.player_store = player_store
        self.limiter = limiter
        self.parked: dict[str, Host] = {}
        self.live: set[Host] = set()          # hosts with a currently-attached socket = "players online"

    def _broadcast_players(self):
        # Push the current live player count to every attached client. Loop-thread only
        # (all callers run on the loop), so touching self.live and the outboxes is safe.
        msg = {"t": "players", "count": len(self.live)}
        for h in self.live:
            if h.outbox is not None:
                h.outbox.put_nowait(msg)

    async def handle(self, ws):
        loop = asyncio.get_running_loop()
        ip = "?"
        try:
            xff = ws.request.headers.get("X-Forwarded-For")
            ip = xff.split(",")[0].strip() if xff else ws.remote_address[0]
        except Exception:
            pass
        try:
            raw = await ws.recv()
        except Exception:
            return
        try:
            first = json.loads(raw)
        except (ValueError, TypeError):
            first = {}
        kind = first.get("kind")
        token = first.get("token") if isinstance(first.get("token"), str) else None
        redraw = bool(first.get("needRedraw"))
        host = None

        if kind == "resume" and token and token in self.parked:
            # Warm re-attach: the worker is still alive; cancel its expire timer and replay.
            host = self.parked.pop(token)
            if host.expire_handle:
                host.expire_handle.cancel()
                host.expire_handle = None
            host.attach(ws, replay=True, redraw=redraw)
        elif kind == "resume" and token and self.store.exists(token):
            # Cold resume: rebuild a fresh Host from the disk snapshot; the Session redraws.
            rec = self.store.load(token)
            if rec is not None and rec.get("state") is not None:
                host = Host(loop, token, self.store,
                            resume_state=rec.get("state"), resume_lang=rec.get("lang", "nl"),
                            player_store=self.player_store, limiter=self.limiter, ip=ip)
                host.attach(ws, replay=False, redraw=True)
                host.start()
        if host is None:
            # Fresh game: mint a new opaque token and drive the worker with a synthetic start.
            token = secrets.token_urlsafe(24)
            lang = first.get("lang") if isinstance(first.get("lang"), str) else "nl"
            host = Host(loop, token, self.store, resume_state=None, resume_lang=lang,
                        player_store=self.player_store, limiter=self.limiter, ip=ip)
            host.attach(ws, replay=False, redraw=False)
            host.start()
            host.feed({"kind": "start", "lang": lang})

        self.live.add(host)                   # now attached -> counts as a player
        self._broadcast_players()

        try:
            async for raw in ws:
                try:
                    m = json.loads(raw)
                except (ValueError, TypeError):
                    continue
                if m.get("kind") == "ping":          # answered here, NOT fed to the worker
                    if host.outbox is not None:
                        host.outbox.put_nowait({"t": "pong"})
                    continue
                host.feed(m)
        except Exception:
            pass
        finally:
            self._on_disconnect(loop, host)

    def _on_disconnect(self, loop, host):
        self.live.discard(host)               # no longer attached -> drop from the player count
        self._broadcast_players()
        host.detach()
        if host.worker.is_alive() and len(self.parked) < MAX_WARM:
            def expire():
                self.parked.pop(host.token, None)
                host.close()
            host.expire_handle = loop.call_later(WARM_GRACE, expire)
            self.parked[host.token] = host
        else:
            host.close()

    async def reaper(self):
        while True:
            await asyncio.sleep(REAP_INTERVAL)
            try:
                n = self.store.reap(RESUME_TTL, MAX_SNAPSHOTS, time.time())
                if self.player_store is not None:
                    n += self.player_store.reap(RESUME_TTL, time.time())
                if n:
                    print(f"[dracula] reaped {n} stale snapshot(s)/identity(ies)")
            except Exception:
                pass


async def main() -> None:
    host = os.environ.get("DRACULA_WEB_HOST", "127.0.0.1")
    port = int(os.environ.get("DRACULA_WEB_PORT", "8765"))
    state_dir = os.environ.get("DRACULA_WEB_STATE_DIR", str(Path(".web-sessions")))
    srv_store = SessionStore(state_dir, max_files=MAX_SNAPSHOTS)
    pepper = load_or_create_pepper(state_dir)
    player_store = PlayerSaveStore(state_dir, pepper)
    srv = Server(srv_store, player_store=player_store, limiter=AuthLimiter())
    async with serve(srv.handle, host, port, process_request=_process_request,
                     origins=_allowed_origins(), max_size=MAX_MESSAGE_SIZE,
                     ping_interval=20, ping_timeout=20):
        print(f"Dracula web server on http://{host}:{port}/  (state: {state_dir}; "
              f"origin-check: {'on' if _allowed_origins() else 'OFF (set DRACULA_WEB_ORIGINS)'})")
        reaper_task = asyncio.create_task(srv.reaper())   # kept referenced (no GC of task)
        try:
            await asyncio.Future()                        # run forever
        finally:
            reaper_task.cancel()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
