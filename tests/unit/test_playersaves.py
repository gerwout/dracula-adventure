from frontends.web.playersaves import PlayerSaveStore

PEP = b"test-pepper-0123456789"


def store(tmp_path):
    return PlayerSaveStore(tmp_path, PEP)


def test_save_load_round_trip(tmp_path):
    s = store(tmp_path)
    assert s.save("Emma", "123456", "Kasteel", {"room": 11}, "nl", "in het dorp") == "ok"
    assert s.load("Emma", "123456", "Kasteel") == {"room": 11}
    assert s.list_slots("Emma", "123456") == [("Kasteel", "in het dorp")]


def test_wrong_pin_is_isolated(tmp_path):
    s = store(tmp_path)
    s.save("Emma", "123456", "Kasteel", {"room": 11}, "nl")
    assert s.load("Emma", "999999", "Kasteel") is None
    assert s.list_slots("Emma", "999999") is None       # auth fail = no such identity
    assert s.list_slots("Emma", "123456") is not None


def test_name_casefolded_pin_and_slot_exact(tmp_path):
    s = store(tmp_path)
    s.save("Emma", "123456", "Kasteel", {"room": 11}, "nl")
    assert s.load("emma", "123456", "Kasteel") == {"room": 11}   # name case-insensitive
    assert s.load("Emma", "123456", "kasteel") == {"room": 11}   # slot normalized/trim only


def test_slot_cap_full_but_overwrite_ok(tmp_path):
    s = PlayerSaveStore(tmp_path, PEP, max_slots=2)
    assert s.save("E", "123456", "a", {"room": 1}, "nl") == "ok"
    assert s.save("E", "123456", "b", {"room": 2}, "nl") == "ok"
    assert s.save("E", "123456", "c", {"room": 3}, "nl") == "full"   # 3rd new slot
    assert s.save("E", "123456", "a", {"room": 9}, "nl") == "ok"     # overwrite existing
    assert s.load("E", "123456", "a") == {"room": 9}


def test_reap_deletes_only_expired_and_renews_on_save(tmp_path):
    s = store(tmp_path)
    s.save("E", "123456", "a", {"room": 1}, "nl", now=1000.0)
    assert s.reap(ttl=100.0, now=1050.0) == 0            # 50s old, kept
    assert s.reap(ttl=100.0, now=1200.0) == 1            # 200s old, expired
    # renewal: a re-save updates ts
    s.save("E", "123456", "a", {"room": 1}, "nl", now=2000.0)
    assert s.reap(ttl=100.0, now=2050.0) == 0


def test_corrupt_file_tolerated_and_reaped(tmp_path):
    s = store(tmp_path)
    (s.dir / "deadbeef.json").write_text("{ not json", encoding="utf-8")
    assert s.reap(ttl=100.0, now=1_000_000.0) == 1       # ts=0 -> expired -> removed


def test_hostile_name_stays_inside_dir(tmp_path):
    s = store(tmp_path)
    s.save("../../etc/passwd", "123456", "a", {"room": 1}, "nl")
    files = list(s.dir.glob("*.json"))
    assert len(files) == 1
    assert files[0].parent == s.dir                      # key is hex -> no traversal


# -- hardening: identity-count cap bounds players/ against disk exhaustion --------------

def test_reap_enforces_identity_count_cap(tmp_path):
    s = PlayerSaveStore(tmp_path, PEP, max_identities=3)
    now = 1_000_000.0
    for i in range(5):
        s.save(f"player{i}", "123456", "a", {"room": i}, "nl", now=now + i)
    assert s.reap(ttl=10**9, now=now + 100) == 2          # TTL deletes nothing; cap deletes 2
    assert len(list(s.dir.glob("*.json"))) == 3
    # the 2 oldest identities are gone; the 3 newest survive
    assert s.list_slots("player0", "123456") is None
    assert s.list_slots("player1", "123456") is None
    assert s.list_slots("player2", "123456") is not None
    assert s.list_slots("player3", "123456") is not None
    assert s.list_slots("player4", "123456") is not None


def test_amortized_cap_bounds_directory(tmp_path):
    s = PlayerSaveStore(tmp_path, PEP, max_identities=3, cap_check_every=2)
    for i in range(10):
        s.save(f"player{i}", "123456", "a", {"room": i}, "nl", now=1_000_000.0 + i)
    # bounded near max_identities (+ up to cap_check_every-1 slack), never the full 10 saved
    assert len(list(s.dir.glob("*.json"))) <= 3 + 1
