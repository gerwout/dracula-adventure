"""In-process end-to-end: drive run_cli.main() through the winning walkthrough off world.json.

Exercises the REAL CLI entry point — argument parsing, language selection, and the play()
outer loop (intro / pause / clear / start), not just the engine — proving the console
frontend loads the self-contained data and reaches the win.

Why in-process (not a subprocess): the real ConsoleIO.pause() calls msvcrt.getwch(), which
reads the Windows console directly, NOT piped stdin, so a piped subprocess hangs forever at
the "press a key" title screen. We swap ConsoleIO for ScriptedIO — headless (IO.pause is a
no-op, read_key falls back to a line read, clear is a no-op) — so the exact same
run_cli.main() code path runs deterministically on every platform. ASCII-normalise the win
sentinel so any accented characters in the ending can't cause a spurious mismatch.

Scope: this drives the Dutch (nl) game — enough to prove the CLI frontend + world.json wiring.
The other win paths are already covered at the engine level and need no CLI duplication:
  - every translated language INCLUDING en: tests/unit/test_playthrough_i18n.py — note the
    player commands are TRANSLATED per language via render_walkthrough (the raw Dutch
    WALKTHROUGH only wins in nl), so a CLI en case would need that rendering machinery here.
  - the faithful/uncorrected text: tests/unit/test_full_playthrough.py::test_full_playthrough_faithful_also_wins.
"""
import re
import sys

import run_cli
from engine.game import new_game
from engine.io import ScriptedIO
from tests.unit.test_full_playthrough import WALKTHROUGH

CHAIN = " . ".join(WALKTHROUGH)


def _ascii(s: str) -> str:
    return re.sub(r"[^\x20-\x7e]", "", s)


def _expected_win_line() -> str:
    # The default (non-faithful) CLI path is explore=True, corrections=True, lang=nl.
    eng = new_game(ScriptedIO([]), explore=True, corrections=True, lang="nl")
    eng.submit(CHAIN)
    assert eng.won, "engine did not win the nl walkthrough"
    # The TROS win ending is message 281; use its longest line as the sentinel.
    return _ascii(max(eng.world.message_text(281).splitlines(), key=len))


def test_run_cli_nl_walkthrough_reaches_the_win(monkeypatch):
    sentinel = _expected_win_line()
    assert len(sentinel) >= 5, "win sentinel too short to match reliably"

    captured = []

    def fake_console():                  # ConsoleIO() takes no args; feed the whole game
        io = ScriptedIO([CHAIN])          # as one chained command, then EOF ("stop")
        captured.append(io)
        return io

    monkeypatch.setattr(run_cli, "ConsoleIO", fake_console)
    monkeypatch.setattr(sys, "argv", ["run_cli.py", "--lang", "nl"])

    run_cli.main()

    assert captured, "run_cli.main() did not construct the IO"
    assert sentinel in _ascii(captured[0].text), "CLI nl run did not reach the win ending"
