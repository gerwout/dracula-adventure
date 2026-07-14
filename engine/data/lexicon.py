"""The engine's externalised string lexicon.

Everything the player sees or types that is *not* in DRACULA.TXT — the generic
parser replies (``Ok``, `` : gepakt.``, ``Je draagt:`` …), the title screen, the
serial header, the tester/BUG logbook headers, the hidden secret word, and the
J/N answer letters — used to be hardcoded Dutch literals scattered across the
engine. They now live in :file:`strings_nl.json`, loaded here into a
:class:`Lexicon`.

Why this exists: so that **nothing is hardcoded** and the whole game can be
translated from one place. A :class:`Lexicon` hangs off the loaded
:class:`~engine.data.model.World` (``world.lexicon``); the engine reads every
such string through it, and :mod:`engine.i18n` can override any entry for another
language (e.g. the death prompt's 'no' letter ``J``/``N`` -> ``Y``/``N``). The
Dutch values remain the byte-for-byte defaults, so default play is unchanged.
"""
from __future__ import annotations

import json
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent


def load_data(lang: str = "nl") -> dict:
    """Read the raw strings dict for a language code (only ``nl`` ships as JSON)."""
    with open(_DATA_DIR / f"strings_{lang}.json", "r", encoding="utf-8") as f:
        return json.load(f)


class Lexicon:
    """Holds every externalised UI string / input token, with dict-backed access.

    Built from :func:`load_data`. All lookups fall back to ``""`` (never raise), so
    a partial translation degrades gracefully rather than crashing the engine.
    """

    def __init__(self, data: dict | None = None):
        data = data or {}
        self._ui: dict[str, str] = dict(data.get("ui", {}))
        self._answers: dict[str, str] = dict(data.get("answers", {}))
        self.secret: str = data.get("secret", "")
        self.intro: list[str] = list(data.get("intro", []))
        self.header: str = data.get("header", "")
        # Verb/direction token overrides for a translation: original TOKEN -> translated
        # TOKEN. Empty by default (the Dutch source tokens live in engine/parser.py); a
        # translation fills these so the parser accepts the translated input words.
        self.verbs: dict[str, str] = dict(data.get("verbs", {}))
        self.dirs: dict[str, str] = dict(data.get("dirs", {}))
        # Scenery/interaction-noun aliases for a translation: target-language 4-char
        # token -> canonical Dutch token (chest CHES -> KIST). Empty by default; a
        # translation fills it so the engine's noun_is()/named-navigation checks
        # (which compare against fixed Dutch tokens) accept the translated words too.
        self.noun_canon: dict[str, str] = dict(data.get("noun_canon", {}))

    # -- lookups ----------------------------------------------------------- #
    def ui(self, key: str) -> str:
        """A generic engine/frontend string by key (e.g. ``OK_TAKE``, ``INV_HEADER``)."""
        return self._ui.get(key, "")

    def answer(self, kind: str) -> str:
        """The localized answer letter — ``"yes"`` (Dutch ``J``) or ``"no"`` (``N``)."""
        return self._answers.get(kind, "")

    @property
    def bug_header(self) -> str:
        return self._ui.get("BUG_HEADER", "")

    # -- introspection (for the translation tool) -------------------------- #
    def all_ui(self) -> dict[str, str]:
        """A copy of every UI string keyed by name (for translate_core.collect_rows)."""
        return dict(self._ui)

    def all_answers(self) -> dict[str, str]:
        """A copy of the answer letters keyed by kind ('yes'/'no')."""
        return dict(self._answers)

    # -- overriding for a translation -------------------------------------- #
    def copy(self) -> "Lexicon":
        clone = Lexicon()
        clone._ui = dict(self._ui)
        clone._answers = dict(self._answers)
        clone.secret = self.secret
        clone.intro = list(self.intro)
        clone.header = self.header
        clone.verbs = dict(self.verbs)
        clone.dirs = dict(self.dirs)
        clone.noun_canon = dict(self.noun_canon)
        return clone

    def apply_overrides(self, *, ui=None, answers=None, secret=None,
                        intro=None, header=None, verbs=None, dirs=None,
                        noun_canon=None) -> None:
        """Merge non-empty translated values in place (empty = keep the Dutch original)."""
        for k, v in (ui or {}).items():
            if v:
                self._ui[k] = v
        for k, v in (answers or {}).items():
            if v:
                self._answers[k] = v
        if secret:
            self.secret = secret
        for idx, v in (intro or {}).items():
            if v and 0 <= idx < len(self.intro):
                self.intro[idx] = v
        if header:
            self.header = header
        for k, v in (verbs or {}).items():
            if v:
                self.verbs[k] = v
        for k, v in (dirs or {}).items():
            if v:
                self.dirs[k] = v
        for k, v in (noun_canon or {}).items():
            if v:
                self.noun_canon[k] = v


def default_lexicon() -> Lexicon:
    """A fresh Lexicon holding the Dutch defaults (each World gets its own copy)."""
    return Lexicon(load_data("nl"))


# The Dutch defaults, loaded once. `EXE` (engine/messages.py) mirrors DEFAULT._ui so
# that direct `EXE.OK`-style access stays byte-identical; the engine itself reads a
# per-World copy (world.lexicon) so a translation can override entries.
DEFAULT = default_lexicon()
