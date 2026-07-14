"""Abstract IO boundary between the engine and any frontend.

The engine never touches stdin/stdout/GUI directly — it talks to an IO object.
This keeps the engine pure and lets the same logic drive a CLI, a tkinter
window, or (later) a web frontend.
"""
from __future__ import annotations

import abc
import sys


class IO(abc.ABC):
    @abc.abstractmethod
    def write(self, text: str) -> None:
        """Emit text to the player (no implicit newline)."""

    def writeln(self, text: str = "") -> None:
        self.write(text + "\n")

    @abc.abstractmethod
    def read_command(self) -> str:
        """Block for one line of player input (without trailing newline)."""

    def read_key(self) -> str:
        """Read a single keypress — ANY key, no Enter needed (used for the title
        screen and the J/N quit prompt). Default: fall back to a full line read so
        scripted/headless play still works."""
        return self.read_command()

    def clear(self) -> None:
        """Optional: clear the screen (faithful frontends implement this)."""

    def pause(self) -> None:
        """Optional: wait for a keypress ('Druk een toets om te beginnen'). No-op by
        default so scripted/headless play does not block; interactive frontends wait."""


class ConsoleIO(IO):
    """Simple stdin/stdout backend for headless play and tests. All I/O is UTF-8."""

    def __init__(self) -> None:
        # Force UTF-8 on the terminal so the decoded game content (accents, box glyphs)
        # renders identically on any platform, regardless of the console's code page.
        for stream in (sys.stdin, sys.stdout):
            reconfigure = getattr(stream, "reconfigure", None)
            if reconfigure is not None:
                try:
                    reconfigure(encoding="utf-8")
                except (ValueError, OSError):
                    pass

    def write(self, text: str) -> None:
        print(text, end="")

    def read_command(self) -> str:
        try:
            return input()
        except EOFError:
            return "stop"

    def read_key(self) -> str:
        """One raw keypress, no Enter required (Windows msvcrt / POSIX termios)."""
        try:
            import msvcrt
        except ImportError:
            msvcrt = None
        if msvcrt is not None:
            try:
                return msvcrt.getwch()
            except Exception:
                return self.read_command()
        try:
            import termios
            import tty
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                return sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
        except Exception:
            return self.read_command()

    def pause(self) -> None:
        # Continue on ANY key, not just Enter.
        self.read_key()

    def clear(self) -> None:
        # Clear the terminal (as the original does after the title screen).
        import os
        os.system("cls" if os.name == "nt" else "clear")


class ScriptedIO(IO):
    """Feeds a fixed list of commands; captures all output. For tests/diffing."""

    def __init__(self, commands: list[str]):
        self._commands = list(commands)
        self.output: list[str] = []

    def write(self, text: str) -> None:
        self.output.append(text)

    def read_command(self) -> str:
        if self._commands:
            return self._commands.pop(0)
        return "stop"

    @property
    def text(self) -> str:
        return "".join(self.output)
