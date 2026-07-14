"""WebIO / WebSaveStore turn engine IO into channel messages and block for replies."""
from frontends.web.webio import Channel, WebIO, WebSaveStore


def make():
    sent = []
    return Channel(sent.append), sent


def test_write_and_clear_emit_messages():
    ch, sent = make()
    io = WebIO(ch)
    io.write("hallo")
    io.clear()
    assert {"t": "out", "text": "hallo"} in sent
    assert {"t": "clear"} in sent


def test_read_command_returns_line_and_announces_await():
    ch, sent = make()
    io = WebIO(ch)
    ch.put({"kind": "line", "text": "kijk"})
    assert io.read_command() == "kijk"
    assert any(m.get("t") == "await" and m.get("mode") == "line" for m in sent)


def test_read_key_returns_char_and_eof_becomes_stop():
    ch, sent = make()
    io = WebIO(ch)
    ch.put({"kind": "key", "ch": "J"})
    assert io.read_key() == "J"
    ch.close()
    assert io.read_command() == "stop"


def test_read_command_ignores_out_of_turn_events():
    ch, sent = make()
    io = WebIO(ch)
    ch.put({"kind": "menu", "action": "save"})     # ignored at a line prompt
    ch.put({"kind": "line", "text": "ga noord"})
    assert io.read_command() == "ga noord"


def test_savestore_round_trip():
    ch, sent = make()
    store = WebSaveStore(ch)
    store.save({"room": 7})
    assert {"t": "save", "data": {"room": 7}} in sent
    ch.put({"kind": "loaded", "data": {"room": 7}})
    assert store.load() == {"room": 7}
    assert any(m.get("t") == "load" for m in sent)


def test_savestore_load_returns_none_on_empty_slot():
    ch, sent = make()
    store = WebSaveStore(ch)
    ch.put({"kind": "loaded", "data": None})
    assert store.load() is None
