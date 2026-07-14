"""Verb state-change events — the puzzle state machine.

Faithful port of the object-manipulation verb handlers reverse-engineered in
docs/verb-events.md. Where room_events.py ports the describe-time chain (0x2399),
this module ports the per-verb handlers (PAK/LEG/OPEN/SLUIT/DUW/HAK/...): the
`(room, noun, precondition-flag)` guards, the DGROUP flag / object-location writes,
and the DRACULA.TXT response message for each branch.

Design
------
Each handler is a free function `name(eng, cmd)` that fully owns its verb group
(including the generic "else" branch). game.py's dispatcher delegates to these.

Object locations use the engine sentinels (engine/data/model.py):
    CARRIED (200)      object is held by the player   (EXE -1)
    LOC_NOWHERE (99)   object consumed / removed      (EXE 99)
    a room number      object lies in that room

Flags live in `eng.state` (the integer DGROUP map, keyed by the EXE address hex
like "e3e"; see room_events.FLAG_DEFAULTS). Message indices are already the
world.messages index (the EXE `[0xe34]=K -> world.messages[K-1]` off-by-one is
applied in docs/verb-events.md, so the numbers here match world.message_text()).

Nouns are matched against 4-char reference tokens with the same prefix rule the
parser uses (engine/parser.py): typed[:len(ref)] == ref.
"""
from __future__ import annotations

import threading

from .data.model import CARRIED, LOC_NOWHERE
from .data.lexicon import DEFAULT as _DEFAULT_LEXICON

# --- object loader-indices (verified against the live object table) ------------
# docs/verb-events.md §1: object k's EXE location var is [0xc5a + 2*k]; the engine
# keys obj_loc by the same loader index k.
LAMP, TOUW, WIG, KNOFLOOK, BOEK, KAPMES, LADDER = 0, 1, 2, 3, 4, 5, 6
HOUT, TAK, KRUIS, BIJL_SCHERP = 7, 8, 9, 10
SCHATKIST, BROOD, MUNT, MELK, LEGE_FLES, WATER, HALSBAND = 13, 14, 15, 16, 17, 18, 19
BED, KIST_DICHT, KIST_LUIK_DICHT, KIST_LUIK_OPEN = 20, 21, 22, 23
KIST_STOF, KIST_BOEK, KIST_LEEG, SCHERVEN, BOTTE_BIJL, SCHEP = 24, 25, 26, 27, 28, 29
WATERBRON, DOOS, HAMER, GIF_FLES, SPIN, BRIEFJE, HARNAS = 30, 31, 32, 33, 34, 35, 36
DOODSKIST, DOODSKIST_OPEN, DEUR_OPEN, DODE_SPIN = 37, 38, 39, 40


# --- small helpers -------------------------------------------------------------
def pr(eng, idx: int) -> None:
    """Print world.messages[idx] (guarded, like room_events.pr)."""
    if idx in eng.world.messages:
        eng.io.writeln(eng.world.message_text(idx))


# Active-language scenery-noun aliases: target-language 4-char token -> canonical Dutch
# token (chest CHES -> KIST). PER-THREAD, so concurrent web sessions (each in its own
# worker thread) never read one another's map. Empty in Dutch play. The dispatching Engine
# sets it each command from its world's lexicon (see Engine.dispatch).
_noun_canon_tls = threading.local()


def set_noun_canon(mapping: dict[str, str] | None) -> None:
    """Install this thread's active scenery-noun alias map (target token -> Dutch token)."""
    _noun_canon_tls.value = mapping or {}


def _active_noun_canon() -> dict[str, str]:
    """This thread's alias map (empty if none installed -> Dutch prefix behaviour)."""
    return getattr(_noun_canon_tls, "value", None) or {}


def canon_token(noun: str | None) -> str:
    """The canonical Dutch 4-char token a typed noun stands for. In Dutch play (no
    translation) that is the word's own first 4 chars (identity). Under a translation it
    is the mapped token for a translated word (door -> DEUR) and "" for anything else, so
    the target language's words drive navigation and the Dutch tokens do NOT leak in
    (English 'gate' must not resolve as the Dutch GAT/'hole')."""
    if not noun:
        return ""
    head = noun.upper()[:4]
    canon = _active_noun_canon()
    if canon:
        return canon.get(head, "")
    return head


def noun_is(noun: str | None, ref: str) -> bool:
    """Does the typed noun mean `ref` (a fixed Dutch token the handlers test against)?

    In Dutch play (no translation active) this is the parser's prefix rule:
    typed[:len(ref)] == ref. Under a translation it matches ONLY through that language's
    alias map (chest -> KIST): the raw Dutch prefix is deliberately NOT tried, so a Dutch
    token never shadows a target-language word -- e.g. English 'gate' means the grating
    (HEK), never the Dutch GAT ('hole'), and 'bedroom' the bedroom (SLAA), not 'bed'."""
    if not noun:
        return False
    r = ref.upper()
    active = _active_noun_canon()
    if active:
        canon = active.get(noun.upper()[:4])
        return canon is not None and canon[: len(r)] == r
    return noun.upper()[: len(r)] == r


def flag(eng, name: str) -> int:
    return eng.state.get(name, 0)


# PAK carry limit: [0x101c] decodes to MBF 7.0 and is numcmp'd against [0xe4a] (the
# carried-item count) at EXE 0x1e00 -> msg 22 when over. Object records have no small
# per-item weight field (the only numeric field is the 9..71 attribute, too large to
# sum under 7), so this is a plain count of at most 7 carried items.
_CARRY_LIMIT = 7


def _at_carry_limit(eng) -> bool:
    return sum(1 for v in eng.obj_loc.values() if v == CARRIED) >= _CARRY_LIMIT


def loc(eng, oid: int) -> int:
    return eng.obj_loc.get(oid)


def carried(eng, oid: int) -> bool:
    return eng.obj_loc.get(oid) == CARRIED


def present(eng, oid: int) -> bool:
    """The [0xe8a] 'present' predicate of the shared resolver 0x3822: an object is
    present when it is carried OR lies in the current room (loc in {room, CARRIED})."""
    return eng.obj_loc.get(oid) in (eng.room, CARRIED)


def resolve_carried(eng, noun: str | None):
    """First object the player is carrying whose token prefix-matches `noun`
    (the [0xe50]!=0 'carried?' branch of the generic resolver 0x3822)."""
    if not noun:
        return None
    w = noun.upper()
    for oid in eng.carried():
        for tok in eng.obj(oid).tokens:
            t = tok.upper()
            if t and w[: len(t)] == t:
                return oid
    return None


# --- LEG / ZET / DROP  (EXE 0x1f32) --------------------------------------------
def _for_all(eng, verb: str, oids) -> None:
    """PAK/LEG ALLE (EXE 0x2a47): re-run <verb> on each object in `oids`, by its first
    token — exactly as the original re-dispatches 'DROP <name>' / 'PAK <name>' per item,
    so each object runs its full per-object handler (drop message, FLES break, weight...)."""
    from .parser import Command
    handler = leg if verb == "leg" else pak
    for oid in oids:
        obj = eng.obj(oid)
        if obj.tokens:
            handler(eng, Command("", verb, verb, obj.tokens[0], None))


def leg(eng, cmd) -> None:
    """Place / drop. docs/verb-events.md §LEG. LEG/GOOI ALLE drops each carried item."""
    if noun_is(cmd.noun, "ALLE"):
        _for_all(eng, "leg", sorted(o for o, v in list(eng.obj_loc.items()) if v == CARRIED))
        return
    noun = cmd.noun
    if not noun:
        pr(eng, 200)                       # row 1: "Moet ik soms bepalen wat je..."
        return
    # row 2 (noun ALLE -> drop-all 0x2a47) is not ported; it falls through to the
    # single-object path below, which is a safe subset.

    oid = resolve_carried(eng, noun)
    if oid is None:
        pr(eng, 23)                        # row 3: "Dat heb je helemaal niet bij je."
        return

    # row 5: LADD @ rm 0 -> the ladder reaches the ceiling gat (becomes a fixture).
    if noun_is(noun, "LADD") and eng.room == 0:
        eng.state["e3e"] = 1
        eng.obj_loc[LADDER] = LOC_NOWHERE
        pr(eng, 25)
        return
    # row 7: LADD @ rm 30 -> the long ladder reaches the room-30 gat.
    if noun_is(noun, "LADD") and eng.room == 30:
        eng.state["e40"] = 1
        eng.obj_loc[LADDER] = LOC_NOWHERE
        pr(eng, 27)
        return
    # row 6: MUNT @ rm 16 -> the coin goes into the well.
    if noun_is(noun, "MUNT") and eng.room == 16:
        eng.state["e66"] = 1
        eng.obj_loc[MUNT] = eng.room
        pr(eng, 26)
        return

    # rows 4/4b (EXE 0x1f88-0x1fdf): dropping a FLES ALWAYS shatters the resolved
    # carried bottle (obj->99, scherven obj27 into the room, msg 24). If that bottle
    # is the blue-poison GIF_FLES (obj33) AND the room holds the spider (obj34, loc-var
    # [0xc9e], start room 34) it additionally kills the spider: obj34->99, dead-spider
    # obj40 into the room, msg 271 (AFTER msg 24). No flag writes — pure loc swaps.
    if noun_is(noun, "FLES"):
        eng.obj_loc[oid] = LOC_NOWHERE         # 0x1f9a [di+0xc58]=0x63: the bottle breaks
        eng.obj_loc[SCHERVEN] = eng.room       # 0x1fa3 [0xc90]=room: shards on the floor
        pr(eng, 24)                            # "De fles valt kapot op de grond."
        if oid == GIF_FLES and eng.room == loc(eng, SPIN):
            eng.obj_loc[SPIN] = LOC_NOWHERE    # 0x1fd0 [0xc9e]=0x63: the spider dies
            eng.obj_loc[DODE_SPIN] = eng.room  # 0x1fd9 [0xcaa]=room: the dead spider drops
            pr(eng, 271)                       # "Het gif stroomt uit de fles en de spin ..."
        return

    # row 8 (else): generic drop into the current room.
    eng.obj_loc[oid] = eng.room
    eng.io.writeln(f"{eng.obj(oid).display_name}{eng.lex.ui('DROPPED')}")


# --- PAK / GRIJP / NEEM / RAAP  (EXE 0x1b73) -----------------------------------
def pak(eng, cmd) -> None:
    """Take. docs/verb-events.md §PAK. Special (scenery / fixture / chest) branches
    are checked in EXE order first; the generic take is the else (row 13), whose
    error messages are preserved from the validated engine baseline. PAK ALLE takes
    each object present in the room."""
    if noun_is(cmd.noun, "ALLE"):
        _for_all(eng, "pak", sorted(o for o, v in list(eng.obj_loc.items()) if v == eng.room))
        return
    noun = cmd.noun
    if not noun:
        pr(eng, 199)                       # row 1: "... wat je zou willen pakken."
        return
    # row 2 (noun ALLE -> take-all 0x29aa) not ported; falls through to generic.

    # row 3: BOEK where the book-chest is ([0xc8c]=obj25 loc) -> take the book,
    # the chest is consumed. Dormant until the chest is revealed into a room.
    if noun_is(noun, "BOEK") and eng.room == loc(eng, KIST_BOEK):
        eng.obj_loc[KIST_BOEK] = LOC_NOWHERE
        eng.obj_loc[BOEK] = CARRIED
        eng.io.writeln(eng.lex.ui("OK"))
        return
    # row 4: the oak BED can't be taken.
    if noun_is(noun, "BED") and eng.room == 1:
        pr(eng, 204)
        return
    # row 5: the glass SCHERVen where they lie ([0xc90]=obj27 loc) cut your hands.
    if noun_is(noun, "SCHE") and eng.room == loc(eng, SCHERVEN):
        pr(eng, 248)
        return
    # rows 6/7: pick the placed ladder back up (clears its fixture flag).
    if noun_is(noun, "LADD") and eng.room == 0 and flag(eng, "e3e") == 1:
        eng.state["e3e"] = 0
        eng.obj_loc[LADDER] = CARRIED
        eng.io.writeln(eng.lex.ui("OK"))
        return
    if noun_is(noun, "LADD") and eng.room == 30 and flag(eng, "e40") == 1:
        eng.state["e40"] = 0
        eng.obj_loc[LADDER] = CARRIED
        eng.io.writeln(eng.lex.ui("OK"))
        return
    # row 8: loose ZAND/STOF just blows out of your hand.
    if (noun_is(noun, "ZAND") or noun_is(noun, "STOF")) and eng.room == 0:
        pr(eng, 229)
        return
    # row 9: KNOF -> the knoflook take event (EXE 0x39cc). The garlic (obj3) starts in
    # the herberg (room 12) with the waard, where it is effectively un-takeable: each
    # attempt angers him ([0xe84]++), and once he is angry enough the grab is fatal.
    if noun_is(noun, "KNOF"):
        pak_knoflook(eng)
        return

    # row 10: the immovable chests.
    if noun_is(noun, "KIST") and eng.room in (2, 14, 29):
        pr(eng, 21)
        return
    # row 11: the opened coffin ([0xca6]=obj38 loc). EXE 0x1d66: if you're carrying
    # anything (weight>0) it's too heavy -> msg 237 (drop everything first); empty-handed
    # you can take it -> carried + msg 238 "Met veel moeite pak je de kist." (the only
    # treasure-carrying escape once the front door has slammed shut).
    if (noun_is(noun, "KIST") or noun_is(noun, "DOOD")) and eng.room == loc(eng, DOODSKIST_OPEN):
        if eng.carried():
            pr(eng, 237)
        else:
            eng.obj_loc[DOODSKIST_OPEN] = CARRIED
            pr(eng, 238)
        return
    # row 12: Dracula's closed coffin ([0xca4]=obj37 loc) is too heavy.
    if (noun_is(noun, "KIST") or noun_is(noun, "DOOD")) and eng.room == loc(eng, DOODSKIST):
        pr(eng, 236)
        return

    # row 13 (else): generic take — preserved from the validated baseline (the
    # already-carried / not-here messages match the original, see docs/exe-map.md §8).
    oid = eng.resolve(noun)
    if oid is None:
        eng._not_here(noun)                # "Ik zie geen <noun> hier."
        return
    if eng.obj_loc[oid] == CARRIED:
        pr(eng, 247)                       # "Dat heb je al in je handen."
        return
    if _at_carry_limit(eng):
        pr(eng, 22)                        # 0x1e0e: "Dat wordt te zwaar, ... laten vallen."
        return
    eng.obj_loc[oid] = CARRIED
    eng.io.writeln(eng.lex.ui("OK_TAKE"))                 # 0x1e17: a single take prints "Ok"


def pak_knoflook(eng) -> None:
    """PAK KNOFLOOK — the un-takeable garlic event. Faithful port of EXE 0x39cc
    (dispatched from PAK, noun KNOF):

        room != knoflook-loc [0xc60]   -> msg 128 "Ik zie geen knoflook." (0x39d8)
        room == loc AND room != 12     -> generic take (0x39e8 -> 0x1dcc)
        room == 12:
            e84 > 1  -> KNIFE DEATH msg 142 + game over (0x39f5 -> 0x3ed3)
            e84 == 0 -> e84++ (->1) + msg 129                     (0x3a01)
            e84 == 1 -> e84++ (->2) + msg 129 THEN msg 130        (0x3a18)

    So the herberg garlic can be grabbed at most twice (each angers the waard); the
    third grab is fatal. The counter garlic is effectively un-takeable in room 12."""
    kloc = loc(eng, KNOFLOOK)              # obj3, starts room 12
    if eng.room != kloc:
        pr(eng, 128)                       # "Ik zie geen knoflook."
        return
    if eng.room != 12:
        # 0x39e8 -> 0x1dcc: the garlic is elsewhere -> a plain take (prints "Ok").
        if _at_carry_limit(eng):
            pr(eng, 22)
            return
        eng.obj_loc[KNOFLOOK] = CARRIED
        eng.io.writeln(eng.lex.ui("OK_TAKE"))
        return
    # room 12: reaching for the waard's garlic.
    if flag(eng, "e84") > 1:               # 0x39eb: already angry enough -> fatal
        pr(eng, 142)                       # the knife death
        eng.dead = True
        return
    eng.state["e84"] = flag(eng, "e84") + 1
    pr(eng, 129)                           # "De waard zegt 'Wat moet dat daar?'…"
    if flag(eng, "e84") > 1:               # was e84==1 -> now 2: he also slaps you
        pr(eng, 130)                       # "Dan stroopt de waard een mouw op…"


# --- KOOP  (EXE 0x3a24) — buy (knoflook-framed) --------------------------------
def koop(eng, cmd) -> None:
    """KOOP — buy. Faithful port of the tavern-buy handler EXE 0x3a24 (verb KOOP
    dispatched at 0xd6b-0xd76 -> jmp 0x3a24). KOOP is entirely knoflook-framed: it
    only ever hands over the streng knoflook (obj3, loc-var [0xc60], start room 12)
    and rejects everything else with a canned line. Branches in EXE order:

        1 (0x3a24): room != knoflook-loc [0xc60]      -> msg 131 "Ik zie geen knoflook."
                    (covers being elsewhere, and after the garlic is taken/given so
                    [0xc60] is -1/CARRIED).
        2 (0x3a39): NOT(noun~KNOF AND room==12)       -> msg 132 "Je kan het gewoon
                    pakken hoor.." (De-Morgan of the QB AND idiom; the EXE B$SCMP
                    matches 'KNOF'@0x1586 ONLY — the synonym token 'STRE' is rejected).
        3 (0x3a67): noun~KNOF AND room==12 AND e84>0  -> msg 133 (the waard calms),
                    SET e84=0; the garlic is NOT handed over on this turn.
        4 (0x3a80): noun~KNOF AND room==12 AND e84<=0 -> msg 134 then jmp 0x1dcc the
                    generic take: hand the garlic over (obj3 -> CARRIED, print
                    'streng knoflook : gepakt.'). TWO lines printed.

    Only writes: [0xe84]=0 (branch 3) and obj3 KNOFLOOK loc -> CARRIED (branch 4).
    No navigation. e84 is read (jg) in branches 3/4 and cleared in branch 3. The
    buy directly hands the garlic over (mirroring pak_knoflook's room!=12 plain take)
    rather than re-entering PAK, whose row-9 KNOF special would loop back here."""
    noun = cmd.noun
    # Branch 1 (0x3a24): the garlic must lie in the current room.
    if eng.room != loc(eng, KNOFLOOK):
        pr(eng, 131)                       # "Ik zie geen knoflook."
        return
    # Branch 2 (0x3a39): only 'KOOP knoflook' in the herberg (room 12) is a real buy;
    # any other noun — or the garlic lying in some room other than 12 — is 'just pick
    # it up'. 'KNOF' only (not the synonym 'STRE'); empty noun also lands here.
    if not (noun_is(noun, "KNOF") and eng.room == 12):
        pr(eng, 132)                       # "Je kan het gewoon pakken hoor.."
        return
    # Branch 3 (0x3a67): an angry waard is first calmed; the garlic is withheld.
    if flag(eng, "e84") > 0:
        pr(eng, 133)                       # "De waard gromt en lijkt wat rustiger..."
        eng.state["e84"] = 0
        return
    # Branch 4 (0x3a80 -> 0x1dcc): the calm waard hands the streng over.
    pr(eng, 134)                           # "De waard zegt 'Je mag het knoflook wel..'"
    if _at_carry_limit(eng):
        pr(eng, 22)                        # 0x3a80 -> 0x1dcc weight check
        return
    eng.obj_loc[KNOFLOOK] = CARRIED
    eng.io.writeln(eng.lex.ui("OK_TAKE"))            # 0x3a80 -> 0x1dcc generic take: "Ok"


# --- BLAAS  (EXE 0x1b11) — blow the dust off the herberg-zolder chest -----------
def blaas(eng, cmd) -> None:
    """Blow. Standalone handler EXE 0x1b11 (verb 'BLAAS'@0x11f6 dispatched at 0xa44).
    Fully static: no RNG, no flag writes — two object-location writes and one of
    three messages. Branches in EXE order:

        guard (0x1b11-0x1b3d, De-Morgan of the QB AND idiom): success iff
              room [0xe2e]==14 (donkere zolder van de herberg) AND noun [0xe14]
              is STOF (0x1554) or KIST (0x154c); else [0xe34]=0xD4=212 -> msg 211.
        0x1b4b: dusty chest already gone (obj24 loc [0xc8a] != 14) -> msg 19.
        0x1b5e: dusty chest present (obj24 loc == 14) -> msg 20, obj24 KIST_STOF
              -> LOC_NOWHERE (99), obj25 KIST_BOEK -> room 14 (book-chest revealed;
              PAK BOEK row 3 then becomes live). Every branch ends jmp 0x261."""
    noun = cmd.noun
    # guard: wrong room / wrong or missing noun -> "pffffff".
    if not (eng.room == 14 and (noun_is(noun, "STOF") or noun_is(noun, "KIST"))):
        pr(eng, 211)
        return
    # dusty chest already blown away (obj24 no longer in room 14).
    if loc(eng, KIST_STOF) != 14:
        pr(eng, 19)                        # "Er is niets stoffigs hier."
        return
    # reveal: consume the dusty chest, place the book-chest in room 14.
    pr(eng, 20)                            # "Onder het stof komt een boek tevoorschijn."
    eng.obj_loc[KIST_STOF] = LOC_NOWHERE   # 0x1b64 [0xc8a]=0x63
    eng.obj_loc[KIST_BOEK] = 14            # 0x1b6a [0xc8c]=0xE


# --- DUW / DRUK / SPRIN  (EXE 0x2bb8) — push -----------------------------------
def duw(eng, cmd) -> None:
    """Push. docs/verb-events.md §DUW."""
    noun = cmd.noun
    if noun_is(noun, "WAAR") and eng.room == 12:
        pr(eng, 64)                        # row 1: the innkeeper glares at you
        return
    if not (noun_is(noun, "STEE") and eng.room == 39):
        pr(eng, 67)                        # row 2: "Er gebeurt helemaal niets."
        return
    if flag(eng, "e42") == 1:
        pr(eng, 65)                        # row 3: stone won't turn further
        return
    eng.state["e42"] = 1                    # row 4: opens the grave passage 39<->37
    pr(eng, 66)


# --- SPRING  (EXE 0x2b46) — jump ------------------------------------------------
# The fatal balcony rooms (0x2b65: room==25 OR room==28). The two non-fatal jumps
# (room 18 -> 17, room 33 -> 30) call the deferred 0x4e21 object-scatter, as elsewhere.
JUMP_FATAL_ROOMS = (25, 28)


def spring(eng, cmd) -> None:
    """Jump — faithful port of the standalone SPRING handler EXE 0x2b46 (verb SPRIN,
    dispatched at 0xa1a). The engine previously MIS-ROUTED 'spring' to `duw`; it is a
    self-contained handler that branches on the current room, in EXE order:

        room 18 (0x2b46):        msg 62 'Iaaaaaaahhhh...'      + move to room 17   (jmp 0x305 redescribe)
        room 25 or 28 (0x2b65):  msg 218 'B A F F ...je sterft' + GAME OVER (fatal, jmp 0x3ed3)
        room 33 (0x2b90):        msg 224 '>>>> BAF <<<< ...enkel' + move to room 30 (jmp 0x305 redescribe)
        else (0x2baf):           msg 63 'hop.....hop....hop..'  (jmp 0x261, no move)

    The noun is ignored (the EXE branches on [0xe2e] only). The two non-fatal moves
    print, change the room, then redescribe (`jmp 0x305` = call 0x4f40); the fatal
    jump routes to the shared game-over hub (game.py prints messages[166] then stops)."""
    room = eng.room
    if room == 18:
        pr(eng, 62)
        eng.room = 17
        eng.describe_room()                # 0x2b62 jmp 0x305
        return
    if room in JUMP_FATAL_ROOMS:
        pr(eng, 218)
        eng.dead = True                    # 0x2b8d jmp 0x3ed3 (game-over hub)
        return
    if room == 33:
        pr(eng, 224)
        eng.room = 30
        eng.describe_room()                # 0x2bac jmp 0x305
        return
    pr(eng, 63)                            # 0x2baf else (jmp 0x261, no move)


# --- HANG / KNOOP / BEVES  (EXE 0x2faa) — tie -----------------------------------
def hang(eng, cmd) -> None:
    """Tie. docs/verb-events.md §HANG."""
    noun = cmd.noun
    if not noun_is(noun, "TOUW"):
        pr(eng, 83)                        # row 1: "Ik denk niet dat dat nodig is."
        return
    if not carried(eng, TOUW):
        pr(eng, 84)                        # row 2: "Je hebt het niet eens bij je."
        return
    if eng.room != 25:
        pr(eng, 85)                        # row 3: "Waaraan ?"
        return
    # row 4: rope tied to the balcony -> enables the ledge descent.
    eng.obj_loc[TOUW] = LOC_NOWHERE
    eng.obj_loc[12] = eng.room             # obj12 = "touw vastgebonden aan het balkon"
    eng.state["e92"] = 1
    pr(eng, 86)


# --- GEEF  (EXE 0x3f58) — give -------------------------------------------------
def geef(eng, cmd) -> None:
    """Give. docs/verb-events.md §GEEF."""
    noun = cmd.noun
    if not noun:
        pr(eng, 179)                       # row 1
        return
    if not (noun_is(noun, "MUNT") and eng.room == 12):
        pr(eng, 180)                       # row 2: "Het wordt niet aangepakt."
        return
    if not carried(eng, MUNT):
        pr(eng, 181)                       # row 3: "Je hebt de munt niet bij je."
        return
    # row 4 (0x3fae): coin given away. The EXE ALWAYS prints msg 182 first (0x3fb4
    # sets [0xc78]=99); then, if the waard was angry (e84>0), it also prints the
    # calming line 189 and clears e84 (0x3fc4->0x3fcd). The calm path prints only 182.
    eng.obj_loc[MUNT] = LOC_NOWHERE
    pr(eng, 182)
    if flag(eng, "e84") > 0:               # row 4b: calms the angry innkeeper
        pr(eng, 189)
        eng.state["e84"] = 0


# --- enter-harnas  (EXE 0x4ca9) — DRAAG / PAS (and the engine's VRAAG) ----------
def enter_harnas(eng) -> None:
    """Climb into the iron armour — faithful port of EXE handler 0x4ca9. In the
    harnas's room ([0xca2]=obj36 loc) set room 54 and redescribe; anywhere else print
    world[276] "Ik zie geen harnas hier.". The handler IGNORES the noun.

    EXE truth (verified, dispatcher 0x0928-0x0949): this handler is dispatched by the
    verbs PAS (0x1164) and DRAAG (0x116c). The engine historically wired it under VRAAG
    (kept as-is — see `vraag`); the real EXE VRAAG is the innkeeper handler 0x2ab5."""
    if eng.room == loc(eng, HARNAS):
        eng.room = 54
        eng.describe_room()
        return
    pr(eng, 276)


def vraag(eng, cmd) -> None:
    """VRAAG WAARD — the two-men conversation with the innkeeper. Faithful port of EXE
    handler 0x2ab5 (dispatcher 0x091a->0x0925). The harnas (enter-harnas 0x4ca9) is a
    SEPARATE handler reached by DRAAG/PAS — see `draag`/`pas` above.

    Guard (0x2ab5-0x2ad3, De Morgan of the QB AND idiom): if NOT(room==12 AND
    noun~=WAAR) -> msg 56 "Niemand geeft antwoord." Otherwise, in room 12 asking the
    waard (0x2ae1 onward):
        e6e != 0                -> msg 57 (he's already told you; "Ben je doof of zo")
        e6e == 0 AND e84 > 0    -> msg 58 (angry brush-off)
        e6e == 0 AND e84 <= 0   -> SET e6e=1 (reveal the zoldertrap) + msg 59 (0x2b08)
    The only flag write is e6e=1; it also enables the describe-time room-12 zoldertrap
    line (room_events #8, msg 47)."""
    noun = cmd.noun
    if not (eng.room == 12 and noun_is(noun, "WAAR")):
        pr(eng, 56)                        # "Niemand geeft antwoord."
        return
    if flag(eng, "e6e") != 0:
        pr(eng, 57)                        # already revealed
        return
    if flag(eng, "e84") > 0:
        pr(eng, 58)                        # angry -> won't talk
        return
    eng.state["e6e"] = 1                    # 0x2b08: reveal the zoldertrap
    pr(eng, 59)


def draag(eng, cmd) -> None:
    """Wear / carry (DRAAG). EXE dispatcher 0x0928-0x0949 routes DRAAG to the
    enter-harnas handler 0x4ca9 (the noun is ignored)."""
    enter_harnas(eng)


def pas(eng, cmd) -> None:
    """Try on (PAS). Same EXE handler 0x4ca9 as DRAAG (dispatcher 0x0928-0x0949)."""
    enter_harnas(eng)


# --- TIL / TREK  (EXE 0x4bd7) — lift / pull ------------------------------------
def til_trek(eng, cmd) -> None:
    """Lift / pull. The dispatcher routes both parser verbs 'til' (0x1274) and
    'trek' (0x127c) to the self-contained handler 0x4bd7 (dispatch chain
    0xb15-0xb36). Four special branches in EXE order, then a generic PAK take
    fallthrough. There are NO flag writes — only the current room ([0xe2e])
    changes, for the harnas enter/exit. (There is no iron-ring / LUIK branch here:
    'aan de ijzeren ring...te trekken' is msg 117 printed by BEKIJK LUIK, and the
    bedroom luik is opened by OPEN LUIK — so TREK RING/LUIK fall through to PAK.)"""
    noun = cmd.noun
    room = eng.room

    # Branch A (0x4bd7): BED. In the bedroom (room 1) the oak bed won't budge;
    # anywhere else there is no bed, so print the shared 'Ik zie geen <noun> hier.'
    # (0x4c88 == eng._not_here). BED never falls through to the generic take.
    if noun_is(noun, "BED"):
        if room == 1:
            pr(eng, 205)                   # "Mhhhhhnnnnggggg...Nee, het lukt niet."
        else:
            eng._not_here(noun)
        return
    # Branch B (0x4bf8): KIST in Dracula's closed-coffin room ([0xca4]=obj37 loc,
    # init 37) -> the coffin lifts a little but nothing is under it. NOTE: only
    # 'KIST' (not 'DOOD'), and only this room — elsewhere KIST falls to PAK, which
    # owns the coffin 'te zwaar' replies (236/237).
    if noun_is(noun, "KIST") and room == loc(eng, DOODSKIST):
        pr(eng, 239)                       # "Je tilt de kist ... maar er ligt niets onder."
        return
    # Branch C (0x4c26): climb OUT of the armour. While inside (room 54), UIT or
    # HARN returns you to the harnas's room ([0xca2]=obj36 loc, init 21).
    if (noun_is(noun, "UIT") or noun_is(noun, "HARN")) and room == 54:
        eng.room = loc(eng, HARNAS)
        eng.describe_room()
        return
    # Branch D (0x4c60): climb INTO the armour. HARN in the harnas's room enters the
    # VRAAG body 0x4ca9 which (room==loc(HARNAS) holds) sets room 54 and redescribes.
    if noun_is(noun, "HARN") and room == loc(eng, HARNAS):
        eng.room = 54
        eng.describe_room()
        return
    # Branch E (0x4c85): everything else -> generic PAK take (which itself owns the
    # other KIST / coffin / scenery replies).
    pak(eng, cmd)


# --- OPEN  (EXE 0x2c32) — front-door / window / hatch / gate / chest / box ------
def open_(eng, cmd) -> None:
    """Open. docs/verb-events.md §OPEN, evaluated in EXE order."""
    noun = cmd.noun
    room = eng.room

    # rows 1/2: window (rooms 0<->6).
    if noun_is(noun, "RAAM") and room in (0, 6):
        if flag(eng, "e3c") == 0:
            pr(eng, 234)                   # already open
        else:
            eng.state["e3c"] = 0           # open it (rm 0<->6 passable)
            pr(eng, 232)
        return
    # row 3: the front door is already open enough.
    if noun_is(noun, "DEUR") and room == 0:
        pr(eng, 282)
        return
    # rows 4/5/6: bedroom luik (room 1).
    if noun_is(noun, "LUIK") and room == 1:
        if flag(eng, "e86") == 0:
            pr(eng, 69)                    # not revealed yet ("Ik zie geen 'luik'.")
        elif flag(eng, "e88") == 1:
            pr(eng, 70)                    # already open
        else:
            eng.state["e88"] = 1           # opens (rooms 1<->4)
            pr(eng, 71)
        return
    # rows 7/8/9: iron gate (rooms 32/37).
    if noun_is(noun, "HEK") and room in (32, 37):
        if flag(eng, "e44") == 1:
            pr(eng, 72)                    # already open
        elif room == 32:
            pr(eng, 73)                    # can't open from the gewelf side
        else:
            eng.state["e44"] = 1           # opens (rm 32<->37)
            pr(eng, 74)
        return
    # row 10: room-14 chest.
    if noun_is(noun, "KIST") and room == 14:
        pr(eng, 75)
        return
    # row 11: Dracula's coffin ([0xca4]=obj37 loc). Opening it wakes Dracula.
    if (noun_is(noun, "KIST") or noun_is(noun, "DOOD")) and room == loc(eng, DOODSKIST):
        eng.state["e76"] = 1
        eng.state["dde"] = 37
        eng.obj_loc[DOODSKIST] = LOC_NOWHERE
        eng.obj_loc[DOODSKIST_OPEN] = room
        pr(eng, 242)
        pr(eng, 243)
        return
    # row 12: coffin already open ([0xca6]=obj38 loc).
    if (noun_is(noun, "KIST") or noun_is(noun, "DOOD")) and room == loc(eng, DOODSKIST_OPEN):
        pr(eng, 244)
        return
    # row 13: tower chest (obj21 closed -> obj22 opened-with-luik).
    if noun_is(noun, "KIST") and room == loc(eng, KIST_DICHT):
        eng.obj_loc[KIST_DICHT] = LOC_NOWHERE
        eng.obj_loc[KIST_LUIK_DICHT] = room
        pr(eng, 76)
        return
    # row 14: room-2 chest has no lid.
    if noun_is(noun, "KIST") and room == 2:
        pr(eng, 206)
        return
    # rows 15/16: the tower-chest luik (obj22 -> obj23), gated on Dracula active.
    if noun_is(noun, "LUIK") and room == 29 and room == loc(eng, KIST_LUIK_DICHT):
        if flag(eng, "e72") == 1:
            eng.obj_loc[KIST_LUIK_DICHT] = LOC_NOWHERE
            eng.obj_loc[KIST_LUIK_OPEN] = room
            pr(eng, 78)
        else:
            pr(eng, 79)                    # muurvast
        return
    # rows 17/18: the wooden doos (drops the hamer).
    doos_present = loc(eng, DOOS) == room or carried(eng, DOOS)
    if noun_is(noun, "DOOS") and doos_present:
        if flag(eng, "e8c") == 1:
            pr(eng, 80)                    # already open
        else:
            eng.state["e8c"] = 1
            eng.obj_loc[HAMER] = room      # the hammer falls out
            pr(eng, 81)
        return
    # OPEN BOEK (book present, carried or in the room) -> the "just read it" quip. EXE
    # 0x2ece: (noun==BOEK) AND ([0xc62]==room OR [0xc62]==-1).
    if noun_is(noun, "BOEK") and present(eng, BOEK):
        pr(eng, 213)
        return
    # OPEN LUIK away from any hatch -> "Ik zie geen luik." (EXE 0x2f20: room != obj22 loc,
    # after the room-1 and tower-luik cases above).
    if noun_is(noun, "LUIK"):
        pr(eng, 77)
        return
    # row 19 (else): can't see how to open that.
    pr(eng, 82)


# --- SLUIT  (EXE 0x3d8b) — close -----------------------------------------------
def sluit(eng, cmd) -> None:
    """Close. docs/verb-events.md §SLUIT."""
    noun = cmd.noun
    room = eng.room

    # row 1: the room-23 exit door latches shut.
    if noun_is(noun, "DEUR") and room == 23:
        eng.state["df0"] = 0
        pr(eng, 163)
        return
    # rows 2/3: the window (rooms 0<->6).
    if noun_is(noun, "RAAM") and room in (0, 6):
        if flag(eng, "e3c") != 0:
            pr(eng, 233)                   # already closed
        else:
            eng.state["e3c"] = -1          # close it (blocks rm 0<->6)
            pr(eng, 231)
        return
    # row 4: the castle door (rooms 20/21) won't budge.
    if noun_is(noun, "DEUR") and room in (20, 21):
        pr(eng, 161)
        return
    # row 5: the house doors have no lock; the wind blows them open.
    if noun_is(noun, "DEUR") and room in (0, 11):
        pr(eng, 162)
        return
    # row 6: the room-40 door swings back open.
    if noun_is(noun, "DEUR") and room == 40:
        pr(eng, 164)
        return
    # row 7 (KIST close variants) — faithful port of EXE 0x3d90:
    if noun_is(noun, "KIST"):
        if room == 2:
            pr(eng, 206)                       # 0x3da3: "Er zit geen deksel op de kist."
        elif room == 14:
            pr(eng, 159)                       # 0x3db6: same text, room-14 index
        elif room == loc(eng, DOODSKIST):      # 0x3dbf: Dracula's coffin ([0xca4])
            pr(eng, 240 if flag(eng, "e76") == 0 else 241)   # already shut / won't shut
        else:
            pr(eng, 160)                       # 0x3de7: "Wat voor kist ?"
        return
    # row 8 (else): nothing moves.
    pr(eng, 165)


# --- HAK / KAP  (EXE 0x20bf) — chop --------------------------------------------
_TREE_ROOMS = {7, 8, 9, 10, 15, 17, 18}


def hak(eng, cmd) -> None:
    """Chop. docs/verb-events.md §HAK."""
    noun = cmd.noun
    if not noun_is(noun, "BOOM"):
        pr(eng, 1)                         # row 1: "Dat gaat niet."
        return
    if eng.room not in _TREE_ROOMS:
        pr(eng, 28)                        # row 2: no trees here
        return
    if carried(eng, BOTTE_BIJL):
        pr(eng, 29)                        # row 3: the axe is too blunt now
        return
    if not carried(eng, BIJL_SCHERP):
        pr(eng, 2)                         # row 4: not with your bare hands
        return
    # row 5: chop -> wood in the room; the sharp axe dulls into the blunt one.
    eng.obj_loc[HOUT] = eng.room
    eng.obj_loc[BIJL_SCHERP] = LOC_NOWHERE
    eng.obj_loc[BOTTE_BIJL] = CARRIED
    pr(eng, 30)


# --- SNIJ  (EXE 0x3203) — carve wood -------------------------------------------
def _snij_carve_wood(eng) -> None:
    """Shared EXE 0x3278 tail: carve the carried wood into the cross, else 'geen hout'.
    Reached by SNIJ HOUT (fallthrough) and SNIJ KRUI (0x32c3 -> 0x3278) alike."""
    if not carried(eng, HOUT):
        pr(eng, 103)                       # 0x3282: "Ik zie geen hout."
        return
    pr(eng, 104)                           # 0x328b: "Na enig snijwerk ... de vorm van een kruis."
    eng.obj_loc[HOUT] = LOC_NOWHERE        # EXE [0xc68] = 0x63
    eng.obj_loc[KRUIS] = CARRIED           # EXE [0xc6c] = 0xffff


def snij(eng, cmd) -> None:
    """Carve wood. Standalone handler EXE 0x3203 (dispatched at 0x0d5d -> jmp 0x3203;
    NOT shared with KOOP, which is a separate tavern-buy handler at 0x3a24).

    The kapmes (obj5) must be CARRIED as a universal precondition; then the handler
    dispatches on the noun in EXE order TAK, HOUT, KRUI, BOOM, else. Only the HOUT and
    KRUI branches with the wood carried perform a transformation — carving it into the
    cross (obj7 -> LOC_NOWHERE, obj9 -> CARRIED, msg 104), which is the ONLY way the
    cross (consumed later by TOON KRUIS) enters play. Every branch prints exactly one
    message; there are no flag writes and no navigation."""
    noun = cmd.noun
    room = eng.room

    # Gate (0x3203): the kapmes must be in hand.
    if not carried(eng, KAPMES):
        pr(eng, 2)                         # "Wou je dat met je blote handen proberen ??"
        return

    # TAK (0x3216): a branch can't be carved into anything.
    if noun_is(noun, "TAK"):
        if loc(eng, TAK) == room:
            pr(eng, 3)                     # 0x3230: "...je zult het eerst moeten pakken."
        elif not carried(eng, TAK):
            pr(eng, 101)                   # 0x3243: "Ik zie geen tak hier."
        else:
            pr(eng, 102)                   # 0x324c: "Met de tak valt niks te beginnen."
        return

    # HOUT (0x3255): carve the carried wood; if it lies in the room, take it first.
    if noun_is(noun, "HOUT"):
        if loc(eng, HOUT) == room:
            pr(eng, 3)                     # 0x326f: "...je zult het eerst moeten pakken."
            return
        _snij_carve_wood(eng)              # 0x3278 tail
        return

    # KRUI (0x32a0): same carve, but wood-in-room asks for a piece of wood (msg 105,
    # DISTINCT from HOUT's msg 3); otherwise falls through to the exact HOUT tail.
    if noun_is(noun, "KRUI"):
        if loc(eng, HOUT) == room:
            pr(eng, 105)                   # 0x32ba: "Je hebt daar een stuk hout voor nodig."
            return
        _snij_carve_wood(eng)              # 0x32c3 -> 0x3278 tail
        return

    # BOOM (0x32c6): whittling the standing tree just sheds splinters.
    if noun_is(noun, "BOOM"):
        pr(eng, 106)                       # 0x32d4: "Er dwarrelen wat snippertjes af."
        return

    # else (0x32dd): any other noun, or none.
    pr(eng, 107)                           # "Dat heeft geen zin."


# --- VUL  (EXE 0x3175) — fill the empty bottle at the well ----------------------
def vul(eng, cmd) -> None:
    """Fill. Standalone handler EXE 0x3175 — the verb dispatcher routes VUL
    (string 0x136c) via `0xd36 jmp 0x3175`, SEPARATELY from EET/DRINK which route to
    0x22b8 (see `eten` below). VUL fills the empty bottle (obj17 LEGE_FLES) with water
    at the well/bron (room 16); the branches are evaluated in EXE order:

        1 (0x3175): noun != FLES                     -> msg 95, return
        2 (0x318c): room != 16                       -> msg 96, return
        3 (0x319f): MELK (obj16) carried             -> msg 97, return
        4 (0x31b2): WATER (obj18) carried            -> msg 98, return
        5 (0x31c5): empty bottle (obj17) NOT carried -> msg 99, return
        6/7 (0x31d8): fill -> msg 100, obj17 -> LOC_NOWHERE, then
              e66 == 1 (coin thrown in well): obj33 GIF_FLES  -> CARRIED (poison)
              e66 != 1                       : obj18 WATER     -> CARRIED

    e66 is READ-only here (set by LEG MUNT @ rm 16 in `leg`); no flag writes, no
    navigation. Message indices are the world.messages index (EXE [0xe34]=K prints
    world.messages[K-1], already applied)."""
    noun = cmd.noun
    # 0x3175: the noun must be FLES (B$SCMP [0xe14] vs 'FLES').
    if not noun_is(noun, "FLES"):
        pr(eng, 95)                        # "Hoe wou je dat vullen ?"
        return
    # 0x318c: only at the well (room 16).
    if eng.room != 16:
        pr(eng, 96)                        # "Waarmee ?"
        return
    # 0x319f: already carrying the bottle of milk.
    if carried(eng, MELK):
        pr(eng, 97)                        # "Er zit al melk in."
        return
    # 0x31b2: already carrying a full bottle of water.
    if carried(eng, WATER):
        pr(eng, 98)                        # "De fles zit nog vol met water."
        return
    # 0x31c5: you must actually hold the empty bottle (jg = loc > -1 -> not carried).
    if not carried(eng, LEGE_FLES):
        pr(eng, 99)                        # "Je hebt geen fles bij je."
        return
    # 0x31d8: fill it. The empty bottle is consumed; a coin in the well (e66==1)
    # turns the water into blue poison (obj33), otherwise you get plain water (obj18).
    pr(eng, 100)                           # "De fles vult zich langzaam.."
    eng.obj_loc[LEGE_FLES] = LOC_NOWHERE
    if flag(eng, "e66") == 1:
        eng.obj_loc[GIF_FLES] = CARRIED    # 0x31f1: blue poison bottle
    else:
        eng.obj_loc[WATER] = CARRIED       # 0x31fa: ordinary water bottle


# --- EET / DRINK  (EXE 0x22b8) — eat / drink -----------------------------------
def eten(eng, cmd) -> None:
    """Eat / drink. docs/verb-events.md §VUL. NOTE: only EET (0x1374) and DRINK
    (0x137c) route here (dispatch `0xd5a jmp 0x22b8`); VUL is the SEPARATE handler
    `vul` above (0x3175). This handler consumes the water/poison bottle that `vul`
    produces (DRINK WATE: GIF_FLES -> df6=-1 msg 36; WATER -> LEGE_FLES msg 37)."""
    noun = cmd.noun
    if not (noun_is(noun, "BROO") or noun_is(noun, "WATE") or noun_is(noun, "MELK")):
        pr(eng, 0)                         # row 1: "Doe niet zo achterlijk.."
        return
    if noun_is(noun, "MELK"):
        if not carried(eng, MELK):
            pr(eng, 3)                     # row 2: grab it first
            return
        eng.obj_loc[MELK] = LOC_NOWHERE    # row 3: drunk -> empty bottle
        eng.obj_loc[LEGE_FLES] = CARRIED
        pr(eng, 35)
        return
    if noun_is(noun, "WATE"):
        if carried(eng, GIF_FLES):
            eng.state["df6"] = -1          # row 4: the blue poison water (EXE 0x234b)
            pr(eng, 36)                    # "...zeer giftig...Je sterft na enkele minuten.."
            # FAITHFUL (verified vs the disassembly): the poison NEVER kills. 0x234b
            # sets [0xdf6]=-1 then `jmp 0x261`; the main loop's very next end-of-turn
            # `0x30e call 0x269e` opens with `mov [0xdf6],0`, unconditionally wiping the
            # latch BEFORE the `0x0311 cmp [0xdf6]` death-check — so the original reads 0
            # and never dies (a latent bug the "Je sterft" flavour text never delivers).
            # We therefore do NOT set eng.dead here: DRINK WATE is death-neutral, exactly
            # like DRACULA.EXE. (The GIF_FLES is not consumed — still throwable at the spider.)
            return
        if not carried(eng, WATER):
            pr(eng, 3)                     # (no water bottle in hand -> grab first)
            return
        eng.obj_loc[WATER] = LOC_NOWHERE   # row 5: ordinary water -> empty bottle
        eng.obj_loc[LEGE_FLES] = CARRIED
        pr(eng, 37)
        return
    # BROO
    if not carried(eng, BROOD):
        pr(eng, 3)                         # row 6
        return
    eng.obj_loc[BROOD] = LOC_NOWHERE       # row 7: eaten
    pr(eng, 38)


# --- GRAAF / SCHEP  (EXE 0x21bd) — dig -----------------------------------------
def graaf(eng, cmd) -> None:
    """Dig — faithful port of EXE 0x21bd (verified against the disassembly).

    The message branches (rows 1-3) are unchanged; the tunnel-network movement
    (rows 4-6) is now wired:

      ROW4 (0x221e): the GRON/GAT noun (as opposed to a compass direction) is not a
                     dig direction -> msg 33 'Geef een richting...' and RETURN.
      ROW5 (0x224b): room 4 -> tunnel down to room 5 (deterministic).
      ROW6 (0x225e): room 5 or 39, LEFT$(noun,1)=='N' -> room 39 (deterministic).
      ROW6-else (0x227c): room 5 or 39, non-N -> int(RND(1.0)*2)+7 in {7,8} (both
                     'donker woud'); advances the shared RNG exactly once, then the
                     describe path draws its own bird/spawn RNDs (EXE jmp 0x2f5)."""
    noun = cmd.noun
    if not carried(eng, SCHEP):
        pr(eng, 2)                         # row 1: not with your bare hands
        return
    if eng.room == 36:
        eng.obj_loc[WATERBRON] = eng.room  # row 2: graveyard bones surface (obj uncertain, §6)
        pr(eng, 31)
        return
    if eng.room not in (4, 5, 39):
        pr(eng, 32)                        # row 3: ground too hard
        return
    # ROW4 (0x221e): 'grond'/'gat' is not a direction -> ask for one, no move.
    if noun_is(noun, "GRON") or noun_is(noun, "GAT"):
        pr(eng, 33)
        return
    # ROW5 (0x224b): dig a direction in room 4 -> down to room 5.
    if eng.room == 4:
        eng.room = 5
        eng.describe_room()
        return
    # ROW6 (0x225e): LEFT$(noun,1)=='N' (dig north) from room 5/39 -> room 39.
    if noun and noun.upper()[:1] == "N":
        eng.room = 39
        eng.describe_room()
        return
    # ROW6-else (0x227c): any other direction -> a random donker-woud room {7,8}.
    eng.room = int(eng.rng.rnd(1.0) * 2.0) + 7
    eng.describe_room()


# --- BEKIJK / ONDER  (EXE 0x32e6) — examine -------------------------------------
def bekijk(eng, cmd) -> None:
    """Examine — faithful port of the shared BEKIJK/ONDER handler EXE 0x32e6.

    The handler opens with `call 0x3822` (the shared resolver): it sets [0xe8a]=1
    iff a noun-matching object is present (carried or in the current room), and
    [0xe54] = that object's EXE 1-based index (loader index + 1). Then ~18 per-noun
    look-text branches evaluate in EXE order before the generic else (0x3803). Every
    branch's message index is the world.messages index (EXE [0xe34]=K -> world[K-1]).

    LEES (0x3076) reads BOEK/TEKS/BRIE/INSC first and then jmps here for any other
    noun; see `lees`. The BED (0x35d0) and TORE/GAT (0x3741) branches are kept."""
    noun = cmd.noun
    if not noun:
        # 0x3803 with an empty noun -> the resolver leaves [0xe8a]=1, so the generic
        # else prints msg 121 (NOT a room redescription). SS-906: bare BEKIJK -> 121.
        pr(eng, 121)
        return
    room = eng.room

    # 0x32e9: WIG present -> the stake description.
    if noun_is(noun, "WIG") and present(eng, WIG):
        pr(eng, 108)
        return
    # 0x330c: BOEK present -> the physical description (its content is LEES BOEK -> 91).
    if noun_is(noun, "BOEK") and present(eng, BOEK):
        pr(eng, 109)
        return
    # 0x332f: (BLOE|VLEK) & room 14 -> the blood-type easter egg (scenery).
    if (noun_is(noun, "BLOE") or noun_is(noun, "VLEK")) and room == 14:
        pr(eng, 212)
        return
    # 0x3369: KAPM present -> the machete description.
    if noun_is(noun, "KAPM") and present(eng, KAPMES):
        pr(eng, 110)
        return
    # 0x338c: HARN present -> "Je zou er precies inpassen." (only the HARN token).
    if noun_is(noun, "HARN") and present(eng, HARNAS):
        pr(eng, 111)
        return
    # 0x33af: (HARN|VIZI) & inside the armour (room 54) -> the visor view, chosen by
    # the harnas's own location [0xca2].
    if (noun_is(noun, "HARN") or noun_is(noun, "VIZI")) and room == 54:
        hloc = loc(eng, HARNAS)
        if hloc == 21:                     # home (default): a random hall/forest view
            pr(eng, 225 + int(eng.rng.rnd(1.0) * 3.0))
        elif hloc == CARRIED:              # carried (EXE loc==-1): the 'foutje' line
            pr(eng, 275)
        elif hloc == 34:                   # kruiskamer side
            pr(eng, 273)
        else:                              # schatkamer side (loc 35) / elsewhere
            pr(eng, 274)
        return
    # 0x346f: TOUW present -> the rope description.
    if noun_is(noun, "TOUW") and present(eng, TOUW):
        pr(eng, 112)
        return
    # 0x3492: RAAM & room 29 -> a random moonlit-forest window view {219,220,221}.
    if noun_is(noun, "RAAM") and room == 29:
        pr(eng, 219 + int(eng.rng.rnd(1.0) * 3.0))
        return
    # 0x34d4: STEE & room 14 -> the INCORE-automatisering ad easter egg.
    if noun_is(noun, "STEE") and room == 14:
        pr(eng, 214)
        return
    # 0x3500: (VOET|SPOR) & room 17 -> the boot/animal prints.
    if (noun_is(noun, "VOET") or noun_is(noun, "SPOR")) and room == 17:
        pr(eng, 217)
        return
    # 0x353a: CIRK & room 2 -> the old-stove spot.
    if noun_is(noun, "CIRK") and room == 2:
        pr(eng, 208)
        return
    # 0x3566: (SCHA|KIST) & the schatkist (obj13, EXE index 14) present -> its contents.
    if (noun_is(noun, "SCHA") or noun_is(noun, "KIST")) and present(eng, SCHATKIST):
        pr(eng, 113)
        return
    # 0x35a4: KIST & room 2 -> the carved craftsmanship.
    if noun_is(noun, "KIST") and room == 2:
        pr(eng, 207)
        return
    # 0x35d0 (KEPT — BED): reveal the bedroom luik once you've slept.
    if noun_is(noun, "BED"):
        if room != 1:
            pr(eng, 114)                   # "Welk bed had je in gedachten ?"
        elif flag(eng, "e96") == 0:
            pr(eng, 115)
        else:
            eng.state["e86"] = 1
            pr(eng, 116)
        return
    # 0x3613: (KIST|DOOD) & standing in Dracula's closed-coffin room ([0xca4]=obj37).
    if (noun_is(noun, "KIST") or noun_is(noun, "DOOD")) and room == loc(eng, DOODSKIST):
        pr(eng, 245)
        return
    # 0x364f: (KIST|DOOD) & the opened coffin (obj38, EXE index 39) present.
    if (noun_is(noun, "KIST") or noun_is(noun, "DOOD")) and present(eng, DOODSKIST_OPEN):
        pr(eng, 246)
        return
    # 0x368d: (DEUR|VREE|SESA) & room 31 -> the strange 'DIT IS SESAM' door.
    if (noun_is(noun, "DEUR") or noun_is(noun, "VREE") or noun_is(noun, "SESA")) and room == 31:
        pr(eng, 283)
        return
    # 0x36d5: LUIK — the bedroom luik (room 1, revealed) or the tower-chest luik
    # (room 29 once the chest has advanced into a luik state, obj22/obj23 here).
    if noun_is(noun, "LUIK"):
        if room == 1 and flag(eng, "e86") == 1:
            pr(eng, 117)
            return
        if room == 29 and (loc(eng, KIST_LUIK_DICHT) == room or loc(eng, KIST_LUIK_OPEN) == room):
            pr(eng, 118)
            return
        # a LUIK that matches no sub-case falls through to the generic else.
    # 0x3741 (KEPT — TORE/GAT): viewing the castle tower from rm 51 ACTIVATES Dracula
    # (e72) and advances the tower chest (obj21->99, obj22->99, obj23->29 in room 29).
    if (noun_is(noun, "TORE") or noun_is(noun, "GAT")) and room == 51:
        if flag(eng, "e70") == 0 and flag(eng, "e72") == 0:
            eng.obj_loc[KIST_DICHT] = LOC_NOWHERE       # 0x3794 [0xc84]=99
            eng.obj_loc[KIST_LUIK_DICHT] = LOC_NOWHERE  # 0x379a [0xc86]=99
            eng.obj_loc[KIST_LUIK_OPEN] = 29            # 0x37a0 [0xc88]=29
            eng.state["e88"] = 1                        # 0x37a6
            eng.state["e72"] = 1                        # 0x37ac (Dracula becomes roaming)
            pr(eng, 119)
        else:
            pr(eng, 176)
        return
    # 0x37be: (EETK|ROOS|GAT) & room 52 -> the deterministic eetkamer spy-view.
    if (noun_is(noun, "EETK") or noun_is(noun, "ROOS") or noun_is(noun, "GAT")) and room == 52:
        pr(eng, 120)
        return
    # 0x3803 (generic else): re-resolve; an object present -> msg 121, else msg 122.
    if eng.resolve(noun) is not None:
        pr(eng, 121)
    else:
        pr(eng, 122)


# --- LEES  (EXE 0x3076) — read (BOEK/TEKS/BRIE/INSC, else -> BEKIJK) -------------
def lees(eng, cmd) -> None:
    """Read — faithful port of the standalone LEES handler EXE 0x3076 (verb LEES
    dispatched at 0xced -> jmp 0x3076). It handles the four readable nouns and then,
    for any other noun, jmps into the BEKIJK handler (0x315c -> jmp 0x32e6). The
    engine previously aliased lees->bekijk, silently dropping these reads."""
    noun = cmd.noun
    room = eng.room

    # 0x3076: BOEK — the vampire-handbook content (must be in hand).
    if noun_is(noun, "BOEK"):
        pr(eng, 91 if carried(eng, BOEK) else 90)
        return
    # 0x30a0: TEKS — room-23 cipher / room-20 castle sign / the book / nothing.
    if noun_is(noun, "TEKS"):
        if room == 23 and flag(eng, "df0") == 0:
            pr(eng, 94)
        elif room == 20:
            pr(eng, 216)
        elif present(eng, BOEK):
            pr(eng, 91)
        else:
            pr(eng, 92)
        return
    # 0x3110: BRIE — read the letter (the Spelregels/quest text) when it is present.
    if noun_is(noun, "BRIE"):
        pr(eng, 201 if present(eng, BRIEFJE) else 202)
        return
    # 0x3151: INSC — the latin inscription in room 2; elsewhere 'not here'.
    if noun_is(noun, "INSC"):
        if room == 2:
            pr(eng, 209)
        else:
            eng._not_here(noun)            # jmp 0x4c88
        return
    # 0x315c: any other noun -> fall through into the BEKIJK handler.
    bekijk(eng, cmd)


# --- SLAAP / RUST  (EXE 0x392a) — sleep ----------------------------------------
def slaap(eng, cmd) -> None:
    """Sleep. docs/verb-events.md §SLAAP (EXE 0x392a).

    Sleeping only works in the bedroom (room 1); anywhere else the ground is too
    hard (msg 123). In room 1 the outcome is a two-condition guard read verbatim
    from the disassembly (0x393d–0x3971):

        if (dee==1) OR (e96==1):  msg 124  "Je wordt 's morgens vroeg weer fit wakker."
        else:                     msg 125  "Je wordt midden in de nacht wakker door
                                            gerommel, dat vanonder het bed lijkt te
                                            komen." ; set [0xe96]=1   (0x396b)

    So the night-time discovery — the ONLY writer of [0xe96], which the already-wired
    BEKIJK BED reveal consumes to expose the luik — fires only when the castle door is
    shut (`[0xdee]==0`) and you have not slept-with-discovery before (`[0xe96]==0`).
    `[0xdee]` starts at 1 (castle door open) and is cleared to 0 by the room-20
    door-slam once Dracula is banished, so this is a genuine EXE gate, not a
    simplification (see the deviation note / docs)."""
    if eng.room != 1:
        pr(eng, 123)                       # "Je kunt hier moeilijk in slaap komen ..."
        return
    if flag(eng, "dee") == 1 or flag(eng, "e96") == 1:
        pr(eng, 124)                       # "Je wordt 's morgens vroeg weer fit wakker."
        return
    eng.state["e96"] = 1                    # the sleep-in-bed event (0x396b)
    pr(eng, 125)                           # "Je wordt midden in de nacht wakker door gerommel ..."


# --- LUISTER  (EXE 0x3a8c) — listen --------------------------------------------
def luister(eng, cmd) -> None:
    """Listen — faithful port of the standalone LUISTER handler EXE 0x3a8c (verb
    LUIST dispatched at 0x0d79 -> jmp 0x3a8c). The noun is IGNORED; the handler
    branches solely on the current room ([0xe2e]), in EXE order:

        room 31 (0x3a8c cmp 0x1f):  [0xe34]=0xdf (K=223) -> world[222]
                                    (the sesam-door pounding); no state change.
        room 13 (0x3a9f cmp 0xd):   the herberg two-men conversation. The counter
                                    [0xe9a] is incremented then clamped to 3
                                    (0x3ab2-0x3ac9); K = e9a+0x88 -> world[135+e9a]
                                    = 136/137/138 for the 1st/2nd/3rd+ listen.
        else (0x3aa9):              [0xe34]=0x88 (K=136) -> world[135]
                                    ('... absolute stilte ...'); no state change.

    [0xe9a] is written/read ONLY here (its two other disassembly refs are the
    BEWAAR/LAAD bulk flag-block save/load), so LUISTER is pure atmosphere and gates
    nothing else — not KOOP KNOFLOOK, VRAAG WAARD (e6e), nor the zolder access."""
    room = eng.room
    if room == 31:
        pr(eng, 222)                       # 0x3a96: the sesam-door pounding
        return
    if room != 13:
        pr(eng, 135)                       # 0x3aa9: "... absolute stilte ..."
        return
    # room 13: advance the two-men-conversation counter (inc, clamp at 3).
    c = min(flag(eng, "e9a") + 1, 3)
    eng.state["e9a"] = c
    pr(eng, 135 + c)                        # 136/137/138 (EXE K = c + 136)


# --- Dracula combat verbs  (docs/verb-events.md §4) ----------------------------
# These land the counter-blows that drive the combat counter e74. When a blow is
# decisive it sets e74 = -1; the DECISIVE RESOLUTION (banish: e70=1, dde=255, and
# the final-blow text) is applied by the end-of-turn routine 0x26d2, which is NOT
# yet ported (a separate RE item). So these handlers faithfully write e74 / object
# state; the visible banish appears once end-of-turn is wired.
def _dracula_here(eng) -> bool:
    return flag(eng, "dde") == eng.room


def _cant(eng) -> None:
    eng.io.writeln(eng.msg.named("cant"))


def schijn(eng, cmd) -> None:
    """SCHIJN / BESCHIJN — shine the lamp. Faithful port of EXE 0x4cc7."""
    # 0x4cc7: no lamp in hand -> the specific reminder, BEFORE any Dracula logic.
    if not carried(eng, LAMP):
        pr(eng, 175)                       # "Je hebt de lamp niet bij je!"
        return
    # 0x4cda: SCHIJN <not-Dracula> falls through into the examine handler.
    if not noun_is(cmd.noun, "DRAC"):
        bekijk(eng, cmd)
        return
    # 0x4ce8: Dracula named but not in this room -> "Dat gaat niet." (world[1]).
    if not _dracula_here(eng):
        _cant(eng)
        return
    # 0x4cfd: he has already been banished once -> the bored taunt.
    if flag(eng, "e70") != 0:
        pr(eng, 258)
        return
    # 0x4d10: the effective shine.
    if flag(eng, "e74") == 1:
        eng.state["e74"] = -1              # decisive counter-blow
    else:
        eng.state["e74"] = 0
        pr(eng, 174)


def _gooi_weapon(eng, noun: str | None):
    """The object slot GOOI resolves for a BIJL/KAPMES throw (EXE 0x4a1e-0x4a95):
    KAPM -> the kapmes (obj5); BIJL -> the sharp bijl (obj10) if carried, else the
    blunt bijl (obj28). Returns the carried object id, or None if none is in hand."""
    if noun_is(noun, "KAPM"):
        return KAPMES if carried(eng, KAPMES) else None
    # BIJL: prefer the sharp axe, else the blunt one (0x4a4a/0x4a5a).
    if carried(eng, BIJL_SCHERP):
        return BIJL_SCHERP
    if carried(eng, BOTTE_BIJL):
        return BOTTE_BIJL
    return None


def _gooi_waard(eng, cmd, oid: int) -> None:
    """GOOI BIJL|KAPMES at the innkeeper, room 12 (EXE waard branch 0x4a97).

    First hit (e84==0, 0x4ac0): SET e84=1, drop the thrown object into room 12, and
    print msg 190 (bijl) or msg 191 (kapmes; slot 6). Subsequent hits (e84!=0, 0x4aea):
    a random reaction K = 193 + INT(RND*3) with a +3 shift for the kapmes (EXE 0x4aea:
    ax=(kapmes?-1:0); bx=ax*3; K -= bx, i.e. +3 for the knife). So bijl -> {193,194,195}
    -> msgs 192/193/194 (axe lines) and kapmes/MES -> {196,197,198} -> msgs 195/196/197
    (knife lines). NO e84 change, NO death. (The EXE re-drop at 0x4b22 is gated on the
    impossible K==193 AND K==196, so it never fires — a thrown-again object stays in
    hand; that 0xc4==196 compare is the witness that the knife pool reaches K=196.)"""
    is_kapmes = noun_is(cmd.noun, "KAPM")   # slot 6 (obj5)
    if flag(eng, "e84") == 0:
        eng.state["e84"] = 1                # 0x4ac0: first hit sets the anger latch
        eng.obj_loc[oid] = eng.room        # 0x4ad2: the object lands in room 12
        pr(eng, 191 if is_kapmes else 190)  # K = 191 - (kapmes?-1:0) -> index 190/191
        return
    # subsequent hit: random flavor, no state change (0x4aea).
    k = 193 + int(eng.rng.random() * 3.0) + (3 if is_kapmes else 0)
    pr(eng, k - 1)


def gooi(eng, cmd) -> None:
    """GOOI / WERP — throw. §4 GOOI KNOF at Dracula (the combat counter-blow) plus the
    innkeeper (waard) throw branch (EXE 0x49af/0x4a97).

    Faithful for the three throwable weapons KAPM/BIJL/KNOF (EXE 0x49ec-0x4b5d):
      * BIJL/KAPM carried in room 12       -> the waard hit (0x4a97).
      * BIJL/KAPM carried elsewhere / KNOF -> the generic drop (0x4b54 -> 0x1f32),
        except GOOI KNOF at Dracula, which lands the combat counter-blow.
      * BIJL/KAPM not carried              -> generic drop (also 0x1f32).
      * KNOF not carried                   -> msg 84 (0x4a8e).
    Any other noun keeps the engine's generic 'Dat gaat niet.' (an out-of-scope
    simplification of the EXE's throw-drops-anything else-branch)."""
    noun = cmd.noun
    # GOOI KNOF at Dracula once his coffin is open (e76!=0) -> garlic is useless now
    # (EXE 0x4b84). In the endgame you must use the cross + stake, not garlic.
    if noun_is(noun, "KNOF") and carried(eng, KNOFLOOK) and _dracula_here(eng) \
            and flag(eng, "e76") != 0:
        pr(eng, 258)
        return
    # GOOI KNOF at Dracula — the combat counter-blow (the EXE dracula-throw path).
    if (noun_is(noun, "KNOF") and carried(eng, KNOFLOOK)
            and _dracula_here(eng) and flag(eng, "e70") != 1):
        if flag(eng, "e74") == 1:
            eng.state["e74"] = -1          # decisive counter-blow
        else:
            eng.state["e74"] = 0
            pr(eng, 173)
        return
    # GOOI KNOF at Dracula after the mid-game banish (e70==1) but before his coffin is
    # opened (e76==0) -> the attack is useless (EXE 0x4bce, msg 150). Rare: he normally
    # leaves once banished, so this only fires if he is somehow present again.
    if noun_is(noun, "KNOF") and carried(eng, KNOFLOOK) and _dracula_here(eng):
        pr(eng, 150)
        return
    # BIJL / KAPMES: resolve the carried weapon; in room 12 it hits the waard, else it
    # simply drops (the slot!=4 waard-hit condition 0x4a97 only holds in room 12).
    if noun_is(noun, "BIJL") or noun_is(noun, "KAPM"):
        oid = _gooi_weapon(eng, noun)
        if oid is None:
            leg(eng, cmd)                  # not carried -> generic drop (0x1f32)
        elif eng.room == 12:
            _gooi_waard(eng, cmd, oid)     # the waard hit
        else:
            leg(eng, cmd)                  # carried but not at the waard -> generic drop
        return
    # KNOF (slot 4) never hits the waard: carried -> generic drop; absent -> msg 84.
    if noun_is(noun, "KNOF"):
        if carried(eng, KNOFLOOK):
            leg(eng, cmd)                  # generic drop (0x4b54 -> 0x1f32)
        else:
            pr(eng, 84)                    # 0x4a8e: "Je hebt het niet eens bij je."
        return
    # Any other noun (incl. FLES) -> the LEG drop handler. Faithful to the EXE default
    # 0x4a1b `jmp 0x1f32`: GOOI of a non-weapon just drops it (and GOOI FLES thus runs
    # the exact break + spider-kill tail of `leg`). Empty/absent nouns land on leg's
    # own row-1/row-3 replies, as the re-entered resolver 0x3822 dictates.
    leg(eng, cmd)


def dood(eng, cmd) -> None:
    """DOOD / VERMO / LIQUI — the EXE KILL handler (0x3c2c), distinct from the SLA
    hit handler (0x3afe). Only the innkeeper (waard) branch is ported faithfully:

    DOOD WAARD, room 12 (0x3c74/0x3c9b): INCREMENT e84; then a random reaction
        K = INT(RND*5) + 141  (base [0x1736]=141, mult [0x1414]=5.0 — the same idiom
        as do_vloek's base 155). Print world.messages[K-1] (msgs 140..144). If the
        computed K == 143 (msg 142) it is the KNIFE DEATH -> game over. (The 20%
        second-RND object-scatter at 0x4e21 is deferred, as elsewhere.)

    DOOD DRACULA (0x3ce5): Dracula absent (room != dde, 0x3cf3) -> msg 145 "Die is
        hier niet."; Dracula present (0x3d08) -> a random taunt K = INT(RND*2) + 172
        (base [0x173a]=172.0) -> msgs 171/172. Pure flavour, no state change (unlike
        SLA DRAC 0x3b86 which gives the single msg 170).

    Any other kill target falls back to the SLA hit handler — a pending-port
    approximation for the handler's spider branch (see deviations)."""
    noun = cmd.noun
    if noun_is(noun, "WAAR") and eng.room == 12:
        eng.state["e84"] = flag(eng, "e84") + 1     # 0x3c9b
        k = int(eng.rng.random() * 5.0) + 141        # 0x3cad
        pr(eng, k - 1)
        if k == 143:                                 # 0x3cba -> 0x3ed3
            eng.dead = True
        return
    if noun_is(noun, "DRAC"):                        # 0x3ce5: DOOD DRACULA
        if not _dracula_here(eng):
            pr(eng, 145)                             # 0x3cf3: "Die is hier niet."
        else:
            k = int(eng.rng.random() * 2.0) + 172    # 0x3d08: INT(RND*2)+172
            pr(eng, k - 1)                           # msgs 171 / 172
        return
    sla(eng, cmd)


def toon(eng, cmd) -> None:
    """SHOW / TOON / HOUDT — show. Faithful port of EXE 0x4ebc."""
    noun = cmd.noun
    # 0x4eec else: not the cross, or not room 24, or Dracula absent -> "Er gebeurt niets."
    if not (noun_is(noun, "KRUI") and eng.room == 24 and _dracula_here(eng)):
        pr(eng, 259)
        return
    # 0x4ef5: the cross must be in hand ([0xc6c]==-1), else world[23].
    if not carried(eng, KRUIS):
        pr(eng, 23)                        # "Dat heb je helemaal niet bij je."
        return
    eng.state["e74"] = 0                   # drives him back, buys a turn
    pr(eng, 260)


def sla(eng, cmd) -> None:
    """DOOD / SLA / STOMP / SCHOP / TRAP — hit. §4 SLA WIG (the stake, EXE 0x3afe),
    plus the ineffective direct attack on Dracula and the spider dodge."""
    noun = cmd.noun
    # SLA/DOOD the kruisspin in its room -> it dodges (EXE 0x3b3d / dood 0x3c6b). obj34
    # carries no tokens; the EXE matches by hardcoded SPIN / KRUISS(pin).
    if (noun_is(noun, "SPIN") or noun_is(noun, "KRUISS")) and eng.room == loc(eng, SPIN):
        pr(eng, 272)
        return
    if (noun_is(noun, "WIG") or noun_is(noun, "PIN")) and eng.room == 24 and _dracula_here(eng):
        if not carried(eng, HAMER):
            pr(eng, 261)                   # "Je hebt geen hamer."
            return
        if not carried(eng, WIG):
            pr(eng, 262)
            return
        if flag(eng, "e74") > 1:
            pr(eng, 263)                   # EXE 0x3c01: still aggressive (e74>1) -> can't
            return
        # e74<=1: Dracula has been CALMED (TOON KRUIS drives him to e74=0) -> the stake
        # through the heart lands (0x3c14: e74=-1, wig consumed).
        eng.state["e74"] = -1
        eng.obj_loc[WIG] = LOC_NOWHERE
        return
    if noun_is(noun, "DRAC"):
        pr(eng, 170 if _dracula_here(eng) else 145)   # direct attacks are useless
        return
    _cant(eng)


# --- Room-31 secret-word password  (EXE 0x4f17 + dispatcher 0x084a) -------------
# The secret is generated DETERMINISTICALLY at startup (0x029e -> 0x500a) into the
# string variable [0xe30] — dynamic string memory, empty in the EXE file, so not
# statically extractable. Recovered via the DOS-oracle read of the running game:
# the word is "incoronium". It is revealed in the dust when Dracula is staked
# (0x4de7), and the dispatcher opens the door when the player types it in room 31.
# The Dutch defaults for the secret word and its dust-reveal framing now live in the
# externalised lexicon (engine/data/strings_nl.json: `secret` and ui.REVEAL_SECRET —
# the latter's four lines are EXE DGROUP constants 0x1856/0x1892/0x18be/0x18ca/0x190c,
# NOT DRACULA.TXT messages). The running engine reads its per-World copy (eng.lex) so a
# translation applies; this module constant is the nl default for direct callers.
SECRET_WORD = _DEFAULT_LEXICON.secret


def reveal_secret(eng) -> None:
    """Port of EXE 0x4de7: the Dracula-defeat message, then the dust that spells out
    the room-31 secret word. Called from the end-of-turn room-24 defeat branch."""
    pr(eng, 264)
    eng.io.writeln(eng.lex.ui("REVEAL_SECRET").format(word=eng.lex.secret))


def is_secret(cmd, secret: str = SECRET_WORD) -> bool:
    """True when the typed line contains the secret word. The EXE compares [0xe30]
    against a typed word slot ([0xe18]) via B$SCMP; we accept the word anywhere in
    the (already upper-cased) input line so it works however the player phrases it.
    ``secret`` defaults to the Dutch word but the engine passes eng.lex.secret so a
    translation's secret is honoured."""
    return secret.upper() in (cmd.raw or "").upper().split()


def room31_password(eng, cmd) -> None:
    """Port of EXE 0x4f17 — the player speaks the secret word in room 31."""
    if flag(eng, "dde") != 257:
        pr(eng, 265)                       # Dracula not yet defeated -> the room stays silent
        return
    pr(eng, 266)                           # "Een zware slag en de deur piept en knarst…"
    eng.state["e48"] = 1                   # open the sesam door (rm 31 -> 34)
    eng.obj_loc[DEUR_OPEN] = 31            # place obj39 "De vreemd gevormde deur is nu open"
