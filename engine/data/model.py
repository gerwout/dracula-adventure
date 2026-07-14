"""Structured world model reconstructed from DRACULA.TXT.

See docs/txt-format.md for the byte-level format this mirrors.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .lexicon import DEFAULT as _DEFAULT_LEXICON, Lexicon


def _fresh_lexicon() -> Lexicon:
    """Each World gets its own copy of the Dutch defaults so a translation can
    override entries without mutating the shared default."""
    return _DEFAULT_LEXICON.copy()

# Sentinel used in the exit table for "no exit in this direction".
NO_EXIT = 255

# Direction order of the 7-word exit vector (confirmed against map geometry).
# Index 0..6 = these directions.
DIRECTIONS = ["noord", "zuid", "oost", "west", "omhoog", "omlaag", "eruit"]

# "location" sentinel meaning an object is not currently placed in any room.
# The original DRACULA.EXE uses 99 for "consumed / removed from play" too.
LOC_NOWHERE = 99

# Runtime sentinel for an object's location == "held by the player". The EXE uses
# -1 (0xffff) for this; the engine uses 200 (a value no real room id reaches) so
# object locations stay non-negative. Single source of truth for game + verb_events.
CARRIED = 200


@dataclass
class Room:
    """A single room: its exit vector and (assembled) description lines."""

    id: int
    exits: list[int]          # 7 entries; NO_EXIT (255) means no exit
    lines: list[str]          # description, one entry per original screen line
    first_record: int         # 0-based DRACULA.TXT record of the first line

    @property
    def description(self) -> str:
        return "\n".join(self.lines)

    def exit_to(self, direction_index: int) -> int | None:
        """Destination room id for a direction index, or None if blocked."""
        v = self.exits[direction_index]
        return None if v == NO_EXIT else v

    @property
    def is_placeholder(self) -> bool:
        """True for the unused '...?...' room slots."""
        d = self.description.strip()
        return d == "" or d.strip(". ?") == ""


@dataclass
class GameObject:
    """An object/scenery/state-variant record from the object table."""

    id: int
    tokens: list[str]         # 4-char parser tokens (upper-case), e.g. ["LANT","BRAN","LAMP"]
    name: str                 # human-readable display name
    attribute: int            # attribute word (weight/flags — semantics TBD from EXE)
    location: int             # initial room id, or LOC_NOWHERE (99)
    raw_text: str             # original 76-byte text field (tokens + name), rstripped

    @property
    def display_name(self) -> str:
        """Name without the leading article-marker byte (see `article`)."""
        return self.name[1:] if self.name[:1] in ("@", "~") else self.name

    @property
    def article(self) -> str:
        """How the room describe lists this object, chosen by a leading marker byte
        in the name (verified from DRACULA.EXE object-lister 0x4f5e, which does
        LEFT$(name,1) and prints MID$(name,2)):
          '@' -> 'plural'   -> "Er zijn <name> hier."      (e.g. @scherven)
          '~' -> 'bare'     -> "<name>"  (a full state sentence, no article/suffix)
          else -> 'singular'-> "Er is een <name> hier."
        """
        m = self.name[:1]
        return "plural" if m == "@" else "bare" if m == "~" else "singular"

    @property
    def placed(self) -> bool:
        return self.location != LOC_NOWHERE

    @property
    def is_real(self) -> bool:
        """False for the unused all-zero object slots at the end of the table."""
        return bool(self.raw_text)


@dataclass
class World:
    """The full decoded game database."""

    rooms: dict[int, Room]
    messages: dict[int, list[str]]     # message id -> lines
    objects: dict[int, GameObject]
    header: list[int]                  # 5 section-boundary words
    raw: bytes = field(default=b"", repr=False)
    # Externalised UI strings / input tokens / answer letters (engine/data/lexicon.py).
    # Defaults to a fresh Dutch copy; engine/i18n.py overrides entries for a translation.
    lexicon: Lexicon = field(default_factory=_fresh_lexicon, repr=False)

    def message_text(self, mid: int) -> str:
        # A few messages (41,42,157,207) carry an embedded NUL byte where the
        # original DOS screen shows a blank cell (CP437 glyph 0x00). Render it as
        # a space so modern frontends match; the un-rendered NUL is preserved in
        # world.json / self.messages, and byte-level fidelity to the original is
        # checked by the guarded provenance test (tests/unit/test_world_json.py).
        return "\n".join(self.messages.get(mid, [])).replace("\x00", " ")

    def real_rooms(self) -> dict[int, Room]:
        return {rid: r for rid, r in self.rooms.items() if not r.is_placeholder}

    def objects_in(self, room_id: int) -> list[GameObject]:
        return [o for o in self.objects.values()
                if o.is_real and o.location == room_id]

    def real_objects(self) -> dict[int, GameObject]:
        return {oid: o for oid, o in self.objects.items() if o.is_real}

    def to_dict(self) -> dict:
        """Serialise to JSON-native primitives (UTF-8 strings; int ids as string keys).
        Excludes `raw` (pre-decode bytes) and `lexicon` (rebuilt fresh on load)."""
        return {
            "header": list(self.header),
            "rooms": {str(rid): {"exits": list(r.exits), "lines": list(r.lines),
                                 "first_record": r.first_record}
                      for rid, r in self.rooms.items()},
            "messages": {str(mid): list(lines) for mid, lines in self.messages.items()},
            "objects": {str(oid): {"tokens": list(o.tokens), "name": o.name,
                                   "attribute": o.attribute, "location": o.location,
                                   "raw_text": o.raw_text}
                        for oid, o in self.objects.items()},
        }

    @staticmethod
    def from_dict(d: dict) -> "World":
        """Reconstruct a World from to_dict() output (keys cast back to int; raw empty)."""
        rooms = {int(k): Room(id=int(k), exits=list(v["exits"]), lines=list(v["lines"]),
                              first_record=v["first_record"])
                 for k, v in d["rooms"].items()}
        messages = {int(k): list(v) for k, v in d["messages"].items()}
        objects = {int(k): GameObject(id=int(k), tokens=list(v["tokens"]), name=v["name"],
                                      attribute=v["attribute"], location=v["location"],
                                      raw_text=v["raw_text"])
                   for k, v in d["objects"].items()}
        return World(rooms=rooms, messages=messages, objects=objects,
                     header=list(d["header"]))
