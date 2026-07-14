"""Play Dracula in the terminal (headless engine + console IO).

Usage:
    python run_cli.py                 # pick a language, then play (named-place nav on)
    python run_cli.py --lang en       # play in English (skip the prompt); --lang nl = Dutch
    python run_cli.py --faithful      # only verified behaviour (directional movement)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from engine.game import new_game            # noqa: E402
from engine.io import ConsoleIO             # noqa: E402
from engine.i18n import AVAILABLE_LANGUAGES  # noqa: E402


def choose_language(argv, io=None) -> str:
    """The language code to play in: from ``--lang <code>`` if given and valid, else a
    one-key menu — press a single number (1/2/…), no Enter. Defaults to the first
    registered language (Dutch, the original) on EOF."""
    for i, arg in enumerate(argv):
        code = None
        if arg == "--lang" and i + 1 < len(argv):
            code = argv[i + 1].lower()
        elif arg.startswith("--lang="):
            code = arg.split("=", 1)[1].lower()
        if code in AVAILABLE_LANGUAGES:
            return code

    codes = list(AVAILABLE_LANGUAGES)
    print("Choose a language / Kies een taal:")
    for n, c in enumerate(codes, 1):
        print(f"  {n}.  {AVAILABLE_LANGUAGES[c]}")
    print(f"(press 1-{len(codes)})")
    if io is None:
        io = ConsoleIO()
    while True:
        key = io.read_key()                 # one keypress, no Enter
        if not key or key == "stop":        # EOF -> the default language
            return codes[0]
        if key.isdigit() and 1 <= int(key) <= len(codes):
            return codes[int(key) - 1]
        # any other key: keep waiting for a valid number


def main():
    argv = sys.argv[1:]
    faithful = "--faithful" in argv
    io = ConsoleIO()
    lang = choose_language(argv, io)
    # --faithful = the true 1982 build: only verified navigation AND the original,
    # uncorrected spelling. The default is the modernised ("Gemoderniseerde") text.
    engine = new_game(io, explore=not faithful, corrections=not faithful, lang=lang)
    engine.play()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except Exception:
        # A double-clicked console build would otherwise vanish before the error can be
        # read. Show the traceback and wait so the player can see (and report) what broke.
        import traceback
        traceback.print_exc()
        try:
            input("\n[er ging iets mis — druk op Enter om af te sluiten]")
        except EOFError:
            pass
        raise SystemExit(1)
