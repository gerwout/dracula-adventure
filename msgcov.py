"""Shared message-emission recorder + coverage logic for the coverage-guard test.

conftest.py tees every ScriptedIO write into EMITTED; tests/unit/test_zz_coverage_guard
then asserts that every reachable DRACULA.TXT message was shown by *some* test across
the full suite. Kept in its own module (not conftest) so the recorder is a single
shared instance regardless of how pytest imports conftest.
"""
import re

EMITTED: list[str] = []


def recorded_output() -> str:
    return "".join(EMITTED)


def _signature(text: str) -> str:
    """A distinctive static substring for a message (its longest placeholder-free chunk)."""
    best = ""
    for line in text.split("\n"):
        for seg in re.split(r"\{[^}]*\}", line):     # drop runtime {name}/{word}/{noun}
            seg = seg.strip()
            if len(seg) > len(best):
                best = seg
    return best


def coverage(world) -> tuple[list[int], list[int]]:
    """(covered, uncovered) message ids: every non-empty message vs the recorded output."""
    agg = recorded_output()
    covered, uncovered = [], []
    for mid in range(300):
        text = world.message_text(mid)
        if not text.strip():
            continue
        sig = _signature(text)
        (covered if len(sig) >= 6 and sig in agg else uncovered).append(mid)
    return covered, uncovered
