"""Ensure the project root is importable as `engine` during tests, and tee every game
message into the message-coverage recorder (see msgcov.py + test_zz_coverage_guard)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import msgcov                          # noqa: E402  (shared emission recorder)
from engine.io import ScriptedIO       # noqa: E402

_orig_scripted_write = ScriptedIO.write


def _tee_write(self, text):
    msgcov.EMITTED.append(text)
    return _orig_scripted_write(self, text)


ScriptedIO.write = _tee_write
