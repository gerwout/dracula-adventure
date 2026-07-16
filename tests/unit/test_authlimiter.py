from frontends.web.authlimiter import AuthLimiter


def test_locks_identity_after_five_failures_then_escalates():
    lim = AuthLimiter()
    t = 1000.0
    for _ in range(4):
        assert lim.locked_for("k", "ip", t) == 0.0
        lim.record_failure("k", "ip", t)
    assert lim.locked_for("k", "ip", t) == 0.0      # 4 failures: still allowed
    lim.record_failure("k", "ip", t)                 # 5th
    assert lim.locked_for("k", "ip", t) == 60.0      # first lock = 60s
    # after the lock, a 6th failure escalates to 120s
    lim.record_failure("k", "ip", t + 61)
    assert lim.locked_for("k", "ip", t + 61) == 120.0


def test_success_clears_identity_counter():
    lim = AuthLimiter()
    t = 1000.0
    for _ in range(5):
        lim.record_failure("k", "ip", t)
    assert lim.locked_for("k", "ip", t) > 0
    lim.record_success("k")
    assert lim.locked_for("k", "ip", t) == 0.0


def test_locked_attempt_is_not_counted_by_caller():
    # The caller checks locked_for FIRST and does not record on a locked attempt;
    # this test documents that record_failure is only called when locked_for==0.
    lim = AuthLimiter()
    t = 1000.0
    for _ in range(5):
        lim.record_failure("k", "ip", t)
    wait = lim.locked_for("k", "ip", t)
    assert wait == 60.0                              # still 60, not extended


def test_per_ip_throttle_across_names():
    lim = AuthLimiter(per_identity_max=999)          # isolate the IP axis
    t = 1000.0
    for i in range(20):
        assert lim.locked_for(f"k{i}", "ip", t) == 0.0
        lim.record_failure(f"k{i}", "ip", t)
    assert lim.locked_for("kX", "ip", t) > 0         # 20 hits in-window -> throttled
    assert lim.locked_for("kX", "other", t) == 0.0   # a different IP is unaffected
