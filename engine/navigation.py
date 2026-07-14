"""Reconstructed named-place navigation (BETREED HUIS / GA HERBERG / ...).

IMPORTANT — this is a RECONSTRUCTION, not verified against the original.

The game lets you enter named places ("als er bv een huis staat, dan kan je
BETREED HUIS of GA HUIS proberen" — from the in-game rules). Those transitions
live in the compiled-BASIC special-event code, which is not statically
recoverable, and the live oracle is currently read-only (can't be driven — see
docs/STATUS.md). So we infer the entries from the data:

  * A room X that is *not* directionally reachable from room Y, but has an exit
    back to Y, is treated as a place you can enter from Y by naming it.
  * The names accepted are the salient nouns in X's own first description line
    (matched by the same 4-char prefix rule as the parser).

This recovers the obvious cases (GA HERBERG, GA KASTEEL, GA ZOLDER, ...) but is
heuristic: it cannot know puzzle gates (locked doors, required items) or the
exact wording, so it is exposed as an opt-in "explore mode", never the faithful
default. When the oracle becomes drivable, replace this with observed transitions.
"""
from __future__ import annotations

import re

from .data.model import NO_EXIT

_STOP = {
    "bent", "staat", "zit", "kruipt", "loopt", "hier", "deze", "naar", "voor",
    "achter", "onder", "boven", "waar", "kunt", "kans", "moeite", "veel", "zeer",
    "erg", "wordt", "loopt", "maar", "het", "een", "van", "met", "aan", "door",
    "over", "langs", "tussen", "onder", "meer", "kleine", "grote", "lange",
    "nauwe", "vochtige", "donkere", "immens", "immense", "open", "gedeelte",
}


def _place_words(first_line: str) -> list[str]:
    words = re.findall(r"[a-zA-Z]{3,}", first_line.lower())
    return [w for w in words if w not in _STOP]


def build_named_entries(world) -> dict[tuple[int, str], int]:
    """Map (from_room, 4-char place key) -> destination room. First hit wins."""
    entries: dict[tuple[int, str], int] = {}
    for x, rx in world.rooms.items():
        if rx.is_placeholder:
            continue
        direct_from_x = {d for d in rx.exits if d != NO_EXIT}
        for y in direct_from_x:
            ry = world.rooms.get(y)
            if ry is None or ry.is_placeholder:
                continue
            if x in {d for d in ry.exits if d != NO_EXIT}:
                continue  # already directly reachable from y
            for word in _place_words(rx.lines[0]):
                key = word[:4].upper()
                entries.setdefault((y, key), x)
    return entries


def resolve_named_place(entries, from_room: int, noun: str | None):
    if not noun:
        return None
    return entries.get((from_room, noun[:4].upper()))


# Verified-from-disassembly named-place navigation (GA/BETRE/KRUIP/LOOP/KLIM/VOLG
# <plaats>). Recovered STATICALLY from DRACULA.EXE's `ga` handler (0xe3e) by
# msbasic_il.boolidiom (the QuickBASIC AND/OR-mask resolver); see
# docs/named-navigation.{md,json}. These are FAITHFUL and always active (not the
# explore-mode heuristic). Each (guard_room, 4-char NOUN) maps to (dest, guard),
# where `guard` is None or a "flag<op>value" state condition ('==' / '!=') that must
# hold for the move — otherwise the transition doesn't fire (the game shows a
# door-closed / blocked reply, not yet wired). Nouns match by 4-char prefix.
VERIFIED_NAMED: dict[tuple[int, str], tuple[int, str | None]] = {
    (0, "SLAA"): (1, None), (0, "DEUR"): (11, None), (0, "HAL"): (2, None),
    (0, "RAAM"): (6, "e3c==0"),
    (2, "RUIM"): (0, None), (2, "UITG"): (0, None),
    (3, "LADD"): (0, None),
    (4, "LUIK"): (1, None),
    (5, "GANG"): (4, None),
    (6, "RAAM"): (0, "e3c==0"),
    (11, "LINK"): (0, None), (11, "HUIS"): (0, None), (11, "HERB"): (12, None),
    (12, "DEUR"): (11, None), (12, "ZITT"): (13, None),
    (13, "STAA"): (12, None),
    (14, "ZOLD"): (12, None), (14, "TRAP"): (12, None),
    (17, "BOOM"): (18, None),
    (19, "KAST"): (20, None), (19, "PAD"): (20, None),
    (20, "KAST"): (21, "dee==1"), (20, "DEUR"): (21, "dee==1"),
    (21, "DEUR"): (20, "dee==1"), (21, "TRAP"): (22, None),
    (22, "SLAA"): (24, "e46!=0"), (22, "DEUR"): (24, "e46!=0"),
    (23, "SLAA"): (40, None), (23, "DEUR"): (40, None),
    (24, "SLAA"): (22, "e46!=0"), (24, "DEUR"): (22, "e46!=0"),
    (27, "DEUR"): (21, None),
    (29, "RAAM"): (28, None),
    (30, "GAT"): (33, "e40==1"), (30, "LADD"): (33, "e40!=0"),
    (31, "SESA"): (34, "e48!=0"), (31, "DEUR"): (34, "e48!=0"),
    (32, "BINN"): (36, None), (32, "KERK"): (36, None), (32, "POOR"): (36, None),
    (32, "TRAP"): (37, "e44==1"), (32, "HEK"): (37, "e44==1"),
    (33, "GAT"): (30, None),
    (37, "TRAP"): (32, "e44==1"), (37, "HEK"): (32, "e44==1"),
    (39, "STEE"): (37, "e42==1"), (39, "GAT"): (37, "e42==1"),
    (40, "SLAA"): (23, None), (40, "DEUR"): (23, None),
}

# The bespoke "the door/gate is shut" line printed when a VERIFIED_NAMED guard fails,
# instead of the generic "Daar kan je niet heen." (unseen-message audit A1). Keyed by
# the same (room, 4-char NOUN); world.messages index. EXE offsets: 13@0x14c6 (castle
# outer door), 15@0x1598 / 14@0x155a (room-30 gat/ladder), 235@0x10aa/0x1335 (window),
# 257@0x18ce/0x1921 (bedroom-2 door), 268@0x19b5 (sesam door).
VERIFIED_NAMED_BLOCKED: dict[tuple[int, str], int] = {
    (20, "KAST"): 13, (20, "DEUR"): 13, (21, "DEUR"): 13,
    (30, "GAT"): 15, (30, "LADD"): 14,
    (0, "RAAM"): 235, (6, "RAAM"): 235,
    (22, "SLAA"): 257, (22, "DEUR"): 257, (24, "SLAA"): 257, (24, "DEUR"): 257,
    (31, "SESA"): 268, (31, "DEUR"): 268,
}


def blocked_message(from_room: int, noun: str | None, state: dict | None = None):
    """world.messages index of the closed-door line for a VERIFIED_NAMED transition
    whose flag guard currently FAILS (else None). Lets the caller print the specific
    reply instead of the generic cant_go when a named move is gated shut."""
    if not noun:
        return None
    from .verb_events import canon_token
    key = (from_room, canon_token(noun))
    entry = VERIFIED_NAMED.get(key)
    if entry is None:
        return None
    _dest, guard = entry
    if _guard_ok(guard, state or {}):
        return None                       # the guard holds -> not blocked
    return VERIFIED_NAMED_BLOCKED.get(key)


# Default flag values for guard evaluation when the caller passes no state
# (the Engine always passes its full self.state; this is a safe fallback).
_FLAG_INIT = {"dee": 1, "df0": 1, "dde": 255, "e3c": 0, "e40": 0, "e42": 0,
              "e44": 0, "e46": 0, "e48": 0}


def _guard_ok(guard: str | None, state: dict) -> bool:
    """Evaluate a 'flag<op>value' guard against the engine's integer flag state."""
    if not guard:
        return True
    import re
    m = re.fullmatch(r"(\w+)(==|!=)(-?\d+)", guard)
    if not m:
        return False
    key, op, val = m.group(1), m.group(2), int(m.group(3))
    cur = state.get(key, _FLAG_INIT.get(key, 0))
    return cur == val if op == "==" else cur != val


def resolve_verified(from_room: int, noun: str | None, state: dict | None = None):
    """Target room for a verified named-place transition, honouring its state guard.

    Matches noun.upper()[:4] against VERIFIED_NAMED for `from_room`; returns the
    destination room when the (optional) flag guard holds, else None (no transition
    here / guard not satisfied) so the caller can fall through.
    """
    if not noun:
        return None
    from .verb_events import canon_token
    return resolve_verified_token(from_room, canon_token(noun), state)


def resolve_verified_token(from_room: int, token: str, state: dict | None = None):
    """Like :func:`resolve_verified` but for an ALREADY-canonical Dutch place token, for
    callers that hold it directly (e.g. the STA handler's "STAA") rather than a typed,
    possibly-translated word that still needs canonicalising."""
    entry = VERIFIED_NAMED.get((from_room, token))
    if entry is None:
        return None
    dest, guard = entry
    return dest if _guard_ok(guard, state or {}) else None


# Stub destination for the GA-BRON else branch (tower not yet viewed). The EXE
# random-teleports via a runtime-DIM'd QuickBASIC array at DGROUP 0x101c whose static
# file image overlaps the verb-string constant pool (BETRE/KRUIP/LOOP/...), so the
# 'lost' room set is heap-allocated at runtime and is NOT statically recoverable.
# We land in a donker-woud room pending DOS-oracle confirmation (see uncertainties).
_BRON_LOST_STUB = 7


def ga_special(eng, noun: str | None) -> bool:
    """Movement specials that a plain VERIFIED_NAMED row cannot express — they emit a
    per-noun failure message and/or toggle bidirectionally, so resolve_verified (which
    returns dest-only and cannot print) is not enough. Verified against DRACULA.EXE.

    Returns True when the command was fully handled here (a message was printed and/or
    the player moved + redescribed), so the caller must stop; False to fall through to
    the normal named/exit resolution.

    (a) Room-0 ceiling climb — the GA-handler room-0 section + the 0x229c climb
        special. GA GAT/LADD with the ladder placed ([0xe3e]!=0) climbs to room 3;
        without it, GAT prints msg 11 ('...het gat zit te hoog', EXE rec 12 @0x10bc)
        and LADD prints msg 34 ('Welke ladder bedoel je ?', EXE rec 35 @0x229c).

    (c) Balcony rope descent — dispatch @0x13ae + special 0x3ad5. GA TOUW in rooms
        25/26 toggles 25<->26 when the rope is tied to the balcony (obj12 @ room 25);
        otherwise it prints msg 139 ('Welk touw ?', EXE rec 140).
    """
    # Imported here to avoid a module-load cycle (verb_events imports no navigation).
    from .verb_events import (pr, noun_is, DOODSKIST_OPEN, slaap,
                              KIST_LUIK_DICHT, KIST_LUIK_OPEN)

    room = eng.room

    # GA BED / GA SLAAP -> the SLAAP handler. EXE ga-noun dispatch 0x1277/0x1298 routes
    # both nouns to 0x392a (SLAAP), which itself gates on room 1. SS-905: ga bed -> msg 124.
    # slaap() reads only eng.room and flags (never cmd), so no Command is needed.
    if noun_is(noun, "BED") or noun_is(noun, "SLAP"):
        slaap(eng, None)
        return True

    # Grave-stone crossing (EXE 0x1690): GA STEE/GAT at room 39 with the stone rotated
    # (e42==1) crosses into the graftombe (37) but prints msg 16 and does NOT redescribe
    # (EXE jmp 0x261, not the post-move describe). At room 37, GA STEE/GAT -> msg 17
    # (the stone has closed behind you); no move. These print a message / suppress the
    # redescribe, so they cannot be plain VERIFIED_NAMED rows.
    if noun_is(noun, "STEE") or noun_is(noun, "GAT"):
        if room == 39 and eng.state.get("e42", 0) == 1:
            eng.room = 37
            pr(eng, 16)                            # "De steen ... slaat met een slag dicht"
            return True
        if room == 37:
            pr(eng, 17)                            # "De steen is weer op zijn plaats geschoven."
            return True

    # GA/KLIM BOOM in the forest rooms 7-10 -> the tree is too slippery (EXE 0x1377:
    # room>6 AND room<11). Room 17's real boomhut climb is a VERIFIED_NAMED row.
    if noun_is(noun, "BOOM") and 7 <= room <= 10:
        pr(eng, 12)
        return True

    # GA RAAM in the bedroom (room 1) -> the window is too small to climb through (0x17be).
    if noun_is(noun, "RAAM") and room == 1:
        pr(eng, 203)
        return True

    # (g) Doodskist slide / climb-in — GA/KRUIP KIST when the OPENED doodskist (obj38,
    # loc-var [0xca6]) sits in the current room. EXE ga-handler branches A/B (0x1a87 /
    # 0x1ac0), both guarded on noun=='KIST'(0x154c) AND room==[0xca6]:
    #   * room == 26 (the hillside ledge): SLIDE (branch B 0x1ac0). The coffin object
    #     relocates to the village ([0xca6]=0xb @0x1af0), the slide line messages[279]
    #     prints (K=0x118), and the player rides inside ([0xe2e]=0x26 @0x1aff). The
    #     schatkist (if carried) is untouched and rides along — end_of_turn Block D then
    #     declares the win once GA UIT drops you into room 11.
    #   * room != 26: CLIMB-IN (branch A 0x1a87). The player enters the coffin interior
    #     ([0xe2e]=0x26 @0x1ab7); no object move, no message. Reversible via GA UIT
    #     (game.do_ga room-38 exit intercept). Not a plain VERIFIED_NAMED row: a dynamic
    #     obj-location guard plus a message-printing / object-moving side effect.
    if noun_is(noun, "KIST"):
        if eng.obj_loc.get(DOODSKIST_OPEN) == room:
            if room == 26:
                eng.obj_loc[DOODSKIST_OPEN] = 11   # 0x1af0: the kist slides to the village
                pr(eng, 279)                       # 0x1af6: "De kist begint te glijden..."
            eng.room = 38                          # 0x1ab7 / 0x1aff: inside the coffin
            eng.describe_room()
            return True
        pr(eng, 18)                                # 0x1b08: no ridable coffin here
        return True

    # (f) Follow Dracula in the endgame chase — VOLG/GA DRACULA (or GA MAN). EXE
    # ga-handler DRAC/MAN block @0x192a: dx=([0xde0]==[0xe2e]); (noun==DRAC|MAN)&dx;
    # if set -> mov [0xe2e],[0xdde]; jmp 0x2f5 (room = Dracula's room [0xdde], then the
    # ordinary post-move redescribe). No message, no flag writes, no object moves. This
    # is a global/computed transition (dynamic source guard de0==room, computed dest
    # [0xdde]) so it cannot be a VERIFIED_NAMED row. Nouns 'DRAC'(0x152c) and 'MAN'
    # (0x1534) both match by prefix. de0/dde default to 255 (EXE init [0xde0]/[0xdde]=
    # 0xff) so the guard never fires until the patrol sets de0 to a real room.
    if (noun_is(noun, "DRAC") or noun_is(noun, "MAN")) and \
            eng.state.get("de0", 255) == room:
        eng.room = eng.state.get("dde", 255)
        eng.describe_room()
        return True

    # (g) Room-1 bedroom hatch descent — GA LUIK in the slaapkamer drops to the kelder
    # (room 4). EXE 0x39b0: if the hatch is not yet revealed ([0xe86]==0) -> msg 127
    # "Welk luik bedoel je ?"; else set [0xe2e]=4 and redescribe (jmp 0x2f5). The hatch is
    # revealed by SLAAP + BEKIJK BED (e96 -> e86); room 4 is reachable ONLY through here on
    # the faithful path, so this gates the whole kelder -> dig -> castle endgame.
    if room == 1 and noun_is(noun, "LUIK"):
        if eng.state.get("e86", 0) == 0:
            pr(eng, 127)
            return True
        eng.room = 4
        eng.describe_room()
        return True

    # GA LUIK away from the bedroom -> the tower-chest luik handler (EXE 0x3f22): at the
    # OPENED tower luik (obj23) descend to slaapkamer 2 (room 24); at the still-closed
    # luik (obj22) -> msg 168 'muurvast'; no luik present -> msg 169 'Wat voor luik ?'.
    if noun_is(noun, "LUIK"):
        if eng.obj_loc.get(KIST_LUIK_OPEN) == room:
            eng.room = 24
            eng.describe_room()
            return True
        if eng.obj_loc.get(KIST_LUIK_DICHT) == room:
            pr(eng, 168)
            return True
        pr(eng, 169)
        return True

    # (b) Innkeeper zolder — GA/KLIM ZOLDER|TRAP up from the herberg (room 12 -> 14).
    # EXE special handler 0x2b17 (reached from the GA room-12 block 0x11b7->0x11d8, so
    # room==12 and the ZOLD/TRAP noun are already established). Guarded on the
    # conversation flag [0xe6e] (must be revealed) and the anger counter [0xe84] (the
    # waard blocks you while angry). Not a plain VERIFIED_NAMED row because it prints
    # per-state failure messages. Descending 14->12 is the plain VERIFIED_NAMED entry.
    if room == 12 and (noun_is(noun, "ZOLD") or noun_is(noun, "TRAP")):
        if eng.state.get("e6e", 0) == 0:
            pr(eng, 60)                                # hint: ask the waard (0x2b21)
            return True
        if eng.state.get("e84", 0) > 0:
            pr(eng, 61)                                # blocked: he comes at you (0x2b34)
            return True
        eng.room = 14                                  # 0x2b3d: climb to the zolder
        eng.describe_room()
        return True

    # (e) Forest path to the waterbron — GA BRON from the dorpsstraat (room 11).
    # EXE dispatch: ga room-11 block 0x113a -> noun BRON (@0x148c) -> jmp 0x3974.
    # Handler 0x3974: cmp [0xe6c],1
    #   je 0x397e  -> mov [0xe2e],0xf (room 15); jmp 0x2f5 (describe, NO message) —
    #                 room 15's own text mentions the bron to the east.
    #   else 0x3987 -> RND-index array @0x101c -> mov [0xe2e],ax; mov [0xe34],0x7f
    #                 (msg 127 -> messages[126] "Je raakt helemaal de weg kwijt...");
    #                 call 0x5564; jmp 0x305 (describe the random room).
    # The e6c latch is set to 1 by describing room 28 (glibberige torendak) in
    # room_events #5, reached via GA RAAM from the kasteeltoren (room 29). From room 15
    # the plain OOST exit -> room 16 (the GOOI MUNT / VUL FLES puzzle room). Not a plain
    # VERIFIED_NAMED row because the else branch prints a message and teleports.
    if room == 11 and noun_is(noun, "BRON"):
        if eng.state.get("e6c", 0) == 1:
            eng.room = 15                              # 0x397e: reach the open bos
            eng.describe_room()                        # jmp 0x2f5 (no message)
            return True
        pr(eng, 126)                                   # 0x39a4: "...weg kwijt..."
        eng.room = _BRON_LOST_STUB                     # 0x39a1 (destination deferred)
        eng.describe_room()                            # jmp 0x305
        return True

    # (a) Room-0 ceiling climb (GA GAT / GA LADD).
    if room == 0 and (noun_is(noun, "GAT") or noun_is(noun, "LADD")):
        if eng.state.get("e3e", 0) == 0:
            pr(eng, 11 if noun_is(noun, "GAT") else 34)   # gat te hoog / welke ladder
            return True
        eng.room = 3
        eng.describe_room()
        return True

    # (c) Balcony rope descent (GA TOUW in rooms 25/26). The faithful gate is obj12's
    # location (the rope tied to the balcony), set to room 25 by HANG TOUW.
    if room in (25, 26) and noun_is(noun, "TOUW"):
        if eng.obj_loc.get(12) != 25:
            pr(eng, 139)                                  # 'Welk touw ?'
            return True
        eng.room = 26 if room == 25 else 25
        eng.describe_room()
        return True

    # (d) Fire-cross inside the harnas (GA VUUR while in the armour, room 54). Verified
    # DRACULA.EXE movement handler: Branch A 0x19be (harnas 34->35, world[277]) and
    # Branch B 0x1a0c (harnas 35->34, world[278]). Only the harnas OBJECT location
    # [0xca2] toggles between the kruiskamer (34) and schatkamer (35) side of the fire;
    # the player stays in room 54 (you then climb OUT with TREK/TIL UIT). If the harnas
    # is on neither fire side, no cross happens and the command falls through.
    if room == 54 and noun_is(noun, "VUUR"):
        from .verb_events import HARNAS, SPIN
        harnas_loc = eng.obj_loc.get(HARNAS)
        # Branch A (34->35): the EXE also guards on room != spider-loc (obj34); this is
        # trivially true in room 54 (the spider stays in the kruiskamer 34) — kept for
        # fidelity, no observable effect.
        if harnas_loc == 34 and eng.room != eng.obj_loc.get(SPIN):
            eng.obj_loc[HARNAS] = 35
            pr(eng, 277)
            return True
        # Branch B (35->34): no spider guard (the EXE branches are asymmetric).
        if harnas_loc == 35:
            eng.obj_loc[HARNAS] = 34
            pr(eng, 278)
            return True
        return False

    # DEATH branch (0x1a4b): GA VUUR while PHYSICALLY standing in the fire room —
    # the kruiskamer (34) or the schatkamer (35) — i.e. NOT inside the harnas (that
    # would be room 54). EXE: `cmp [0xe2e],0x22` OR `cmp [0xe2e],0x23`, ANDed with
    # noun==VUUR, no flag/object guard -> `mov [0xe34],0x119` (K=281 -> world[280]);
    # `call 0x5564` (print); `jmp 0x3ed3` (game-over hub). Walking into the fire
    # unprotected disintegrates you. Without this the command fell through to
    # resolve_verified (no VUUR row for 34/35) and wrongly printed "cant_go".
    if room in (34, 35) and noun_is(noun, "VUUR"):
        pr(eng, 280)
        eng.dead = True
        return True

    return False
