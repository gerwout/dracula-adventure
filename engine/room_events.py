"""Describe-time room-entry events — a faithful port of DRACULA.EXE routine 0x2399.

The original describe routine (`0x4f40`) does three things in order:

    call 0x5446   ; print the room's static text (DRACULA.TXT room record + chain)
    call 0x2399   ; ROOM-ENTRY EVENTS  <-- this module
    <loop>        ; list the objects present ("Er is een <x> hier." / …)

`0x2399` is a single top-to-bottom fall-through chain (offsets 0x2399–0x269d) evaluated
on EVERY room describe; several blocks may fire for one room (e.g. room 37 prints two
lines, room 20 prints the door status then possibly the slam line). We mirror that chain
block-for-block in `run_room_events`.

Message indices are **world.messages indices**, already corrected for the EXE off-by-one
(EXE `[0xe34]=K` prints `world.messages[K-1]`; see docs/message-dispatch.md).

Two blocks are RANDOM: the "bird" ambient (rooms 7–11, fires when `RND > 1.6`, ≈20%) and
the Dracula spawn (castle-upper rooms, fires when `RND ≤ 0.6`, ≈30%). BASRUN's `RND` is a
24-bit LCG uniform on **[0, 2)** (multiplier 0x43FD; see docs/room-events-analysis.md and
docs/rng.md). They take their random draw from the injected `rng` (see `Rng`).

Full derivation — the three runtime routines, the DGROUP float constants (0x1632=1.6,
0x1636=0.6), the computed rooms-20/21 door formula and the room-32 gate — is in
docs/room-events-analysis.md. Flag initial values / setters are in docs/flag-semantics.md.
"""
from __future__ import annotations

from typing import Protocol


class Rng(Protocol):
    """A BASRUN-compatible RND source: returns the next value, uniform on [0, 2)."""
    def rnd(self) -> float: ...


class NullRng:
    """Placeholder RND for tests/deterministic checks. Returns a fixed value in
    (0.3, 0.8] so neither random describe-event fires (bird needs RND>0.8, Dracula
    spawn needs RND<=0.3) — the quiet, most-common outcome. NOT faithful to any seed;
    the engine uses the real BASRUN RND (engine/rng.py) for play."""
    def rnd(self) -> float:
        return 0.5


# DGROUP describe-flag initial values (docs/flag-semantics.md). Every flag the 0x2399
# chain reads defaults to the BASIC scalar 0, EXCEPT these three set in the init prologue.
FLAG_DEFAULTS: dict[str, int] = {
    "e3e": 0,   # ladder placed for room-0 ceiling gat (0=no, 1=yes)
    "e40": 0,   # ladder present in room 30
    "e44": 0,   # iron gate open (room 32/37)
    "e6c": 0,   # reveal latch set on visiting room 28 -> enables room-11 well line
    "e6e": 0,   # reveal latch -> enables room-12 attic-stairs line
    "e70": 0,   # Dracula-has-appeared/attacked latch
    "e72": 0,   # Dracula-eligible precondition (must be !=0 to spawn)
    "e74": 0,   # Dracula combat phase
    "e76": 0,   # Dracula blocking-state flag (selects the msg-49 path)
    "dee": 1,   # castle door open (rooms 20/21): 1=open (init), 0=closed
    "df0": 1,   # room-23 exit door open: 1=open (init)
    "dde": 255,  # Dracula's current room, 255 = absent (init)
    # Door/gate flags used by named-navigation guards (docs/named-navigation.json).
    "e3c": 0,   # window rooms 0<->6: 0 = passable (init), nonzero = closed
    "e42": 0,   # grave/graftombe access (rooms 39<->37) opened
    "e46": 0,   # castle-bedroom door (rooms 22<->24) open
    "e48": 0,   # sesam/kruiskamer door (room 31->34) open
    # State flags written by the verb-event handlers (docs/verb-events.md §2). All
    # init 0; only their describe/nav consumers already lived above. The engine's
    # verb_events module both reads and writes these.
    "e66": 0,   # coin thrown into the well (room 16)
    "e84": 0,   # innkeeper (waard) anger counter (room 12)
    "e86": 0,   # bedroom luik revealed (room 1, after sleeping + BEKIJK BED)
    "e88": 0,   # bedroom luik open (rooms 1<->4) / tower viewed
    "e8c": 0,   # wooden doos opened (drops the hamer)
    "e92": 0,   # rope tied to the balcony (room 25)
    "e96": 0,   # slept in the bed (room 1)
    "e9a": 0,   # herberg two-men-conversation counter (room 13, LUISTER; 1..3)
    "df6": 0,   # player poisoned (drank the blue water)
    # End-of-turn routine state (docs/end-of-turn.md, EXE 0x269e).
    "e7a": 0,   # spider-room proximity timer (room 34)
    "e78": 0,   # scratch: was Dracula in your room this turn (patrol print gate)
    "de0": 255,  # room Dracula stepped away from this turn (patrol bookkeeping); EXE
                 # inits [0xde0]=0xff @0x27c (255=none) — the VOLG-follow guard (de0==room)
                 # must never hold until the patrol sets it, else follow -> rooms[255].
}

# RND thresholds (DGROUP MBF float constants 0x1632 / 0x1636, bias-129 decoded).
# RND is uniform on [0,1) (see engine/rng.py), so these give P 0.20 / 0.30.
_BIRD_THRESHOLD = 0.8     # block #4 fires when RND > 0.8   (const [0x1632])
_SPAWN_THRESHOLD = 0.3    # block #10 fires when RND <= 0.3 (const [0x1636])


def run_room_events(room: int, state: dict, world, io, rng: Rng | None = None) -> None:
    """Emit the describe-time room-entry events for `room`, in EXE fall-through order,
    mutating `state` exactly as routine 0x2399 mutates its DGROUP flags.

    `state` is the engine's integer DGROUP-flag map (see FLAG_DEFAULTS). `rng` supplies
    the two random blocks (defaults to NullRng, i.e. neither random block fires).
    """
    if rng is None:
        rng = NullRng()

    def pr(idx: int) -> None:
        if idx in world.messages:
            io.writeln(world.message_text(idx))

    def flag(name: str) -> int:
        return state.get(name, FLAG_DEFAULTS.get(name, 0))

    # #1/#2 (0x2399/0x23b7) room 0 ceiling gat.
    if room == 0:
        if flag("e3e") == 0:
            pr(39)                     # "…maar je kunt het niet bereiken." (+RET)
            return
        pr(40)                         # "Via een ladder kan je naar boven klimmen."

    # #3 (0x23fe) rooms 20/21 castle-door status — computed K = 2*(1-dee)+room+22.
    if room in (20, 21):
        k = 2 * (1 - flag("dee")) + room + 22
        pr(k - 1)

    # #4 (0x2415) random ambient. The RND draw at 0x2430 is UNCONDITIONAL: every
    # describe that reaches this block advances the shared RND stream (only room 0
    # with no ladder RET'd earlier, at #1). The room 7-11 test merely gates whether
    # the "vogel fluiten" line prints. So describing ANY room here consumes one RND.
    if rng.rnd() > _BIRD_THRESHOLD and 7 <= room <= 11:
        pr(45)                         # "In de verte hoor je een vogel fluiten."

    # #5 (0x2451) room 28 sets the room-11 reveal latch.
    if room == 28:
        state["e6c"] = 1

    # #6 (0x2461) room 30 long ladder.
    if room == 30 and flag("e40") == 1:
        pr(223)

    # #7 (0x2489) room 11 well — gated by the room-28 latch.
    if room == 11 and flag("e6c") == 1:
        pr(46)                         # "Ver in het bos kan je een bron zien."

    # #8 (0x24b1) room 12 attic stairs — gated by e6e.
    if room == 12 and flag("e6e") == 1:
        pr(47)

    # #9 (0x24d9) room 20 door slams shut once Dracula is banished and the door is open.
    if room == 20 and flag("e70") == 1 and flag("dee") != 0:
        pr(48)                         # "Plotseling beweegt de deur en slaat … dicht."
        state["dee"] = 0

    # #10 (0x2535) Dracula spawn: castle-upper rooms, RND <= 0.6 (≈30%), no message.
    # As with the bird, the RND draw at 0x2595 is UNCONDITIONAL (the eligibility mask
    # is computed first, then RND is drawn, then combined) — so every non-RET describe
    # consumes a SECOND RND here. Only the eligibility + RND<=0.6 gate the spawn.
    spawn_roll = rng.rnd()
    if (room >= 21 and room not in (26, 39) and room != flag("dde")
            and flag("e70") != 1 and flag("dee") != 0 and flag("e72") != 0
            and spawn_roll <= _SPAWN_THRESHOLD):
        state["dde"] = room
        state["e74"] = 2

    # #11/#12 (0x25b9/0x25ee) Dracula present -> "blokkeert alle uitgangen."
    if room == 24 and room == flag("dde") and flag("e76") == 1:
        pr(49)
    if room == flag("dde") and flag("e76") == 0:
        pr(49)

    # #13 (0x2618) room 32 iron gate.
    if room == 32:
        pr(50 if flag("e44") == 1 else 51)

    # #14 (0x2648/0x265b) room 37 iron gate — always msgs[52], + msgs[53] when closed.
    if room == 37:
        pr(52)
        if flag("e44") != 1:
            pr(53)

    # #15 (0x2664) room 23 exit door.
    if room == 23:
        pr(54 if flag("df0") == 1 else 55)

    # #16 (0x268d) room 40 opens the room-23 door, then RET.
    if room == 40:
        state["df0"] = 1
        return
