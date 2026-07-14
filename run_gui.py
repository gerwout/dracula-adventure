"""Play Dracula in a desktop window (tkinter GUI).

Usage:
    python run_gui.py                 # pick a language on the startup screen, then play
    python run_gui.py --lang en       # start directly in English (skip the picker);
                                      #   --lang nl = Dutch
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from frontends.desktop_tk import main   # noqa: E402  (main handles --lang + the picker)


if __name__ == "__main__":
    main()
