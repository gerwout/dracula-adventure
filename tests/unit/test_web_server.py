"""End-to-end over a real loopback: the server serves BOTH the static page (on /) and
the WebSocket (on /ws). Skipped unless `websockets` is installed (a server-only
dependency, not required by the rest of the suite)."""
import asyncio
import json
import urllib.request

import pytest

websockets = pytest.importorskip("websockets")
from websockets.asyncio.server import serve                # noqa: E402
from websockets.asyncio.client import connect              # noqa: E402

from frontends.web.server import _serve_connection, _process_request   # noqa: E402
from tests.unit.test_full_playthrough import WALKTHROUGH    # noqa: E402

CHAIN = " . ".join(WALKTHROUGH)


def test_server_serves_page_and_plays_to_win():
    async def scenario():
        server = await serve(_serve_connection, "127.0.0.1", 0,
                             process_request=_process_request)
        port = server.sockets[0].getsockname()[1]
        loop = asyncio.get_running_loop()
        try:
            # 1. the static game page is served on / (fetched in a thread so the event
            #    loop stays free to answer the request)
            html = await loop.run_in_executor(
                None,
                lambda: urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=5)
                .read().decode("utf-8"))
            assert "<!doctype html>" in html.lower() and 'id="out"' in html

            # 2. the WebSocket at /ws plays a full game to the Dutch win ("TROS")
            async with connect(f"ws://127.0.0.1:{port}/ws") as ws:
                await ws.send(json.dumps({"kind": "start", "lang": "nl"}))
                await ws.send(json.dumps({"kind": "key", "ch": " "}))
                await ws.send(json.dumps({"kind": "line", "text": CHAIN}))
                out = []
                async with asyncio.timeout(25):
                    async for raw in ws:
                        m = json.loads(raw)
                        if m.get("t") == "out":
                            out.append(m["text"])
                            if "TROS" in "".join(out):
                                break
                assert "TROS" in "".join(out)
        finally:
            server.close()
            await server.wait_closed()

    asyncio.run(scenario())
