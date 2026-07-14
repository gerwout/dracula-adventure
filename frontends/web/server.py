"""Web server: serves the static game page AND the per-connection WebSocket, so a
single process is a complete, playable web app.

Each WebSocket connection runs one Session in a worker thread; ordered outbound delivery
is guaranteed by a single async sender task draining a per-connection queue that the
worker thread fills via loop.call_soon_threadsafe. A normal HTTP GET (any path other than
/ws) returns the static index.html.

Run:  python -m frontends.web.server    then open http://127.0.0.1:8765/
      (env DRACULA_WEB_HOST / DRACULA_WEB_PORT override the host/port)
"""
from __future__ import annotations

import asyncio
import json
import os
import threading
from pathlib import Path

import websockets
from websockets.asyncio.server import serve
from websockets.datastructures import Headers
from websockets.http11 import Response

from .session import Session
from .webio import Channel

_STATIC_INDEX = Path(__file__).resolve().parent / "static" / "index.html"


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


async def _serve_connection(ws):
    loop = asyncio.get_running_loop()
    outbox: "asyncio.Queue[dict]" = asyncio.Queue()

    def send(msg: dict) -> None:                     # engine thread -> loop (thread-safe)
        loop.call_soon_threadsafe(outbox.put_nowait, msg)

    channel = Channel(send)
    session = Session(channel)
    worker = threading.Thread(target=session.run, name="dracula-session", daemon=True)
    worker.start()

    async def sender():
        while True:
            msg = await outbox.get()
            await ws.send(json.dumps(msg))

    send_task = asyncio.create_task(sender())
    try:
        async for raw in ws:
            try:
                channel.put(json.loads(raw))
            except (ValueError, TypeError):
                pass                                 # ignore malformed frames
    except websockets.ConnectionClosed:
        pass
    finally:
        channel.close()                              # unblock the worker (-> EOF/"stop")
        send_task.cancel()
        await loop.run_in_executor(None, worker.join)


async def main() -> None:
    host = os.environ.get("DRACULA_WEB_HOST", "127.0.0.1")
    port = int(os.environ.get("DRACULA_WEB_PORT", "8765"))
    async with serve(_serve_connection, host, port, process_request=_process_request):
        print(f"Dracula web server on http://{host}:{port}/  (game page + /ws WebSocket)")
        await asyncio.Future()                       # run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
