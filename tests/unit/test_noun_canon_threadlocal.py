"""verb_events._NOUN_CANON must be per-thread, so concurrent web sessions in different
languages never read each other's scenery-noun alias map."""
import threading

from engine.verb_events import noun_is, set_noun_canon


def test_noun_canon_is_isolated_between_threads():
    results = {}
    b_installed = threading.Event()
    a_may_check = threading.Event()

    def session_a():                         # a Dutch session: no alias map
        set_noun_canon({})
        b_installed.wait(2)                  # let B install a DIFFERENT map first
        results["a"] = noun_is("kist", "KIST")     # Dutch prefix rule -> True
        a_may_check.set()

    def session_b():                         # an English-like session: its own alias map
        set_noun_canon({"GATE": "HEK"})
        b_installed.set()
        a_may_check.wait(2)
        results["b"] = noun_is("gate", "HEK")      # via its own alias -> True

    ta = threading.Thread(target=session_a)
    tb = threading.Thread(target=session_b)
    ta.start(); tb.start(); ta.join(3); tb.join(3)

    # With a shared module global, B's {"GATE":"HEK"} is still installed when A checks, so
    # A's noun_is("kist","KIST") wrongly returns False (KIST not in B's map).
    assert results["a"] is True, "session A read another thread's noun-canon map"
    assert results["b"] is True
