from engine.io import ScriptedIO
from frontends.web.webio import Channel, WebIO


def test_read_key_accepts_and_ignores_keys_hint():
    io = ScriptedIO(["x"])
    assert io.read_key([{"label": "Ja", "ch": "J"}]) == "x"   # base ignores hint


def test_webio_forwards_keys_in_await():
    sent = []
    ch = Channel(lambda m: sent.append(m))
    io = WebIO(ch)
    ch.put({"kind": "key", "ch": "J"})
    io.read_key([{"label": "Ja", "ch": "J"}, {"label": "Nee", "ch": "N"}])
    awaits = [m for m in sent if m.get("t") == "await" and m.get("mode") == "key"]
    assert awaits and awaits[-1]["keys"] == [{"label": "Ja", "ch": "J"},
                                             {"label": "Nee", "ch": "N"}]
