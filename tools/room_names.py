"""Descriptive short names for the ~48 real rooms of Dracula Avontuur.

The original game has no explicit room names — each room is only known by its
first description line (``world.rooms[r].lines[0]``). For the translation tool we
want a concise human label per room, so a translator can see *where* a string
appears.

Two layers:

* ``ROOM_NAME_OVERRIDES`` — a curated label for every real room. These are the
  authoritative names (the heuristic below is only a fallback for rooms not in
  the dict, e.g. after a data change).
* ``room_name(world, r)`` — returns the override if present, otherwise derives a
  name heuristically from the first description line by grabbing the salient noun
  after an article ("in de/het/een <noun>", "op de …", "achter het …").

The names are intentionally kept in Dutch (the source language) so they still
match the original geography; a translator localises the *strings*, not these
internal location labels.
"""
from __future__ import annotations

import re

# Curated, human-friendly labels. Keys are room ids (loader indices).
ROOM_NAME_OVERRIDES: dict[int, str] = {
    0: "Eigen huis",
    1: "Slaapkamer",
    2: "Hal",
    3: "Zolder (huis)",
    4: "Kelder",
    5: "Zandtunnel",
    6: "Achter het huis",
    7: "Donker woud",
    8: "Donker woud",
    9: "Donker woud",
    10: "Donker woud",
    11: "Dorpsstraat",
    12: "Herberg",
    13: "Herberg (tafel)",
    14: "Zolder (herberg)",
    15: "Bos (open plek)",
    16: "Heuvel",
    17: "Donker woud (boom)",
    18: "Boomhut",
    19: "Bospad",
    20: "Kasteel (ingang)",
    21: "Kasteelhal",
    22: "Lange gang",
    23: "Kasteelslaapkamer",
    24: "Kasteelslaapkamer 2",
    25: "Balkon",
    26: "Smalle rand",
    27: "Eetkamer",
    28: "Torendak",
    29: "Kasteeltoren",
    30: "Wenteltrap (vertikaal)",
    31: "Wenteltrap",
    32: "Gewelf",
    33: "Spionageruimte",
    34: "Kruiskamer",
    35: "Schatkamer",
    36: "Binnenplaats/kerkhof",
    37: "Graftombe",
    38: "Doodskist",
    39: "Gegraven gat",
    40: "Lange gang (kelder)",
    41: "Nis (kijkgat)",
    42: "Nauwe hoge gang",
    43: "Gang (gat in grond)",
    44: "Gang (onbegaanbaar)",
    51: "Nauwe nis",
    52: "Ventilatieruimte",
    54: "Harnas",
}

# Words that are never a useful room name if they turn up right after an article.
_HEURISTIC_STOP = {
    "kleine", "grote", "lange", "nauwe", "hoge", "lage", "donkere", "vochtige",
    "immense", "immens", "smalle", "brede", "breed", "open", "zeer", "soort",
    "van", "het", "een", "de",
}

_ARTICLE_RE = re.compile(
    r"\b(?:in|op|achter|aan|voor|onder|bij|naar)\s+"
    r"(?:de|het|een|je|jouw|zijn)\s+([a-zA-Z]+)",
    re.IGNORECASE,
)


def _heuristic_name(first_line: str) -> str:
    """Best-effort room label from a first description line.

    Grabs the first meaningful noun after an article. Skips adjective-like stop
    words (so "een kleine hal" yields "Hal", not "Kleine"). Falls back to the
    first few words if nothing matches.
    """
    for m in _ARTICLE_RE.finditer(first_line):
        word = m.group(1)
        if word.lower() not in _HEURISTIC_STOP:
            return word.capitalize()
    # Fallback: first non-trivial word of the line.
    for word in re.findall(r"[a-zA-Z]{3,}", first_line):
        if word.lower() not in _HEURISTIC_STOP:
            return word.capitalize()
    return first_line.strip()[:20] or "?"


def room_name(world, r: int) -> str:
    """Return a concise descriptive name for room ``r``.

    Uses the curated override when available, else derives one from the room's
    first description line. Placeholder / empty rooms return "(ongebruikt)".
    """
    if r in ROOM_NAME_OVERRIDES:
        return ROOM_NAME_OVERRIDES[r]
    room = world.rooms.get(r)
    if room is None or room.is_placeholder or not room.lines:
        return "(ongebruikt)"
    return _heuristic_name(room.lines[0])
