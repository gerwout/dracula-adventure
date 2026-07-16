"""Deterministic tests for the resumable-session server (Host + Server).

Two behaviours are proven here:
  (a) a fresh `start` mints a token, sends {"t":"session", token}, and — once play has
      actually begun — a per-turn disk snapshot exists for that token;
  (b) a `resume` for a pre-seeded cold snapshot ({"room": 1}) redraws mid-game (real
      output present, and NO "D R A C U L A" title, i.e. the intro was skipped).

Determinism (Risk 1 in the task brief): handle() returns as soon as the FakeWS inbound is
exhausted, but the worker thread produces its output asynchronously — so a naive test can
detach() before that output was ever sent. To make this deterministic the FakeWS stays
"open": its async-iteration awaits an Event instead of ending immediately, and a poller
running on the event loop watches ws.sent for the expected output. Only once the condition
holds do we close the socket and let handle() return. No fixed sleep-and-hope; the bounded
timeout only guards against a genuine hang (which then fails the test rather than blocking).

pytest-asyncio is NOT a dependency of this repo (Risk 2), so each test drives its own loop
via asyncio.run inside a plain test function — no marker, no config needed.
"""
import asyncio
import json

import pytest

pytest.importorskip("websockets")   # server.py imports websockets at module import time

from frontends.web.server import Host, Server, WARM_GRACE      # noqa: E402
from frontends.web.sessionstore import SessionStore            # noqa: E402


class _Closed(Exception):
    pass


class FakeWS:
    """Minimal async websocket double.

    `recv` yields the handshake frame (handle() reads exactly one). Async-iteration yields
    any remaining inbound frames and then AWAITS `close()` before ending — that await is
    what holds the connection open long enough for the worker's output to arrive, instead
    of racing handle() to a premature StopAsyncIteration."""

    def __init__(self, inbound):
        self._inbound = [m if isinstance(m, str) else json.dumps(m) for m in inbound]
        self.sent = []
        self._closed = asyncio.Event()

    async def recv(self):
        if self._inbound:
            return self._inbound.pop(0)
        await self._closed.wait()
        raise _Closed()

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._inbound:
            return self._inbound.pop(0)
        await self._closed.wait()      # stay open until the test says we've seen enough
        raise StopAsyncIteration

    async def send(self, data):
        self.sent.append(json.loads(data))

    def close(self):
        self._closed.set()


async def _drive(srv, ws, condition, timeout=10.0):
    """Run srv.handle(ws) while polling `condition(ws)` on the loop. Close the socket the
    instant the condition holds (or after `timeout` as a hang guard), then let handle()
    finish and tear down any parked Host so its worker thread is released."""
    loop = asyncio.get_running_loop()
    task = asyncio.create_task(srv.handle(ws))
    deadline = loop.time() + timeout
    while loop.time() < deadline and not condition(ws):
        await asyncio.sleep(0.005)     # yield -> worker's call_soon_threadsafe + sender run
    ws.close()
    await task
    await asyncio.sleep(0)             # let the cancelled sender task settle cleanly
    for host in list(srv.parked.values()):
        if host.expire_handle:
            host.expire_handle.cancel()
        host.close()                  # signal EOF so the parked worker thread exits
    srv.parked.clear()
    return ws


def _session_token(ws):
    for m in ws.sent:
        if m.get("t") == "session" and m.get("token"):
            return m["token"]
    return None


def test_fresh_connection_mints_token_and_persists_snapshot(tmp_path):
    async def scenario():
        srv = Server(SessionStore(tmp_path))
        # start + a key to dismiss the title: play then actually begins and the per-turn
        # autosnapshot fires (the snapshot is written from inside the command loop).
        ws = FakeWS([{"kind": "start", "lang": "nl"}, {"kind": "key", "ch": " "}])

        def snapshot_written(w):
            tok = _session_token(w)
            return bool(tok) and srv.store.exists(tok)

        await _drive(srv, ws, snapshot_written)

        tok = _session_token(ws)
        assert tok, "server must mint a token and send {'t':'session', token}"
        assert srv.store.exists(tok), "a disk snapshot must exist for the minted token"

    asyncio.run(scenario())


def test_reconnect_resumes_from_disk(tmp_path):
    async def scenario():
        store = SessionStore(tmp_path)
        store.save("tokZ", {"room": 1}, "nl")          # pre-seed a cold snapshot
        srv = Server(store)
        ws = FakeWS([{"kind": "resume", "token": "tokZ", "needRedraw": True}])

        def redrew(w):
            return any(m.get("t") == "out" and m.get("text") for m in w.sent)

        await _drive(srv, ws, redrew)

        out = "".join(m.get("text", "") for m in ws.sent if m.get("t") == "out")
        assert out, "a cold resume must redraw the current room (real output)"
        assert "D R A C U L A" not in out, "resume must skip the intro/title screen"
        assert _session_token(ws) == "tokZ", "resume must keep the same token"

    asyncio.run(scenario())


async def _poll(condition, timeout=10.0):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline and not condition():
        await asyncio.sleep(0.005)
    return condition()


def test_warm_reattach_replays_from_buffer_without_disturbing_worker(tmp_path):
    async def scenario():
        srv = Server(SessionStore(tmp_path))

        # --- first connection: start a game and get the worker into the command loop ---
        ws1 = FakeWS([{"kind": "start", "lang": "nl"}, {"kind": "key", "ch": " "}])
        task1 = asyncio.create_task(srv.handle(ws1))
        awaiting_line = lambda w: any(
            m.get("t") == "await" and m.get("mode") == "line" for m in w.sent)
        assert await _poll(lambda: awaiting_line(ws1)), "game must reach the command loop"
        tok = _session_token(ws1)
        assert tok

        # disconnect WITHOUT closing the host -> handle() returns -> Host is parked warm
        ws1.close()
        await task1
        assert tok in srv.parked, "a live worker must be parked on disconnect"
        parked = srv.parked[tok]
        assert parked.worker.is_alive()
        assert parked.expire_handle is not None, "an expire timer must be armed while parked"

        # --- reconnect: warm re-attach replays the screen from the host-side buffer ---
        ws2 = FakeWS([{"kind": "resume", "token": tok, "needRedraw": True}])
        task2 = asyncio.create_task(srv.handle(ws2))
        replayed = lambda: (_session_token(ws2) == tok
                            and any(m.get("t") == "out" and m.get("text") for m in ws2.sent))
        assert await _poll(replayed), "warm re-attach must replay the buffered screen"
        # same live worker was reused (no cold rebuild) and its expire timer was cancelled
        assert parked.worker.is_alive()

        ws2.close()
        await task2
        await asyncio.sleep(0)

        out2 = "".join(m.get("text", "") for m in ws2.sent if m.get("t") == "out")
        assert out2 and "D R A C U L A" not in out2, "replay is mid-game, not the title"
        # a warm re-attach ends by replaying the last await (client knows it's their turn)
        assert any(m.get("t") == "await" and m.get("mode") == "line" for m in ws2.sent)

        # cleanup: release the (re-)parked worker thread
        for host in list(srv.parked.values()):
            if host.expire_handle:
                host.expire_handle.cancel()
            host.close()
        srv.parked.clear()

    asyncio.run(scenario())


def test_warm_reattach_replays_actual_screen_kind_not_hardcoded_game(tmp_path):
    # Regression: Host.attach()'s redraw path used to hardcode {"t":"screen","kind":"game"}
    # regardless of what screen the client was actually parked on. A client that reloads
    # while on the title screen and warm-re-attaches must get "title" back, not "game"
    # (which loses the title's white-space:pre / title-fit CSS and can misrender).
    # Driven directly against Host (no live worker needed): feed a screen hint through
    # _on_msg, then attach with replay+redraw and inspect what got queued for the client.
    async def scenario():
        store = SessionStore(tmp_path)
        loop = asyncio.get_running_loop()
        host = Host(loop, "tokTitle", store, resume_state=None, resume_lang="nl")
        host._on_msg({"t": "screen", "kind": "title"})

        ws = FakeWS([])
        host.attach(ws, replay=True, redraw=True)

        def screen_sent(w):
            return any(m.get("t") == "screen" for m in w.sent)

        assert await _poll(lambda: screen_sent(ws)), "attach() must queue a screen replay"
        host.detach()

        kinds = [m.get("kind") for m in ws.sent if m.get("t") == "screen"]
        assert "title" in kinds, "warm replay must use the recorded screen kind"
        assert "game" not in kinds, "warm replay must NOT hardcode 'game' over a title screen"

    asyncio.run(scenario())


def test_stateless_snapshot_does_not_soft_lock_falls_through_to_fresh(tmp_path):
    # Regression: a resumable-looking record on disk with no real `state` (e.g. an
    # interrupted/partial snapshot write) used to still satisfy `rec is not None`, building
    # a Host around resume_state=None -> the client would get stuck instead of a playable
    # game. It must instead be treated as unresolvable and fall through to a fresh start.
    async def scenario():
        store = SessionStore(tmp_path)
        store.save("tokStale", None, "nl")     # a snapshot record with NO real state
        srv = Server(store)
        ws = FakeWS([{"kind": "resume", "token": "tokStale", "needRedraw": True},
                     {"kind": "key", "ch": " "}])

        def snapshot_written(w):
            tok = _session_token(w)
            return bool(tok) and srv.store.exists(tok)

        await _drive(srv, ws, snapshot_written)

        tok = _session_token(ws)
        assert tok, "server must still mint a token and send {'t':'session', token}"
        assert tok != "tokStale", "a stateless snapshot must not be resumed as-is"
        assert srv.store.exists(tok), "the fresh session must persist its own snapshot"

    asyncio.run(scenario())


def test_warm_grace_constant_is_sane():
    # A guard so the grace window can't silently drift to 0/negative.
    assert WARM_GRACE > 0


def test_named_save_reaper_sweeps_players(tmp_path):
    from frontends.web.playersaves import PlayerSaveStore
    from frontends.web.authlimiter import AuthLimiter
    from frontends.web.sessionstore import SessionStore
    ps = PlayerSaveStore(tmp_path, b"pep")
    ps.save("E", "123456", "a", {"room": 1}, "nl", now=1000.0)
    srv = Server(SessionStore(tmp_path), player_store=ps, limiter=AuthLimiter())
    # reap with a tiny TTL and a far-future now -> the identity file is removed
    n = ps.reap(ttl=1.0, now=1_000_000.0)
    assert n == 1
    assert srv.player_store is ps and srv.limiter is not None


def test_reap_once_sweeps_expired_snapshot_and_identity(tmp_path):
    from frontends.web.server import Server, RESUME_TTL, MAX_SNAPSHOTS
    from frontends.web.sessionstore import SessionStore
    from frontends.web.playersaves import PlayerSaveStore
    from frontends.web.authlimiter import AuthLimiter
    import time

    store = SessionStore(tmp_path)
    store.save("tok", {"room": 1}, "nl")           # token snapshot, ts ~ now

    ps = PlayerSaveStore(tmp_path, b"pep")
    ps.save("E", "123456", "a", {"room": 1}, "nl")  # identity, ts ~ now

    srv = Server(store, player_store=ps, limiter=AuthLimiter())

    n = srv._reap_once(now=time.time() + RESUME_TTL + 10)
    assert n >= 2, "both the stale snapshot and the stale identity must be reaped"
    assert ps.list_slots("E", "123456") is None, "the identity file must be gone"

    # a fresh reap (now == now) removes nothing: nothing is older than TTL yet
    store.save("tok2", {"room": 1}, "nl")
    ps.save("E2", "654321", "a", {"room": 1}, "nl")
    assert srv._reap_once(now=time.time()) == 0


def test_client_ip_prefers_xff_then_remote_then_default(tmp_path):
    import types
    from frontends.web.server import Server
    from frontends.web.sessionstore import SessionStore

    srv = Server(SessionStore(tmp_path))

    ws_xff = types.SimpleNamespace(
        request=types.SimpleNamespace(headers={"X-Forwarded-For": "1.2.3.4, 5.6.7.8"}),
        remote_address=("9.9.9.9", 1234),
    )
    assert srv._client_ip(ws_xff) == "1.2.3.4"

    ws_remote = types.SimpleNamespace(
        request=types.SimpleNamespace(headers={}),
        remote_address=("9.9.9.9", 1234),
    )
    assert srv._client_ip(ws_remote) == "9.9.9.9"

    ws_bare = object()
    assert srv._client_ip(ws_bare) == "?"
