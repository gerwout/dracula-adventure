from pathlib import Path
from frontends.web.sessionstore import SessionStore


def test_save_load_roundtrip(tmp_path):
    s = SessionStore(tmp_path)
    s.save("tok1", {"room": 5, "state": {"dde": 255}}, "nl")
    rec = s.load("tok1")
    assert rec["state"] == {"room": 5, "state": {"dde": 255}}
    assert rec["lang"] == "nl"
    assert isinstance(rec["ts"], (int, float))


def test_load_missing_or_corrupt_returns_none(tmp_path):
    s = SessionStore(tmp_path)
    assert s.load("nope") is None
    assert not s.exists("nope")
    (Path(tmp_path) / "bad.json").write_text("{not json", encoding="utf-8")
    assert s.load("bad") is None


def test_illegal_token_never_escapes_dir(tmp_path):
    s = SessionStore(tmp_path)
    # path-traversal-ish tokens must not read/write outside the directory
    assert s.load("../../etc/passwd") is None
    s.save("../evil", {"x": 1}, "nl")
    assert not (Path(tmp_path).parent / "evil.json").exists()


def test_reap_deletes_only_expired_and_caps_count(tmp_path):
    s = SessionStore(tmp_path)
    now = 1_000_000.0
    for i in range(5):
        s.save(f"t{i}", {"i": i}, "nl")
    # backdate t0,t1 beyond ttl by rewriting their ts
    for i in (0, 1):
        p = Path(tmp_path) / f"t{i}.json"
        import json
        d = json.loads(p.read_text()); d["ts"] = now - 10_000; p.write_text(json.dumps(d))
    deleted = s.reap(ttl=3600, max_files=50_000, now=now)
    assert deleted == 2
    assert not s.exists("t0") and s.exists("t2")
    # count cap: with 3 left, cap at 1 removes the 2 oldest by ts
    s.save("t2", {"i": 2}, "nl")  # refresh t2 ts newest
    removed = s.reap(ttl=10**9, max_files=1, now=now + 1)
    assert removed >= 2 and s.exists("t2")


def test_reap_tolerates_wrong_shape_json(tmp_path):
    s = SessionStore(tmp_path)
    now = 1_000_000.0
    (Path(tmp_path) / "arr.json").write_text("[]", encoding="utf-8")
    (Path(tmp_path) / "badts.json").write_text('{"ts": "x"}', encoding="utf-8")
    # must not raise, and both are treated as ts=0 -> expired -> removed
    deleted = s.reap(ttl=3600, max_files=50_000, now=now)
    assert deleted == 2
    assert not (Path(tmp_path) / "arr.json").exists()
    assert not (Path(tmp_path) / "badts.json").exists()


def test_load_returns_none_for_non_dict_json(tmp_path):
    s = SessionStore(tmp_path)
    (Path(tmp_path) / "arr.json").write_text("[]", encoding="utf-8")
    (Path(tmp_path) / "nul.json").write_text("null", encoding="utf-8")
    (Path(tmp_path) / "num.json").write_text("42", encoding="utf-8")
    (Path(tmp_path) / "str.json").write_text('"hello"', encoding="utf-8")
    assert s.load("arr") is None
    assert s.load("nul") is None
    assert s.load("num") is None
    assert s.load("str") is None


# -- hardening: amortized write-time cap bounds the dir between hourly reaps -------------

def test_write_time_cap_enforce_evicts_oldest(tmp_path):
    import os
    s = SessionStore(tmp_path, max_files=2, cap_check_every=1000)   # no auto-prune during setup
    for i in range(5):
        s.save(f"t{i}", {"room": i}, "nl")
        os.utime(Path(tmp_path) / f"t{i}.json", (1_000_000 + i, 1_000_000 + i))  # ascending mtime
    assert len(list(Path(tmp_path).glob("*.json"))) == 5           # not pruned yet
    s._enforce_count_cap()
    remaining = sorted(p.stem for p in Path(tmp_path).glob("*.json"))
    assert remaining == ["t3", "t4"]                               # the oldest three evicted


def test_save_triggers_amortized_cap(tmp_path):
    s = SessionStore(tmp_path, max_files=1, cap_check_every=1)      # prune on every save
    s.save("a", {"room": 0}, "nl")
    s.save("b", {"room": 0}, "nl")                                 # this save prunes down to 1
    assert len(list(Path(tmp_path).glob("*.json"))) <= 1


# -- optional `active` field: the named-save identity (key+slot), persisted alongside the
# per-turn snapshot so a cold resume can restore it and autosave re-engages --------------

def test_save_round_trips_active_field(tmp_path):
    s = SessionStore(tmp_path)
    s.save("tok1", {"room": 5}, "nl", {"key": "abc", "slot": "Kasteel"})
    rec = s.load("tok1")
    assert rec["active"] == {"key": "abc", "slot": "Kasteel"}


def test_save_without_active_loads_as_none(tmp_path):
    s = SessionStore(tmp_path)
    s.save("tok2", {"room": 5}, "nl")            # no `active` arg -> old-record shape
    rec = s.load("tok2")
    assert rec.get("active") is None
