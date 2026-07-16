import queue
from frontends.web.webio import Channel
from frontends.web.playersaves import PlayerSaveStore
from frontends.web.authlimiter import AuthLimiter
from frontends.web.namedsave import NamedWebSaveStore


def _driver(inbound):
    """A Channel whose get() yields queued client events; send() records outbound."""
    sent = []
    ch = Channel(lambda m: sent.append(m))
    for ev in inbound:
        ch.put(ev)
    return ch, sent


def test_save_writes_slot_and_reports_ok(tmp_path):
    ps = PlayerSaveStore(tmp_path, b"pep")
    ids = []
    ch, sent = _driver([{"kind": "save-submit", "name": "Emma", "pin": "123456", "slot": "Kasteel"}])
    store = NamedWebSaveStore(ch, ps, AuthLimiter(), "ip",
                              on_identity=lambda *a: ids.append(a),
                              hint_fn=lambda: "in het dorp", lang_fn=lambda: "nl")
    assert store.save({"room": 11}) is True
    assert ps.load("Emma", "123456", "Kasteel") == {"room": 11}
    assert ids == [("Emma", "123456", "Kasteel")]
    assert any(m.get("t") == "save-result" and m.get("status") == "ok" for m in sent)


def test_save_existing_slot_requires_confirm(tmp_path):
    ps = PlayerSaveStore(tmp_path, b"pep")
    ps.save("Emma", "123456", "Kasteel", {"room": 1}, "nl")
    ch, sent = _driver([
        {"kind": "save-submit", "name": "Emma", "pin": "123456", "slot": "Kasteel"},           # -> exists
        {"kind": "save-submit", "name": "Emma", "pin": "123456", "slot": "Kasteel", "confirm": True},
    ])
    store = NamedWebSaveStore(ch, ps, AuthLimiter(), "ip",
                              on_identity=lambda *a: None, hint_fn=lambda: "", lang_fn=lambda: "nl")
    assert store.save({"room": 2}) is True
    assert [m["status"] for m in sent if m.get("t") == "save-result"] == ["exists", "ok"]
    assert ps.load("Emma", "123456", "Kasteel") == {"room": 2}


def test_save_rejects_invalid_then_cancel(tmp_path):
    ps = PlayerSaveStore(tmp_path, b"pep")
    ch, sent = _driver([
        {"kind": "save-submit", "name": "Emma", "pin": "12", "slot": "x"},   # short PIN
        {"kind": "cancel"},
    ])
    store = NamedWebSaveStore(ch, ps, AuthLimiter(), "ip",
                              on_identity=lambda *a: None, hint_fn=lambda: "", lang_fn=lambda: "nl")
    assert store.save({"room": 1}) is False
    assert any(m.get("status") == "invalid" for m in sent if m.get("t") == "save-result")


def test_load_lists_then_returns_slot(tmp_path):
    ps = PlayerSaveStore(tmp_path, b"pep")
    ps.save("Emma", "123456", "Kasteel", {"room": 11}, "nl", "in het dorp")
    ch, sent = _driver([
        {"kind": "list-submit", "name": "Emma", "pin": "123456"},
        {"kind": "load-pick", "name": "Emma", "pin": "123456", "slot": "Kasteel"},
    ])
    store = NamedWebSaveStore(ch, ps, AuthLimiter(), "ip",
                              on_identity=lambda *a: None, hint_fn=lambda: "", lang_fn=lambda: "nl")
    assert store.load() == {"room": 11}
    slot_msgs = [m for m in sent if m.get("t") == "slots"]
    assert slot_msgs and slot_msgs[0]["slots"] == [{"name": "Kasteel", "hint": "in het dorp"}]


def test_load_auth_fail_records_and_locks(tmp_path):
    ps = PlayerSaveStore(tmp_path, b"pep")
    lim = AuthLimiter()
    ch, sent = _driver([{"kind": "list-submit", "name": "Nobody", "pin": "123456"},
                        {"kind": "cancel"}])
    store = NamedWebSaveStore(ch, ps, lim, "ip",
                              on_identity=lambda *a: None, hint_fn=lambda: "", lang_fn=lambda: "nl")
    assert store.load() is None
    assert any(m.get("status") == "auth-fail" for m in sent if m.get("t") == "load-result")
