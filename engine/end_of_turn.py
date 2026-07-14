"""End-of-turn events — faithful port of DRACULA.EXE routine 0x269e.

The main loop calls this once after every command (EXE `0x030e: call 0x269e`),
then checks the death flag. It runs a linear fall-through of gated blocks:

  A. Dracula in your room (`room==dde & e70!=1`): land the counter-blow (`e74<0`
     → banish) or the combat counter escalates.
  B. Dracula patrol (`e76!=0 & dde!=24`): he steps one room 37→32→31→30→22→24;
     OR the room-24 confrontation (`room==24 & dde==24 & e76!=0`): defeat / escalate
     / death.
  C. Spider room (34): a proximity timer that warns then kills.
  D. Treasure win: carrying the schatkist into room 11 ends the game a winner.

Deaths set `eng.dead`; the win sets `eng.won` (the Engine ends the game on either).
Message indices are `world.messages` indices (the EXE `[0xe34]=K → messages[K-1]`
off-by-one is already applied). See docs/end-of-turn.md for the full disassembly.

Stub until the tests below it are green (TDD).
"""
from __future__ import annotations

from .data.model import CARRIED
from . import verb_events

SCHATKIST = 13          # obj13, the schatkist ([0xc74]); carried == the treasure win
SPIN = 34               # obj34, the spider ([0xc9e]); its room drives the spider timer


def _cint(x: float) -> int:
    """QuickBASIC CINT — round to nearest, ties to even (banker's rounding), the
    semantics of the BASRUN fn 0x53 the computed-message formula ends with. Python's
    round() already implements round-half-to-even, so this is a thin, named wrapper."""
    return round(x)

# Dracula's one-step patrol path (EXE 0x2768): dde value -> (new dde, message index).
# He walks 37→32→31→30→22→24, one room per turn; the extra effects are handled inline.
_PATROL = {
    37: (32, 253),      # 0x27ff: also opens the iron gate (e44)
    32: (31, 252),      # 0x27e3
    31: (30, 251),      # 0x27c7
    30: (22, 250),      # 0x27ab
    22: (24, 249),      # 0x2783: also arms the bedroom door (e46) and resets e74=2
}


def run_end_of_turn(eng) -> None:
    """Port of EXE 0x269e — run once after each command; may set eng.dead/eng.won."""
    st = eng.state

    def flag(name):
        return st.get(name, 0)

    def pr(idx):
        if idx in eng.world.messages:
            eng.io.writeln(eng.world.message_text(idx))

    room = eng.room

    # --- Block A (0x26a4): you are standing in Dracula's room, not yet safe. -----
    if room == flag("dde") and flag("e70") != 1:
        if flag("e74") < 0:                       # counter-blow landed -> banish
            st["e70"] = 1
            st["dde"] = 255
            pr(149)
        elif flag("e74") == 5:                    # 0x26ea: computed Dracula-approach line
            # [0xe34] = CINT(RND*1 + 148.0) -> world.messages[[0xe34]-1] = messages[147]
            # or [148] ('Dracula komt langzaam dichterbij' / '...begint te lachen').
            # The DGROUP const 0x163a is MBF 148.0 — a message-index BASE, NOT 296 K
            # (the old temperature reading was a bias-128 decode error). NON-fatal.
            idx = _cint(148.0 + eng.rng.random())
            pr(idx - 1)
            st["e74"] = flag("e74") + 1           # 0x2742: escalate to phase 6
        elif flag("e74") == 6:                    # 0x2714: computed Dracula-attack -> DEATH
            # [0xe34] = CINT(RND*1 + 152.0) -> messages[151] or [152] (the neck-bite
            # collapse, the death climax). 0x163e is MBF 152.0. Sets [0xdf6]=-1 (death).
            idx = _cint(152.0 + eng.rng.random())
            pr(idx - 1)
            eng.dead = True
        else:
            # e74 in {0,1,2,3,4}: escalate one phase (2->3->4->5), no message.
            st["e74"] = flag("e74") + 1

    # --- Block B (0x2749): patrol OR the room-24 confrontation. -----------------
    if flag("e76") != 0 and flag("dde") != 24:
        # Patrol (0x2768): Dracula steps one room closer; print only if you see him.
        seen = room == flag("dde")
        step = _PATROL.get(flag("dde"))
        if step is not None:
            new_dde, msg = step
            came_from = flag("dde")
            st["dde"] = new_dde
            st["de0"] = came_from
            if came_from == 37:
                st["e44"] = 1                     # 0x2815: opens the iron gate
            if came_from == 22:
                st["e46"] = -1                    # 0x279f: arms the bedroom door
                st["e74"] = 2                     # 0x2799: (re)start combat at phase 2
            if seen:
                pr(msg)
    elif room == 24 and flag("dde") == 24 and flag("e76") != 0:
        # Room-24 confrontation (0x285e).
        if flag("e74") < 0:                       # decisive stake -> Dracula defeated
            st["dde"] = 257
            st["e76"] = 0
            verb_events.reveal_secret(eng)        # 0x4de7: defeat message + dust reveal
                                                  # of the room-31 secret word ("incoronium")
        elif flag("e74") == 3:
            pr(254)
            st["e74"] = 4
        elif flag("e74") == 4:
            pr(255)
            st["e74"] = 5                         # (0x4e21 object-scatter deferred)
        elif flag("e74") == 7:
            pr(256)
            eng.dead = True
        else:
            st["e74"] = flag("e74") + 1

    # --- Block C (0x28d2): the spider's room (34, or wherever the spider is). ----
    if room == 34 or room == eng.obj_loc.get(SPIN):
        if flag("e7a") > 3:
            pr(269)
            eng.dead = True
        elif flag("e7a") == 2:
            pr(270)
            st["e7a"] = 3
        else:
            st["e7a"] = flag("e7a") + 1

    # --- Block D (0x2929): carry the schatkist home (room 11) -> you win. --------
    if room == 11 and eng.obj_loc.get(SCHATKIST) == CARRIED:
        pr(281)
        eng.won = True                            # (0x2948 scoring loop deferred)
