"""Translation seam for Dracula Avontuur.

The game's original text is **Dutch** (language code ``nl``) and is loaded from
DRACULA.TXT by :mod:`engine.data.loader`. This module marks that Dutch text as the
source language and provides a documented, opt-in path to run the game in another
language, *without* changing default behaviour:

* :class:`Translator` holds a language code (default ``"nl"``) and optional
  per-string overrides for messages, room static text, and verb input tokens. In
  its default state (``lang == "nl"`` and no overrides) it is a no-op — the game
  stays byte-identical to the original.

* :func:`Translator.from_csv` loads a translation file exported by the GUI
  (``tools/translate_gui.py``) and picks a single target-language column.

* :func:`apply_translation` swaps a loaded :class:`~engine.data.model.World`'s
  message texts and room description lines in place with the translations, so all
  existing engine code (which calls ``world.message_text`` / reads ``room.lines``)
  transparently emits the translated strings.

Adding a language, end to end::

    python tools/translate_gui.py         # Export -> translate the "en" column -> Import -> Export
    # then, in code / a frontend:
    from engine.data.loader import load_file
    world = load_file(translator=Translator.from_csv("dracula_en.csv", "en"))

Row ids in the CSV are ``msg:<n>`` (message index), ``room:<n>`` (room id),
``obj:<n>`` (object display name), ``verb:<TOKEN>`` / ``dir:<TOKEN>`` (input words),
and the externalised lexicon
(engine/data/lexicon.py): ``ui:<KEY>`` (generic engine/frontend strings),
``answer:yes`` / ``answer:no`` (the J/N answer letters), ``secret:word`` (the room-31
password) and ``intro:<n>`` / ``intro:header`` (the title screen). See
tools/translate_core.py. Applying a translation is engine-wide: messages, room text,
parser tokens, UI strings and the J/N letters all switch together.
"""
from __future__ import annotations

import csv
from pathlib import Path

from .data.object_nouns import noun_token

SOURCE_LANG = "nl"
_I18N_DIR = Path(__file__).resolve().parent / "data" / "i18n"

# Each language names itself with the ui:LANGUAGE_NAME string ("Nederlands", "English",
# …) — its endonym. The source (nl) reads it from strings_nl.json; every other language
# reads it from its own bundled CSV. So the set of playable languages is DISCOVERED from
# the files, and adding a language is literally dropping a dracula_<code>.csv into
# engine/data/i18n/ (with its LANGUAGE_NAME translated) — no code change.


def _source_endonym() -> str:
    from .data.lexicon import load_data
    return load_data(SOURCE_LANG).get("ui", {}).get("LANGUAGE_NAME", SOURCE_LANG)


def _csv_endonym(path: "Path", code: str) -> str:
    """The endonym from a bundled CSV's ui:LANGUAGE_NAME row (its own language column),
    or the code itself if absent/unreadable."""
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("id") == "ui:LANGUAGE_NAME":
                    return row.get(code) or code
    except (OSError, ValueError):
        pass
    return code


def available_languages(i18n_dir: "str | Path | None" = None) -> dict[str, str]:
    """Discover the playable languages -> their endonyms: the Dutch source first, then
    every engine/data/i18n/dracula_<code>.csv found (sorted). Pass ``i18n_dir`` to scan a
    different directory (used in tests)."""
    d = Path(i18n_dir) if i18n_dir is not None else _I18N_DIR
    langs = {SOURCE_LANG: _source_endonym()}
    for path in sorted(d.glob("dracula_*.csv")):
        code = path.stem[len("dracula_"):]
        if code and code != SOURCE_LANG:
            langs.setdefault(code, _csv_endonym(path, code))
    return langs


# Discovered once at import (adding a language then needs a restart, not a code change).
AVAILABLE_LANGUAGES: dict[str, str] = available_languages()


def builtin_translator(lang: str) -> "Translator | None":
    """A :class:`Translator` for a bundled language, or ``None`` for the Dutch source
    (which needs no translation). Raises ``FileNotFoundError`` for an unknown language."""
    if lang == SOURCE_LANG:
        return None
    return Translator.from_csv(_I18N_DIR / f"dracula_{lang}.csv", lang)


class Translator:
    """Holds a target language and its per-string overrides (else falls back to nl).

    Overrides are keyed by the same ids the translation CSV uses:
      * ``messages``: ``{message_index: translated_text}``
      * ``rooms``:    ``{room_id: translated_description}``
      * ``verbs``:    ``{original_TOKEN: translated_token}``
    Empty translations are never stored, so a missing key always means "keep the
    Dutch original".
    """

    def __init__(self, lang: str = SOURCE_LANG):
        self.lang = lang
        self.messages: dict[int, str] = {}
        self.rooms: dict[int, str] = {}
        self.verbs: dict[str, str] = {}       # verb input TOKEN overrides
        self.dirs: dict[str, str] = {}        # direction input TOKEN overrides
        # Externalised lexicon overrides (engine/data/lexicon.py):
        self.ui: dict[str, str] = {}          # generic engine/frontend strings
        self.answers: dict[str, str] = {}     # 'yes'/'no' answer letters (J/N -> Y/N)
        self.secret: str = ""                 # the room-31 secret word
        self.intro: dict[int, str] = {}       # title-screen line index -> text
        self.header: str = ""                 # the serienummer header line
        self.objects: dict[int, str] = {}     # object display-name overrides
        self.object_nouns: dict[int, list[str]] = {}   # object input-noun overrides
        self.nouns: dict[str, list[str]] = {}          # scenery-noun words per canonical token

    # -- predicate ---------------------------------------------------------- #
    def is_default(self) -> bool:
        """True when this translator changes nothing (default Dutch behaviour)."""
        return self.lang == SOURCE_LANG and not (
            self.messages or self.rooms or self.verbs or self.dirs or self.ui
            or self.answers or self.secret or self.intro or self.header
            or self.objects or self.object_nouns or self.nouns)

    # -- lookups (with Dutch fallback) ------------------------------------- #
    def message(self, mid: int, fallback: str) -> str:
        return self.messages.get(mid, fallback)

    def room(self, rid: int, fallback: str) -> str:
        return self.rooms.get(rid, fallback)

    def verb(self, token: str, fallback: str) -> str:
        return self.verbs.get(token, fallback)

    # -- construction ------------------------------------------------------ #
    @classmethod
    def from_rows(cls, rows: list[dict], lang: str) -> "Translator":
        """Build a translator from exported rows, taking the ``lang`` column."""
        tr = cls(lang)
        for row in rows:
            rid = row.get("id", "")
            value = (row.get(lang) or "").strip("\n")
            if not value:
                continue
            kind, _, key = rid.partition(":")
            if kind == "msg":
                try:
                    tr.messages[int(key)] = value
                except ValueError:
                    pass
            elif kind == "room":
                try:
                    tr.rooms[int(key)] = value
                except ValueError:
                    pass
            elif kind == "verb":
                # `value` is the full word the player types (take); derive its parser
                # token (TAKE) the same way object nouns do -- first 4 chars, uppercased.
                tr.verbs[key] = noun_token(value)
            elif kind == "dir":
                tr.dirs[key] = noun_token(value)
            elif kind == "ui":
                tr.ui[key] = value
            elif kind == "answer":
                tr.answers[key] = value
            elif kind == "obj":
                try:
                    tr.objects[int(key)] = value
                except ValueError:
                    pass
            elif kind == "objnoun":
                try:
                    tr.object_nouns[int(key)] = [w.strip() for w in value.split(",")
                                                 if w.strip()]
                except ValueError:
                    pass
            elif kind == "noun":
                # Scenery/interaction nouns keyed by their canonical Dutch token.
                tr.nouns[key] = [w.strip() for w in value.split(",") if w.strip()]
            elif kind == "secret":
                tr.secret = value
            elif kind == "intro":
                if key == "header":
                    tr.header = value
                else:
                    try:
                        tr.intro[int(key)] = value
                    except ValueError:
                        pass
        return tr

    @classmethod
    def from_csv(cls, path: str | Path, lang: str) -> "Translator":
        """Load a GUI-exported CSV (utf-8-sig) and pick the ``lang`` column."""
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            rows = [dict(r) for r in csv.DictReader(f)]
        return cls.from_rows(rows, lang)

    # -- application ------------------------------------------------------- #
    def apply(self, world) -> None:
        """Swap ``world``'s message texts, room lines and lexicon entries with the
        translations. No-op when this translator is default (Dutch).

        Verb/direction token overrides go onto ``world.lexicon`` (verbs/dirs); the
        Engine rebuilds its parser tables from there, so the translated input words
        are accepted. The UI strings, answer letters (J/N -> Y/N), secret word and
        title screen are likewise overridden on the lexicon, which the engine reads
        through everywhere. Empty translations are skipped (Dutch original kept)."""
        if self.is_default():
            return
        for mid, text in self.messages.items():
            if mid in world.messages:
                world.messages[mid] = text.split("\n")
        for rid, text in self.rooms.items():
            if rid in world.rooms:
                world.rooms[rid].lines = text.split("\n")
        for oid, text in self.objects.items():
            obj = world.objects.get(oid)
            if obj is not None:
                # Preserve the article marker (@ plural / ~ bare) that the object lister
                # reads from the first char; translate only the visible name.
                marker = obj.name[:1] if obj.name[:1] in ("@", "~") else ""
                obj.name = marker + text
        for oid, words in self.object_nouns.items():
            obj = world.objects.get(oid)
            if obj is not None and words:
                # The player types the translated noun; the parser matches its first 4
                # chars, so derive the target-language tokens (garlic -> GARL).
                obj.tokens = [noun_token(w) for w in words]
        # Scenery-noun aliases: map each translated word's parser token back to its
        # canonical Dutch token (chest -> CHES -> KIST), so the engine's fixed Dutch
        # noun_is()/navigation checks accept the translated words.
        noun_canon: dict[str, str] = {}
        for canonical, words in self.nouns.items():
            for w in words:
                tok = noun_token(w)
                if tok:
                    noun_canon[tok] = canonical
        world.lexicon.apply_overrides(
            ui=self.ui, answers=self.answers, secret=self.secret,
            intro=self.intro, header=self.header,
            verbs=self.verbs, dirs=self.dirs, noun_canon=noun_canon)


def apply_translation(world, csv_path: str | Path, lang: str) -> Translator:
    """Convenience: load a translation CSV, apply it to ``world``, return the Translator."""
    tr = Translator.from_csv(csv_path, lang)
    tr.apply(world)
    return tr
