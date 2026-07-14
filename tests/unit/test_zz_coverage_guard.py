"""Whole-suite message-coverage guard (runs last -- 'zz' sorts after every other test).

Asserts that EVERY reachable DRACULA.TXT message was shown by some test across the full
suite. The only messages allowed to be unshown are the DEAD_MESSAGES: message records
that no reachable code path in the ORIGINAL game ever prints (confirmed by reverse
engineering). This turns "all messages appear in a test" into an enforced guarantee --
if a future change stops a message from being exercised, this fails.

Skips when run in isolation (the recorder only has the full suite's output after a full
run); use `pytest tests/unit` (or the whole suite) to exercise it.
"""
import pytest

import msgcov
from engine.data.loader import load_file
from tools.translate_core import DEAD_MESSAGES   # RE-confirmed dead code (single source)


def test_every_reachable_message_is_shown_by_the_suite():
    world = load_file()
    covered, uncovered = msgcov.coverage(world)
    if len(covered) < 260:
        pytest.skip("coverage guard needs the whole suite's output "
                    "(run `pytest tests/unit`); saw only %d covered" % len(covered))
    regressed = sorted(set(uncovered) - DEAD_MESSAGES)
    assert not regressed, (
        "these messages are shown by NO test (coverage regression): "
        + ", ".join(f"msg:{m} {world.message_text(m)[:40]!r}" for m in regressed))
