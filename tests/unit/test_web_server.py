"""End-to-end over a real loopback WebSocket. Skipped unless `websockets` is installed
(it is a server-only dependency, not required by the rest of the suite)."""
import asyncio
import json

import pytest

websockets = pytest.importorskip("websockets")

from frontends.web.server import _serve_connection      # noqa: E402
from tests.unit.test_full_playthrough import WALKTHROUGH  # noqa: E402

CHAIN = " . ".join(WALKTHROUGH)


def test_real_socket_playthrough_reaches_win():
    async def scenario():
        server = await websockets.serve(_serve_connection, "127.0.0.1", 0)
        port = server.sockets[0].getsockname()[1]
        async with websockets.connect(f"ws://127.0.0.1:{port}") as ws:
            await ws.send(json.dumps({"kind": "start", "lang": "nl"}))
            await ws.send(json.dumps({"kind": "key", "ch": " "}))
            await ws.send(json.dumps({"kind": "line", "text": CHAIN}))
            out = []
            try:
                async with asyncio.timeout(25):
                    async for raw in ws:
                        m = json.loads(raw)
                        if m.get("t") == "out":
                            out.append(m["text"])
                            if "TROS" in "".join(out):     # the win ending (nl)
                                break
            finally:
                server.close()
                await server.wait_closed()
            assert "TROS" in "".join(out)

    asyncio.run(scenario())
