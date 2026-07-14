"""WebSocket server: one Session in a worker thread per connection.

Ordered outbound delivery is guaranteed by a single async sender task draining a
per-connection queue that the worker thread fills via loop.call_soon_threadsafe.
Run:  python -m frontends.web.server   (env DRACULA_WEB_HOST / DRACULA_WEB_PORT)
"""
from __future__ import annotations

import asyncio
import json
import os
import threading

import websockets

from .session import Session
from .webio import Channel


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
    async with websockets.serve(_serve_connection, host, port):
        print(f"Dracula web server listening on ws://{host}:{port}")
        await asyncio.Future()                       # run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
