"""Verb state-change events (the puzzle state machine) — faithful port of the
per-verb handlers documented in docs/verb-events.md.

Every test drives the public Engine API (eng.submit / describe) and asserts on the
observable output plus the DGROUP flag / object-location state the original mutates.
Expected message strings are read from the loaded world (the gitignored original
data), never hardcoded, so no copyrighted game text lives in the repo.

Object location convention in the engine (see engine/game.py): CARRIED == 200,
a room number == lies in that room, LOC_NOWHERE == 99 == consumed/removed. The EXE
uses -1 for "carried"; verb_events translates it to CARRIED.
"""
from engine.data.loader import load_file
from engine.game import CARRIED, Engine
from engine.data.model import LOC_NOWHERE
from engine.io import ScriptedIO
from engine.messages import EXE
from engine.parser import parse_line

# Object loader-indices (verified against the live object table, docs/verb-events.md §1).
LAMP, TOUW, WIG, KNOFLOOK, BOEK, KAPMES, LADDER = 0, 1, 2, 3, 4, 5, 6
HOUT, KRUIS, BIJL_SCHERP = 7, 9, 10
SCHATKIST, BROOD, MUNT, MELK, LEGE_FLES, WATER = 13, 14, 15, 16, 17, 18
BED, KIST_DICHT, KIST_LUIK_DICHT, KIST_LUIK_OPEN = 20, 21, 22, 23
KIST_STOF, KIST_BOEK, SCHERVEN, BOTTE_BIJL, SCHEP = 24, 25, 27, 28, 29
DOOS, HAMER, GIF_FLES, SPIN, BRIEFJE, HARNAS = 31, 32, 33, 34, 35, 36
DOODSKIST, DOODSKIST_OPEN, DODE_SPIN = 37, 38, 40


def _engine(room: int, carrying=(), placed=None):
    """Fresh engine in `room`, with the given object ids carried and optional
    {obj_id: location} overrides applied to the initial object-location map."""
    world = load_file()
    eng = Engine(world, ScriptedIO([]))
    eng.room = room
    for oid in carrying:
        eng.obj_loc[oid] = CARRIED
    for oid, loc in (placed or {}).items():
        eng.obj_loc[oid] = loc
    return eng, world


def _run(eng, line: str) -> str:
    # Dispatch the verb(s) in isolation, WITHOUT the end-of-turn routine that
    # Engine.submit() runs after each command — these are verb-unit tests; the
    # end-of-turn interaction is covered in tests/unit/test_end_of_turn.py.
    eng.io = ScriptedIO([])
    for cmd in parse_line(line):
        eng.dispatch(cmd)
    return eng.io.text


# --------------------------------------------------------------- LEG / ZET / DROP
def test_leg_ladder_room0_sets_e3e_and_becomes_fixture():
    # docs/verb-events.md §LEG row 5: LEG LADD @ rm 0 -> e3e=1, ladder loc=99, msg 25.
    eng, w = _engine(0, carrying=[LADDER])
    out = _run(eng, "leg ladder")
    assert eng.state["e3e"] == 1
    assert eng.obj_loc[LADDER] == LOC_NOWHERE
    assert w.message_text(25) in out


def test_leg_ladder_room30_sets_e40():
    # §LEG row 7: LEG LADD @ rm 30 -> e40=1, ladder loc=99, msg 27.
    eng, w = _engine(30, carrying=[LADDER])
    out = _run(eng, "leg ladder")
    assert eng.state["e40"] == 1
    assert eng.obj_loc[LADDER] == LOC_NOWHERE
    assert w.message_text(27) in out


def test_leg_munt_room16_sets_e66():
    # §LEG row 6: LEG MUNT @ rm 16 -> e66=1, msg 26.
    eng, w = _engine(16, carrying=[MUNT])
    out = _run(eng, "leg munt")
    assert eng.state["e66"] == 1
    assert w.message_text(26) in out


def test_leg_not_carrying_is_rejected():
    # §LEG row 3: dropping something you don't hold -> msg 23, no state change.
    eng, w = _engine(0)                       # ladder still in its start room (36)
    out = _run(eng, "leg ladder")
    assert w.message_text(23) in out
    assert eng.state["e3e"] == 0


def test_leg_generic_drop_still_works():
    # §LEG row 8 (else): a carried object with no special rule drops into the room.
    eng, w = _engine(2, carrying=[BROOD])
    out = _run(eng, "leg brood")
    assert eng.obj_loc[BROOD] == 2
    assert w.objects[BROOD].display_name in out
    assert "laten vallen" in out


# --------------------------------------------- LEG/GOOI FLES: break + spider kill
# EXE 0x1f88-0x1fdf (FLES tail of the LEG handler, reached by LEG FLES and GOOI FLES).
# Breaking ANY carried FLES: obj->99, scherven obj27->room, msg 24. If the broken
# bottle is the blue-poison GIF_FLES (obj33) AND the room holds the spider (obj34,
# loc-var [0xc9e], start room 34) -> spider obj34->99, dead-spider obj40->room, msg 271.
def test_leg_fles_poison_kills_spider():
    # LEG FLES with the poison bottle, standing in the spider's room (34) -> break AND
    # kill: msg 24 then msg 271, bottle+spider consumed, scherven+dead-spider placed.
    eng, w = _engine(34, carrying=[GIF_FLES])
    assert eng.obj_loc[SPIN] == 34            # spider starts in the kruiskamer
    out = _run(eng, "leg fles")
    assert eng.obj_loc[GIF_FLES] == LOC_NOWHERE
    assert eng.obj_loc[SCHERVEN] == 34
    assert eng.obj_loc[SPIN] == LOC_NOWHERE
    assert eng.obj_loc[DODE_SPIN] == 34
    assert w.message_text(24) in out
    assert w.message_text(271) in out
    # order: the bottle breaks (24) BEFORE the spider dies (271).
    assert out.index(w.message_text(24)) < out.index(w.message_text(271))


def test_gooi_fles_poison_kills_spider():
    # GOOI FLES routes through the same LEG FLES tail (EXE 0x4a1b jmp 0x1f32) -> identical.
    eng, w = _engine(34, carrying=[GIF_FLES])
    out = _run(eng, "gooi fles")
    assert eng.obj_loc[GIF_FLES] == LOC_NOWHERE
    assert eng.obj_loc[SCHERVEN] == 34
    assert eng.obj_loc[SPIN] == LOC_NOWHERE
    assert eng.obj_loc[DODE_SPIN] == 34
    assert w.message_text(24) in out
    assert w.message_text(271) in out


def test_leg_fles_poison_wrong_room_only_breaks():
    # The poison bottle broken away from the spider still shatters (msg 24) but leaves
    # the spider (still in room 34) alive: no msg 271, obj34 untouched, obj40 absent.
    eng, w = _engine(16, carrying=[GIF_FLES])   # room 16, spider stays in 34
    out = _run(eng, "leg fles")
    assert eng.obj_loc[GIF_FLES] == LOC_NOWHERE
    assert eng.obj_loc[SCHERVEN] == 16
    assert eng.obj_loc[SPIN] == 34              # spider survives
    assert eng.obj_loc[DODE_SPIN] == LOC_NOWHERE
    assert w.message_text(24) in out
    assert w.message_text(271) not in out


def test_leg_fles_nonpoison_in_spider_room_only_breaks():
    # A NON-poison FLES (plain water obj18) broken in the spider's room breaks (msg 24)
    # but does NOT kill the spider (guard is oid==GIF_FLES): no msg 271.
    eng, w = _engine(34, carrying=[WATER])
    out = _run(eng, "leg fles")
    assert eng.obj_loc[WATER] == LOC_NOWHERE
    assert eng.obj_loc[SCHERVEN] == 34
    assert eng.obj_loc[SPIN] == 34              # spider survives
    assert eng.obj_loc[DODE_SPIN] == LOC_NOWHERE
    assert w.message_text(24) in out
    assert w.message_text(271) not in out


def test_gooi_fles_not_carried_is_rejected():
    # GOOI FLES with no bottle in hand re-runs the LEG resolver -> msg 23, no break.
    eng, w = _engine(34)
    out = _run(eng, "gooi fles")
    assert eng.obj_loc[SCHERVEN] == LOC_NOWHERE   # nothing broke
    assert eng.obj_loc[SPIN] == 34                # spider untouched
    assert w.message_text(23) in out


def test_gooi_generic_noun_drops_faithful_to_jmp_1f32():
    # EXE GOOI default (non-KAPM/BIJL/KNOF) is `jmp 0x1f32` -> the LEG drop. A carried
    # ordinary object thrown just drops into the room (not the old 'Dat gaat niet.').
    eng, w = _engine(2, carrying=[BROOD])
    out = _run(eng, "gooi brood")
    assert eng.obj_loc[BROOD] == 2
    assert "laten vallen" in out


# ------------------------------------------------------ PAK / GRIJP / NEEM / RAAP
def test_pak_empty_noun():
    # §PAK row 1: "pak" with no noun -> msg 199.
    eng, w = _engine(0)
    assert w.message_text(199) in _run(eng, "pak")


def test_pak_ladder_room0_clears_e3e():
    # §PAK row 6: picking the ladder back up in rm 0 clears e3e and re-carries it.
    eng, w = _engine(0, placed={LADDER: LOC_NOWHERE})
    eng.state["e3e"] = 1
    out = _run(eng, "pak ladder")
    assert eng.state["e3e"] == 0
    assert eng.obj_loc[LADDER] == CARRIED
    assert EXE.OK in out


def test_pak_ladder_room30_clears_e40():
    # §PAK row 7: same for the long ladder in rm 30.
    eng, w = _engine(30, placed={LADDER: LOC_NOWHERE})
    eng.state["e40"] = 1
    out = _run(eng, "pak ladder")
    assert eng.state["e40"] == 0
    assert eng.obj_loc[LADDER] == CARRIED


def test_pak_bed_room1_is_refused():
    # §PAK row 4: BED @ rm 1 -> msg 204, nothing taken.
    eng, w = _engine(1)
    assert w.message_text(204) in _run(eng, "pak bed")


def test_pak_zand_room0_blows_away():
    # §PAK row 8: ZAND/STOF @ rm 0 -> msg 229.
    eng, w = _engine(0)
    assert w.message_text(229) in _run(eng, "pak zand")


def test_pak_kist_immovable_rooms():
    # §PAK row 10: KIST @ rm in {2,14,29} -> msg 21 ("niet te tillen").
    for room in (2, 14, 29):
        eng, w = _engine(room)
        assert w.message_text(21) in _run(eng, "pak kist"), room


def test_pak_doodskist_too_heavy():
    # §PAK row 12: KIST/DOOD in Dracula's coffin room ([0xca4]=obj37 loc, init 37).
    eng, w = _engine(37)
    assert eng.obj_loc[DOODSKIST] == 37
    assert w.message_text(236) in _run(eng, "pak kist")


def test_pak_scherven_hurts():
    # §PAK row 5: SCHERV where the shards lie ([0xc90]=obj27 loc) -> msg 248.
    eng, w = _engine(9, placed={SCHERVEN: 9})
    assert w.message_text(248) in _run(eng, "pak scherven")


def test_pak_generic_take_preserved():
    # §PAK row 13 (else): a present, takeable object is picked up. A single take prints
    # "Ok" (EXE 0x1e17); "<name> : gepakt." is the PAK ALLE per-item line only.
    eng, w = _engine(1)                       # lantern (obj0) starts in room 1
    out = _run(eng, "pak lantaarn")
    assert eng.obj_loc[LAMP] == CARRIED
    assert out.strip() == "Ok"


def test_pak_absent_object_preserved():
    # generic "not here" path is preserved for a noun that matches no visible object.
    eng, w = _engine(0)
    assert "Ik zie geen zwaard hier." in _run(eng, "pak zwaard")


# ------------------------------------------------------------ DUW / DRUK / SPRIN
def test_duw_steen_opens_grave_passage():
    # §DUW row 4: DUW STEE @ rm 39 (e42!=1) -> e42=1, msg 66.
    eng, w = _engine(39)
    out = _run(eng, "duw steen")
    assert eng.state["e42"] == 1
    assert w.message_text(66) in out


def test_duw_steen_again_is_stuck():
    # §DUW row 3: once open (e42==1) the stone won't turn further -> msg 65.
    eng, w = _engine(39)
    eng.state["e42"] = 1
    out = _run(eng, "duw steen")
    assert w.message_text(65) in out


def test_duw_waard_room12():
    # §DUW row 1: DUW WAARD @ rm 12 -> msg 64.
    eng, w = _engine(12)
    assert w.message_text(64) in _run(eng, "duw waard")


def test_duw_anything_else_does_nothing():
    # §DUW row 2: pushing anything but the stone/innkeeper -> msg 67.
    eng, w = _engine(0)
    assert w.message_text(67) in _run(eng, "duw deur")


# ------------------------------------------------------------------ SPRING (jump)
def test_spring_room25_is_fatal():
    # EXE 0x2b65: SPRING in room 25 -> msg 218 (B A F F) + death; room unchanged.
    eng, w = _engine(25)
    out = _run(eng, "spring")
    assert w.message_text(218) in out
    assert eng.dead is True
    assert eng.room == 25


def test_spring_room28_is_fatal():
    # EXE 0x2b65: room 28 shares the fatal balcony jump -> msg 218 + death.
    eng, w = _engine(28)
    out = _run(eng, "spring")
    assert w.message_text(218) in out
    assert eng.dead is True


def test_spring_room33_hurts_ankle_and_moves_to_30():
    # EXE 0x2b90: room 33 -> msg 224 (BAF, twisted ankle) + move to room 30, non-fatal.
    eng, w = _engine(33)
    out = _run(eng, "spring")
    assert w.message_text(224) in out
    assert eng.room == 30
    assert eng.dead is False


def test_spring_room18_moves_to_17():
    # EXE 0x2b46: room 18 -> msg 62 (Iaaaaaaahhhh...) + move to room 17, non-fatal.
    eng, w = _engine(18)
    out = _run(eng, "spring")
    assert w.message_text(62) in out
    assert eng.room == 17
    assert eng.dead is False


def test_spring_elsewhere_just_hops():
    # EXE 0x2baf (else): any other room -> msg 63 (hop.....hop....hop..), no move.
    eng, w = _engine(0)
    out = _run(eng, "spring")
    assert w.message_text(63) in out
    assert eng.room == 0
    assert eng.dead is False


def test_spring_verb_routes_to_spring_not_duw():
    # game.py dispatch: 'spring' must reach the jump handler (was mis-routed to duw).
    # In room 25 the jump handler is fatal, which duw could never be.
    eng, w = _engine(25)
    _run(eng, "spring gat")
    assert eng.dead is True


# ------------------------------------------------------- HANG / KNOOP / BEVESTIG
def test_hang_touw_room25_ties_rope():
    # §HANG row 4: HANG/KNOOP TOUW @ rm 25 (carried) -> e92=1, rope consumed, msg 86.
    eng, w = _engine(25, carrying=[TOUW])
    out = _run(eng, "knoop touw")
    assert eng.state["e92"] == 1
    assert eng.obj_loc[TOUW] == LOC_NOWHERE
    assert w.message_text(86) in out


def test_hang_non_rope_is_pointless():
    # §HANG row 1: tying anything but the rope -> msg 83.
    eng, w = _engine(25)
    assert w.message_text(83) in _run(eng, "hang boom")


def test_hang_touw_not_carried():
    # §HANG row 2: rope not in hand -> msg 84.
    eng, w = _engine(25)
    assert w.message_text(84) in _run(eng, "hang touw")


def test_hang_touw_wrong_room():
    # §HANG row 3: rope carried but not in rm 25 -> msg 85.
    eng, w = _engine(0, carrying=[TOUW])
    assert w.message_text(85) in _run(eng, "hang touw")


# --------------------------------------------------------------------- GEEF
def test_geef_munt_room12_gives_coin():
    # §GEEF row 4: GEEF MUNT @ rm 12 (carried) -> coin consumed, msg 182.
    eng, w = _engine(12, carrying=[MUNT])
    out = _run(eng, "geef munt")
    assert eng.obj_loc[MUNT] == LOC_NOWHERE
    assert w.message_text(182) in out


def test_geef_munt_calms_angry_innkeeper():
    # §GEEF row 4b (0x3fc4): an angry innkeeper (e84>0) gets BOTH msg 182 (the coin
    # accepted) THEN msg 189 (he calms), and e84 is cleared.
    eng, w = _engine(12, carrying=[MUNT])
    eng.state["e84"] = 1
    out = _run(eng, "geef munt")
    assert eng.state["e84"] == 0
    assert w.message_text(182) in out
    assert w.message_text(189) in out


def test_geef_empty_noun():
    # §GEEF row 1: give with no noun -> msg 179.
    eng, w = _engine(12)
    assert w.message_text(179) in _run(eng, "geef")


def test_geef_munt_wrong_room():
    # §GEEF row 2: not (MUNT & rm 12) -> msg 180.
    eng, w = _engine(0, carrying=[MUNT])
    assert w.message_text(180) in _run(eng, "geef munt")


def test_geef_munt_not_carried():
    # §GEEF row 3: in rm 12 but coin not in hand -> msg 181.
    eng, w = _engine(12)
    assert w.message_text(181) in _run(eng, "geef munt")


# --------------------------------------------------------------------- VRAAG
# VERB MISMAP #1 fix: the real EXE VRAAG (0x2ab5) asks the innkeeper — it is NOT the
# enter-harnas handler (that belongs to DRAAG/PAS, tested above). The full innkeeper
# conversation is covered in tests/unit/test_waard_events.py; these two lock in that
# VRAAG no longer routes to the harnas.
def test_vraag_is_innkeeper_conversation_not_harnas():
    # VRAAG in the harnas room now does the conversation guard, NOT the harnas climb.
    eng, w = _engine(21)
    out = _run(eng, "vraag harnas")
    assert eng.room == 21                             # did NOT enter the armour
    assert w.message_text(56) in out                  # "Niemand geeft antwoord."


def test_vraag_waard_room12_reveals_zoldertrap():
    # §VRAAG (0x2b08): asking the waard in room 12 reveals the zoldertrap (e6e=1, msg 59).
    eng, w = _engine(12)
    out = _run(eng, "vraag waard")
    assert eng.state["e6e"] == 1
    assert w.message_text(59) in out


# --------------------------------------------------------------------- OPEN
def test_open_raam_closed_then_open():
    # §OPEN rows 1/2: window starts open (e3c=0) -> "al open" (234); when closed
    # (e3c!=0) OPEN RAAM re-opens it (e3c=0) -> 232.
    eng, w = _engine(0)
    assert w.message_text(234) in _run(eng, "open raam")       # already open
    eng.state["e3c"] = -1                                       # closed
    out = _run(eng, "open raam")
    assert eng.state["e3c"] == 0
    assert w.message_text(232) in out


def test_open_luik_room1_needs_reveal():
    # §OPEN rows 4/5/6: bedroom luik.
    eng, w = _engine(1)
    assert w.message_text(69) in _run(eng, "open luik")        # e86==0 -> not seen
    eng.state["e86"] = 1                                        # revealed
    out = _run(eng, "open luik")
    assert eng.state["e88"] == 1
    assert w.message_text(71) in out
    assert w.message_text(70) in _run(eng, "open luik")        # e88==1 -> already open


def test_open_hek_room37_opens_gate():
    # §OPEN rows 7/8/9: iron gate opens from rm 37 only.
    eng, w = _engine(37)
    out = _run(eng, "open hek")
    assert eng.state["e44"] == 1
    assert w.message_text(74) in out
    assert w.message_text(72) in _run(eng, "open hek")         # now already open


def test_open_hek_room32_is_stuck():
    # §OPEN row 8: from the gewelf side (rm 32) the gate won't open.
    eng, w = _engine(32)
    out = _run(eng, "open hek")
    assert eng.state["e44"] == 0
    assert w.message_text(73) in out


def test_open_coffin_releases_dracula():
    # §OPEN row 11: OPEN KIST in Dracula's coffin room (obj37 @ rm 37).
    eng, w = _engine(37)
    out = _run(eng, "open doodskist")
    assert eng.state["e76"] == 1
    assert eng.state["dde"] == 37
    assert eng.obj_loc[DOODSKIST] == LOC_NOWHERE
    assert eng.obj_loc[DOODSKIST_OPEN] == 37
    assert w.message_text(242) in out
    # §OPEN row 12: opening again -> "al open" (244).
    assert w.message_text(244) in _run(eng, "open kist")


def test_open_tower_chest_room29():
    # §OPEN row 13: OPEN KIST reveals the luik in the tower chest (obj21 -> obj22).
    eng, w = _engine(29)
    assert eng.obj_loc[KIST_DICHT] == 29
    out = _run(eng, "open kist")
    assert eng.obj_loc[KIST_DICHT] == LOC_NOWHERE
    assert eng.obj_loc[KIST_LUIK_DICHT] == 29
    assert w.message_text(76) in out


def test_open_tower_luik_needs_dracula_active():
    # §OPEN rows 15/16: the tower-chest luik opens only when Dracula is active (e72).
    eng, w = _engine(29, placed={KIST_DICHT: LOC_NOWHERE, KIST_LUIK_DICHT: 29})
    assert w.message_text(79) in _run(eng, "open luik")        # e72!=1 -> muurvast
    eng.state["e72"] = 1
    out = _run(eng, "open luik")
    assert eng.obj_loc[KIST_LUIK_DICHT] == LOC_NOWHERE
    assert eng.obj_loc[KIST_LUIK_OPEN] == 29
    assert w.message_text(78) in out


def test_open_doos_drops_hammer():
    # §OPEN rows 17/18: OPEN DOOS (present) -> e8c=1, hammer drops, msg 81.
    eng, w = _engine(4)                                         # doos (obj31) starts in rm 4
    out = _run(eng, "open doos")
    assert eng.state["e8c"] == 1
    assert eng.obj_loc[HAMER] == 4
    assert w.message_text(81) in out
    assert w.message_text(80) in _run(eng, "open doos")        # already open


def test_open_kist_room14_and_room2():
    # §OPEN rows 10/14: fixed responses for the other chests.
    eng, w = _engine(14)
    assert w.message_text(75) in _run(eng, "open kist")
    eng, w = _engine(2)
    assert w.message_text(206) in _run(eng, "open kist")


def test_open_unopenable_thing():
    # §OPEN row 19 (else): msg 82.
    eng, w = _engine(0)
    assert w.message_text(82) in _run(eng, "open boom")


# --------------------------------------------------------------------- SLUIT
def test_sluit_deur_room23_closes_exit():
    # §SLUIT row 1: SLUIT DEUR @ rm 23 -> df0=0, msg 163.
    eng, w = _engine(23)
    out = _run(eng, "sluit deur")
    assert eng.state["df0"] == 0
    assert w.message_text(163) in out


def test_sluit_raam_toggles_window():
    # §SLUIT rows 2/3: SLUIT RAAM closes the window (e3c=-1); again -> "al dicht".
    eng, w = _engine(0)
    out = _run(eng, "sluit raam")
    assert eng.state["e3c"] == -1
    assert w.message_text(231) in out
    assert w.message_text(233) in _run(eng, "sluit raam")


def test_sluit_castle_and_house_and_r40_doors():
    # §SLUIT rows 4/5/6: doors that can't be (usefully) closed.
    assert w_msg(20, "sluit deur", 161)
    assert w_msg(0, "sluit deur", 162)
    assert w_msg(40, "sluit deur", 164)


def test_sluit_else():
    # §SLUIT row 8 (else): msg 165.
    eng, w = _engine(9)
    assert w.message_text(165) in _run(eng, "sluit boom")


def w_msg(room, line, idx):
    eng, w = _engine(room)
    return w.message_text(idx) in _run(eng, line)


# --------------------------------------------------------------------- HAK / KAP
TREE_ROOM = 7


def test_hak_non_tree_is_refused():
    # §HAK rows 1/2.
    assert w_msg(0, "hak steen", 1)                 # not a tree
    assert w_msg(0, "hak boom", 28)                 # no trees in this room


def test_hak_boom_bare_handed():
    # §HAK row 4: a tree room but no sharp axe in hand -> msg 2.
    eng, w = _engine(TREE_ROOM)
    assert w.message_text(2) in _run(eng, "hak boom")


def test_hak_boom_with_sharp_axe_yields_wood():
    # §HAK row 5: chop -> wood in the room, sharp axe consumed, blunt axe now carried.
    eng, w = _engine(TREE_ROOM, carrying=[BIJL_SCHERP])
    out = _run(eng, "hak boom")
    assert eng.obj_loc[HOUT] == TREE_ROOM
    assert eng.obj_loc[BIJL_SCHERP] == LOC_NOWHERE
    assert eng.obj_loc[BOTTE_BIJL] == CARRIED
    assert w.message_text(30) in out


def test_hak_boom_blunt_axe():
    # §HAK row 3: the blunt axe can't chop -> msg 29.
    eng, w = _engine(TREE_ROOM, carrying=[BOTTE_BIJL])
    assert w.message_text(29) in _run(eng, "hak boom")


# --------------------------------------------------------- VUL / EET / DRINK
def test_eat_non_food():
    # §VUL row 1: not bread/water/milk -> msg 0.
    assert w_msg(0, "eet steen", 0)


def test_eat_brood():
    # §VUL rows 6/7: eating carried bread -> bread consumed, msg 38.
    eng, w = _engine(2, carrying=[BROOD])
    out = _run(eng, "eet brood")
    assert eng.obj_loc[BROOD] == LOC_NOWHERE
    assert w.message_text(38) in out
    # not carried -> "grab first" (msg 3)
    eng, w = _engine(2)
    assert w.message_text(3) in _run(eng, "eet brood")


def test_drink_milk_leaves_empty_bottle():
    # §VUL row 3: milk drunk -> milk consumed, empty bottle now carried, msg 35.
    eng, w = _engine(2, carrying=[MELK])
    out = _run(eng, "drink melk")
    assert eng.obj_loc[MELK] == LOC_NOWHERE
    assert eng.obj_loc[LEGE_FLES] == CARRIED
    assert w.message_text(35) in out


def test_drink_water_ordinary():
    # §VUL row 5: ordinary water -> consumed, empty bottle carried, msg 37.
    eng, w = _engine(2, carrying=[WATER])
    out = _run(eng, "drink water")
    assert eng.obj_loc[WATER] == LOC_NOWHERE
    assert eng.obj_loc[LEGE_FLES] == CARRIED
    assert w.message_text(37) in out


def test_drink_poison_sets_df6_but_does_not_kill():
    # §VUL row 4 (EXE 0x233b-0x2351): the blue poison water sets [0xdf6]=-1 (0x234b)
    # and prints msg 36, then `jmp 0x261`. FAITHFUL TRUTH (verified against the
    # disassembly): the death NEVER fires — the main loop reaches `0x30e call 0x269e`,
    # whose FIRST instruction (`mov [0xdf6],0`) unconditionally wipes the latch BEFORE
    # the `0x0311 cmp [0xdf6]` death-check reads it. The message's "Je sterft"/"na
    # enkele minuten" flavour is a latent-bug promise the code never keeps. So DRINK
    # WATE (poison) is faithfully death-NEUTRAL: df6 is set, the line prints, no death.
    eng, w = _engine(2, carrying=[GIF_FLES])
    out = _run(eng, "drink water")
    assert eng.state["df6"] == -1              # 0x234b: the poison latch is set …
    assert w.message_text(36) in out           # … and the giftig-water line prints …
    assert eng.dead is False                   # … but the player does NOT die (EXE-faithful)


# ------------------------------------------- VUL (fill bottle at the well, 0x3175)
def test_vul_wrong_noun():
    # 0x3175 branch 1: noun != FLES -> msg 95 ("Hoe wou je dat vullen ?"). No state.
    eng, w = _engine(16)
    out = _run(eng, "vul steen")
    assert w.message_text(95) in out


def test_vul_fles_wrong_room():
    # branch 2: FLES but not at the well (room != 16) -> msg 96 ("Waarmee ?").
    eng, w = _engine(2, carrying=[LEGE_FLES])
    out = _run(eng, "vul fles")
    assert w.message_text(96) in out
    assert eng.obj_loc[LEGE_FLES] == CARRIED     # nothing consumed


def test_vul_melk_carried():
    # branch 3: at the well with milk in hand -> msg 97 ("Er zit al melk in.").
    eng, w = _engine(16, carrying=[MELK])
    out = _run(eng, "vul fles")
    assert w.message_text(97) in out


def test_vul_water_carried():
    # branch 4: at the well already holding water -> msg 98 ("...nog vol met water.").
    eng, w = _engine(16, carrying=[WATER])
    out = _run(eng, "vul fles")
    assert w.message_text(98) in out


def test_vul_no_empty_bottle():
    # branch 5: at the well but the empty bottle isn't carried -> msg 99.
    eng, w = _engine(16)                          # LEGE_FLES default LOC_NOWHERE
    out = _run(eng, "vul fles")
    assert w.message_text(99) in out


def test_vul_fill_water_no_coin():
    # branch 7 (e66 != 1): fill the empty bottle with ordinary water.
    eng, w = _engine(16, carrying=[LEGE_FLES])
    assert eng.state["e66"] == 0
    out = _run(eng, "vul fles")
    assert w.message_text(100) in out
    assert eng.obj_loc[LEGE_FLES] == LOC_NOWHERE
    assert eng.obj_loc[WATER] == CARRIED
    assert eng.obj_loc[GIF_FLES] != CARRIED


def test_vul_fill_poison_with_coin():
    # branch 6 (e66 == 1, coin thrown in well): fill gives the blue poison bottle.
    eng, w = _engine(16, carrying=[LEGE_FLES])
    eng.state["e66"] = 1
    out = _run(eng, "vul fles")
    assert w.message_text(100) in out
    assert eng.obj_loc[LEGE_FLES] == LOC_NOWHERE
    assert eng.obj_loc[GIF_FLES] == CARRIED
    assert eng.obj_loc[WATER] != CARRIED


# --------------------------------------------------------------- GRAAF / SCHEP
def test_graaf_without_spade():
    # §GRAAF row 1: no spade -> msg 2.
    assert w_msg(36, "graaf gat", 2)


def test_graaf_graveyard():
    # §GRAAF row 2: digging in the graveyard (rm 36) -> bones, msg 31.
    eng, w = _engine(36, carrying=[SCHEP])
    assert w.message_text(31) in _run(eng, "graaf gat")


def test_graaf_hard_ground():
    # §GRAAF row 3: rooms you can't dig -> msg 32.
    eng, w = _engine(0, carrying=[SCHEP])
    assert w.message_text(32) in _run(eng, "graaf gat")


def test_graaf_needs_direction():
    # §GRAAF row 4: diggable room, GRON/GAT noun (not a direction) -> msg 33.
    eng, w = _engine(39, carrying=[SCHEP])
    assert w.message_text(33) in _run(eng, "graaf gat")


def test_graaf_grond_needs_direction():
    # §GRAAF ROW4: the 'GRON' noun also triggers the give-a-direction reply.
    eng, w = _engine(5, carrying=[SCHEP])
    out = _run(eng, "graaf grond")
    assert w.message_text(33) in out
    assert eng.room == 5                      # no move


def test_graaf_room4_down_to_room5():
    # §GRAAF ROW5: digging a direction in room 4 tunnels down to room 5 (deterministic).
    eng, w = _engine(4, carrying=[SCHEP])
    _run(eng, "graaf west")
    assert eng.room == 5


def test_graaf_room5_north_to_room39():
    # §GRAAF ROW6: digging 'N...' (LEFT$(noun,1)=='N') from room 5 -> room 39.
    eng, w = _engine(5, carrying=[SCHEP])
    _run(eng, "graaf noord")
    assert eng.room == 39


def test_graaf_room39_north_stays_room39():
    # §GRAAF ROW6: digging north from room 39 stays at 39 (EXE 0x2273, both rm 5/39).
    eng, w = _engine(39, carrying=[SCHEP])
    _run(eng, "graaf noord")
    assert eng.room == 39


def test_graaf_room5_nonnorth_random_donker_woud():
    # §GRAAF ROW6-else: a non-N dig in room 5/39 -> int(RND*2)+7 in {7,8}. With the
    # fresh game RNG (seed 5) the first draw (0.1677..) picks room 7.
    eng, w = _engine(5, carrying=[SCHEP])
    _run(eng, "graaf west")
    assert eng.room == 7


def test_graaf_room39_nonnorth_random_in_range():
    # ROW6-else from room 39: still a {7,8} donker-woud pick, never a stray room.
    eng, w = _engine(39, carrying=[SCHEP])
    _run(eng, "graaf zuid")
    assert eng.room in (7, 8)


# --------------------------------------------------- GA GAT/LADD (room-0 ceiling)
def test_ga_gat_room0_no_ladder_message():
    # (a) GA GAT @ room0, e3e==0 (no ladder) -> msg 11 'gat te hoog', no move.
    eng, w = _engine(0)
    out = _run(eng, "ga gat")
    assert w.message_text(11) in out
    assert eng.room == 0


def test_ga_ladder_room0_no_ladder_message():
    # (a) GA LADD @ room0, e3e==0 -> msg 34 'Welke ladder bedoel je ?', no move.
    eng, w = _engine(0)
    out = _run(eng, "ga ladder")
    assert w.message_text(34) in out
    assert eng.room == 0


def test_ga_gat_room0_with_ladder_climbs_to_room3():
    # (a) GA GAT @ room0, e3e!=0 (ladder placed) -> room 3.
    eng, w = _engine(0)
    eng.state["e3e"] = 1
    _run(eng, "ga gat")
    assert eng.room == 3


def test_ga_ladder_room0_with_ladder_climbs_to_room3():
    # (a) GA LADD @ room0, e3e!=0 -> room 3 (via the 0x229c climb special).
    eng, w = _engine(0)
    eng.state["e3e"] = 1
    _run(eng, "ga ladder")
    assert eng.room == 3


# ------------------------------------------------- GA TOUW (balcony rope descent)
def test_ga_touw_room25_untied_message():
    # (c) GA TOUW @ room25, obj12 not at 25 (rope not tied) -> msg 139, no move.
    eng, w = _engine(25)
    out = _run(eng, "ga touw")
    assert w.message_text(139) in out
    assert eng.room == 25


def test_ga_touw_room25_descends_when_tied():
    # (c) GA TOUW @ room25, obj12 at 25 -> descend to room 26.
    eng, w = _engine(25, placed={12: 25})
    _run(eng, "ga touw")
    assert eng.room == 26


def test_ga_touw_room26_ascends_when_tied():
    # (c) GA TOUW @ room26, obj12 at 25 -> ascend to room 25 (bidirectional toggle).
    eng, w = _engine(26, placed={12: 25})
    _run(eng, "ga touw")
    assert eng.room == 25


def test_hang_touw_then_descend_end_to_end():
    # Integration: HANG TOUW @ rm25 ties the rope (obj12->25), then GA TOUW descends.
    eng, w = _engine(25, carrying=[TOUW])
    _run(eng, "hang touw")
    assert eng.obj_loc[12] == 25
    _run(eng, "ga touw")
    assert eng.room == 26


# ------------------------------------------------------------ BEKIJK (flag cases)
def test_bekijk_bed_before_and_after_sleeping():
    # §BEKIJK rows 1/2: examining the bed reveals the luik only after sleeping (e96).
    eng, w = _engine(1)
    assert w.message_text(115) in _run(eng, "bekijk bed")     # not slept
    eng.state["e96"] = 1
    out = _run(eng, "bekijk bed")
    assert eng.state["e86"] == 1
    assert w.message_text(116) in out


def test_bekijk_toren_activates_dracula():
    # §BEKIJK row 3: examining the tower from rm 51 ACTIVATES Dracula (e72).
    eng, w = _engine(51)
    out = _run(eng, "bekijk toren")
    assert eng.state["e72"] == 1
    assert eng.state["e88"] == 1
    assert w.message_text(119) in out
    # row 4: examining again -> the "verlaten kasteeltoren" line (176).
    assert w.message_text(176) in _run(eng, "bekijk toren")


def test_bekijk_generic_object_preserved():
    # non-flag examine still gives the generic "niets bijzonders" response.
    eng, w = _engine(1)                       # lantern (obj0) is here
    assert "niets bijzonders" in _run(eng, "bekijk lantaarn")


# ================================================================= BEKIJK details
# EXE 0x32e6 (shared BEKIJK/ONDER handler). The shared resolver 0x3822 sets
# [0xe8a]=present iff a noun-matching object is carried/in-room; then ~18 look-text
# branches evaluate in EXE order before the generic else. All indices are the
# world.messages index (EXE [0xe34]=K prints world.messages[K-1]).
def test_bekijk_wig_detail():
    # 0x32e9: WIG present -> msg 108.
    eng, w = _engine(0, carrying=[WIG])
    assert w.message_text(108) in _run(eng, "bekijk wig")


def test_bekijk_wig_absent_is_generic():
    # WIG not present -> no WIG branch, generic else (absent) -> msg 122.
    eng, w = _engine(0)                        # wig (obj2) is in room 18
    out = _run(eng, "bekijk wig")
    assert w.message_text(108) not in out
    assert w.message_text(122) in out


def test_bekijk_boek_physical_detail():
    # 0x330c: BOEK present -> msg 109 (physical description; LEES BOEK is the content).
    eng, w = _engine(0, carrying=[BOEK])
    assert w.message_text(109) in _run(eng, "bekijk boek")


def test_bekijk_kapmes_detail():
    # 0x3369: KAPM present -> msg 110.
    eng, w = _engine(0, carrying=[KAPMES])
    assert w.message_text(110) in _run(eng, "bekijk kapmes")


def test_bekijk_harnas_detail():
    # 0x338c: HARN present (harnas at home room 21) -> msg 111. Room != 54 so the
    # visor branch is not reached.
    eng, w = _engine(21)                       # harnas (obj36) starts in room 21
    assert w.message_text(111) in _run(eng, "bekijk harnas")


def test_bekijk_touw_detail():
    # 0x346f: TOUW present -> msg 112.
    eng, w = _engine(0, carrying=[TOUW])
    assert w.message_text(112) in _run(eng, "bekijk touw")


def test_bekijk_schatkist_detail():
    # 0x3566: (SCHA|KIST) & present(SCHATKIST, EXE index 14) -> msg 113.
    eng, w = _engine(35)                       # schatkist (obj13) starts in room 35
    assert w.message_text(113) in _run(eng, "bekijk schatkist")
    eng, w = _engine(35)
    assert w.message_text(113) in _run(eng, "bekijk kist")


def test_bekijk_bloed_easteregg_room14():
    # 0x332f: (BLOE|VLEK) & room==14 -> msg 212 (blood-type easter egg, scenery).
    eng, w = _engine(14)
    assert w.message_text(212) in _run(eng, "bekijk bloed")
    eng, w = _engine(14)
    assert w.message_text(212) in _run(eng, "bekijk vlek")


def test_bekijk_steen_incore_room14():
    # 0x34d4: STEE & room==14 -> msg 214 (INCORE automatisering easter egg).
    eng, w = _engine(14)
    assert w.message_text(214) in _run(eng, "bekijk steen")


def test_bekijk_voetsporen_room17():
    # 0x3500: (VOET|SPOR) & room==17 -> msg 217 (boot/animal prints).
    eng, w = _engine(17)
    assert w.message_text(217) in _run(eng, "bekijk voetsporen")
    eng, w = _engine(17)
    assert w.message_text(217) in _run(eng, "bekijk sporen")


def test_bekijk_cirkel_room2():
    # 0x353a: CIRK & room==2 -> msg 208 (old stove spot).
    eng, w = _engine(2)
    assert w.message_text(208) in _run(eng, "bekijk cirkel")


def test_bekijk_kist_room2_craftsmanship():
    # 0x35a4: KIST & room==2 (no schatkist here) -> msg 207 (carved craftsmanship).
    eng, w = _engine(2)
    assert w.message_text(207) in _run(eng, "bekijk kist")


def test_bekijk_bed_elsewhere_asks_which_bed():
    # 0x35d0: BED with room!=1 -> msg 114 ("Welk bed had je in gedachten ?").
    eng, w = _engine(2)
    assert w.message_text(114) in _run(eng, "bekijk bed")


def test_bekijk_doodskist_closed_coffin():
    # 0x3613: (KIST|DOOD) & room==loc(DOODSKIST obj37, init 37) -> msg 245.
    eng, w = _engine(37)
    assert eng.obj_loc[DOODSKIST] == 37
    assert w.message_text(245) in _run(eng, "bekijk doodskist")
    eng, w = _engine(37)
    assert w.message_text(245) in _run(eng, "bekijk kist")


def test_bekijk_doodskist_open_coffin():
    # 0x364f: (KIST|DOOD) & present(DOODSKIST_OPEN obj38, EXE index 39) -> msg 246.
    # The closed coffin (obj37) must NOT be in the room, else 0x3613 wins first.
    eng, w = _engine(37, placed={DOODSKIST: LOC_NOWHERE, DOODSKIST_OPEN: 37})
    assert w.message_text(246) in _run(eng, "bekijk kist")


def test_bekijk_sesam_door_room31():
    # 0x368d: (DEUR|VREE|SESA) & room==31 -> msg 283 ("DIT IS SESAM" gebrand).
    eng, w = _engine(31)
    assert w.message_text(283) in _run(eng, "bekijk deur")
    eng, w = _engine(31)
    assert w.message_text(283) in _run(eng, "bekijk vreemde")


def test_bekijk_luik_room1_revealed():
    # 0x36d5: LUIK & room==1 & e86==1 -> msg 117.
    eng, w = _engine(1)
    eng.state["e86"] = 1
    assert w.message_text(117) in _run(eng, "bekijk luik")


def test_bekijk_luik_room29_tower_chest():
    # 0x36d5: LUIK & room==29 & (room==loc(obj22) or room==loc(obj23)) -> msg 118.
    eng, w = _engine(29, placed={KIST_LUIK_DICHT: 29})
    assert w.message_text(118) in _run(eng, "bekijk luik")


def test_bekijk_eetkamer_spyview_room52():
    # 0x37be: (EETK|ROOS|GAT) & room==52 -> msg 120 (deterministic eetkamer spy-view).
    eng, w = _engine(52)
    assert w.message_text(120) in _run(eng, "bekijk eetkamer")
    eng, w = _engine(52)
    assert w.message_text(120) in _run(eng, "bekijk rooster")


def test_bekijk_raam_window_random_room29():
    # 0x3492: RAAM & room==29 -> RANDOM msg 219 + int(RND*3) in {219,220,221}. With
    # the fresh game RNG (seed 5) the first draw (0.1677..) selects the base, msg 219.
    eng, w = _engine(29)
    out = _run(eng, "bekijk raam")
    assert w.message_text(219) in out


def test_bekijk_vizier_home_random_room54():
    # 0x33af: (HARN|VIZI) & room==54, harnas at home (loc 21) -> RANDOM visor view
    # msg 225 + int(RND*3) in {225,226,227}; fresh RNG -> msg 225.
    eng, w = _engine(54, placed={HARNAS: 21})
    assert w.message_text(225) in _run(eng, "bekijk vizier")


def test_bekijk_vizier_kruiskamer_room54():
    # 0x33af sub-case: harnas at loc 34 (kruiskamer) -> msg 273.
    eng, w = _engine(54, placed={HARNAS: 34})
    assert w.message_text(273) in _run(eng, "bekijk vizier")


def test_bekijk_vizier_schatkamer_room54():
    # 0x33af sub-case: harnas elsewhere (loc 35, schatkamer) -> msg 274.
    eng, w = _engine(54, placed={HARNAS: 35})
    assert w.message_text(274) in _run(eng, "bekijk vizier")


def test_bekijk_vizier_carried_room54():
    # 0x33af sub-case: harnas carried (loc -1) -> msg 275 ("Onmogelijkheid, foutje..").
    eng, w = _engine(54, carrying=[HARNAS])
    assert w.message_text(275) in _run(eng, "bekijk vizier")


def test_bekijk_generic_present_object_msg121():
    # 0x3803 generic else: an object present but with no look-text -> msg 121
    # ("Zover ik het kan beoordelen is er niets bijzonders mee."). KRUIS has no branch.
    eng, w = _engine(0, carrying=[KRUIS])
    out = _run(eng, "bekijk kruis")
    assert w.message_text(121) in out


def test_bekijk_generic_absent_object_msg122():
    # 0x3803 generic else: nothing matches -> msg 122 ("Ik zie er niets bijzonders
    # aan."). This corrects the old deviation (which printed "Ik zie geen ... hier.").
    eng, w = _engine(0)
    out = _run(eng, "bekijk zwaard")
    assert w.message_text(122) in out


def test_bekijk_brief_has_no_bekijk_branch():
    # BRIEF (obj35) has NO BEKIJK branch (only LEES 0x3110) -> generic present, msg 121.
    eng, w = _engine(0)                        # briefje (obj35) starts in room 0
    out = _run(eng, "bekijk briefje")
    assert w.message_text(121) in out
    assert w.message_text(201) not in out      # the letter text is LEES-only


def test_bekijk_tower_activates_and_advances_chest():
    # 0x3741 (kept, now faithful): BEKIJK TORE @ rm 51 sets e72/e88 AND advances the
    # tower chest (obj21->99, obj22->99, obj23->29) so room 29 gets the open luik.
    eng, w = _engine(51)
    _run(eng, "bekijk toren")
    assert eng.state["e72"] == 1
    assert eng.state["e88"] == 1
    assert eng.obj_loc[KIST_DICHT] == LOC_NOWHERE
    assert eng.obj_loc[KIST_LUIK_DICHT] == LOC_NOWHERE
    assert eng.obj_loc[KIST_LUIK_OPEN] == 29


# ===================================================================== LEES (read)
# EXE 0x3076 (verb LEES -> jmp 0x3076): BOEK/TEKS/BRIE/INSC, then any other noun
# falls through to BEKIJK (0x315c -> jmp 0x32e6). The engine un-aliases lees from
# bekijk (game.py) so these reads are no longer dropped.
def test_lees_boek_carried_content():
    # 0x3076: LEES BOEK carried -> msg 91 (VAMPIER HANDBOECK content).
    eng, w = _engine(0, carrying=[BOEK])
    assert w.message_text(91) in _run(eng, "lees boek")


def test_lees_boek_not_carried():
    # 0x3084: LEES BOEK not carried -> msg 90 ("Dat moet je dan wel bij je hebben.").
    eng, w = _engine(0)                        # boek (obj4) starts nowhere
    assert w.message_text(90) in _run(eng, "lees boek")


def test_lees_tekst_cipher_room23():
    # 0x30a0: TEKS & room==23 & df0==0 -> msg 94 (the cipher).
    eng, w = _engine(23)
    eng.state["df0"] = 0
    assert w.message_text(94) in _run(eng, "lees tekst")


def test_lees_tekst_castle_sign_room20():
    # 0x30d6: TEKS & room==20 -> msg 216 (DRACULA CASTLE sign).
    eng, w = _engine(20)
    assert w.message_text(216) in _run(eng, "lees tekst")


def test_lees_tekst_book_present():
    # 0x30e9: TEKS with the book present (not room 23/20) -> msg 91.
    eng, w = _engine(0, carrying=[BOEK])
    assert w.message_text(91) in _run(eng, "lees tekst")


def test_lees_tekst_nothing():
    # 0x3107: TEKS, no book, ordinary room -> msg 92 ("Ik zie geen tekst.").
    eng, w = _engine(0)
    assert w.message_text(92) in _run(eng, "lees tekst")


def test_lees_briefje_present_rules():
    # 0x3110: BRIE present -> msg 201 (the Spelregels/quest text).
    eng, w = _engine(0)                        # briefje (obj35) starts in room 0
    assert w.message_text(201) in _run(eng, "lees briefje")


def test_lees_briefje_absent():
    # 0x3148: BRIE not present -> msg 202 ("Welk papier ?").
    eng, w = _engine(5)                        # briefje is back in room 0, not here
    assert w.message_text(202) in _run(eng, "lees briefje")


def test_lees_inscriptie_room2():
    # 0x3151: INSC & room==2 -> msg 209 (the latin inscription).
    eng, w = _engine(2)
    assert w.message_text(209) in _run(eng, "lees inscriptie")


def test_lees_inscriptie_elsewhere_not_here():
    # 0x3172: INSC & room!=2 -> jmp 0x4c88 (eng._not_here, "Ik zie geen ... hier.").
    eng, w = _engine(0)
    assert "Ik zie geen inscriptie hier." in _run(eng, "lees inscriptie")


def test_lees_other_noun_falls_through_to_bekijk():
    # 0x315c: any other noun jmps into the BEKIJK handler. LEES WIG (wig present)
    # therefore yields the BEKIJK WIG look-text (msg 108).
    eng, w = _engine(0, carrying=[WIG])
    assert w.message_text(108) in _run(eng, "lees wig")


# ------------------------------------------------------------------ SLAAP (sleep)
# EXE 0x392a: sleeping only works in the bedroom (room 1); elsewhere -> msg 123.
# In room 1 the night event is gated on the castle-door flag [0xdee] and whether the
# discovery already happened ([0xe96]):
#   (dee==1 OR e96==1) -> wake fresh in the morning (msg 124), no state change;
#   (dee==0 AND e96==0) -> woken at night by rumbling under the bed (msg 125), which
#   sets [0xe96]=1 (0x396b) — the writer BEKIJK BED needs to reveal the luik.
def test_slaap_wrong_room_is_uncomfortable():
    # room != 1 -> "Je kunt hier moeilijk in slaap komen ..." (msg 123); no flag write.
    eng, w = _engine(0)
    out = _run(eng, "slaap")
    assert w.message_text(123) in out
    assert eng.state["e96"] == 0


def test_slaap_room1_door_open_wakes_fresh():
    # room 1 with the castle door still open (dee==1, the game-start value) -> the
    # peaceful "Je wordt 's morgens vroeg weer fit wakker." (msg 124); e96 unchanged.
    eng, w = _engine(1)
    assert eng.state["dee"] == 1                      # start value
    out = _run(eng, "slaap")
    assert w.message_text(124) in out
    assert eng.state["e96"] == 0


def test_slaap_room1_discovers_luik_and_sets_e96():
    # room 1, castle door closed (dee==0) and not slept yet -> the night-rumbling
    # discovery "Je wordt midden in de nacht wakker door gerommel ..." (msg 125),
    # which sets [0xe96]=1.
    eng, w = _engine(1)
    eng.state["dee"] = 0
    out = _run(eng, "slaap")
    assert eng.state["e96"] == 1
    assert w.message_text(125) in out


def test_slaap_room1_already_slept_wakes_fresh():
    # room 1, dee==0 but the discovery already happened (e96==1) -> back to the
    # peaceful "fit wakker" (msg 124); no re-trigger.
    eng, w = _engine(1)
    eng.state["dee"] = 0
    eng.state["e96"] = 1
    out = _run(eng, "slaap")
    assert w.message_text(124) in out
    assert eng.state["e96"] == 1


def test_slaap_then_bekijk_bed_reveals_luik():
    # End-to-end: the sleep event provides the [0xe96] writer that the already-wired
    # BEKIJK BED reveal consumes (rm 1, dee==0): SLAAP -> e96=1 -> BEKIJK BED -> e86=1
    # + msg 116 (the luik-under-the-bed reveal).
    eng, w = _engine(1)
    eng.state["dee"] = 0
    _run(eng, "slaap")
    assert eng.state["e96"] == 1
    out = _run(eng, "bekijk bed")
    assert eng.state["e86"] == 1
    assert w.message_text(116) in out


# --------------------------------------------------------------- TIL / TREK
# EXE 0x4bd7 (dispatch 0xb15-0xb36 routes both 'til' (0x1274) and 'trek' (0x127c)
# here). Four special branches in EXE order, then a generic PAK fallthrough. No
# flag writes; only the current room ([0xe2e]) changes for the harnas enter/exit.
def test_til_bed_room1_wont_lift():
    # Branch A: TIL BED in the bedroom (room 1) -> msg 205 (K=0xce), no state change.
    eng, w = _engine(1)
    assert w.message_text(205) in _run(eng, "til bed")


def test_trek_bed_room1_same_as_til():
    # TREK routes to the same handler as TIL (dispatch 0xb15-0xb36).
    eng, w = _engine(1)
    assert w.message_text(205) in _run(eng, "trek bed")


def test_til_bed_elsewhere_not_here():
    # Branch A (room!=1): BED jmps to the shared 'Ik zie geen <noun> hier.' printer
    # (0x4c88 == eng._not_here); BED never falls through to the generic take.
    eng, w = _engine(2)
    assert "Ik zie geen bed hier." in _run(eng, "til bed")


def test_til_kist_coffin_room_lifts_nothing():
    # Branch B: KIST in Dracula's closed-coffin room ([0xca4]=obj37 loc, init 37)
    # -> msg 239 (K=0xf0). Distinct from PAK's coffin 'te zwaar' msg 236.
    eng, w = _engine(37)
    assert eng.obj_loc[DOODSKIST] == 37
    out = _run(eng, "til kist")
    assert w.message_text(239) in out
    assert w.message_text(236) not in out


def test_til_kist_other_room_falls_to_pak():
    # Branch B miss (room != coffin room) -> generic PAK; KIST in {2,14,29} -> msg 21.
    eng, w = _engine(14)
    assert w.message_text(21) in _run(eng, "til kist")


def test_trek_harnas_enters_armour():
    # Branch D: TREK HARN in the harnas's room ([0xca2]=obj36 loc, init 21) climbs
    # INTO the armour (room 54), via the VRAAG body 0x4ca9. Redescribes room 54.
    eng, w = _engine(21)
    out = _run(eng, "trek harnas")
    assert eng.room == 54
    assert w.rooms[54].description in out


def test_til_uit_exits_armour():
    # Branch C: TIL UIT while inside the armour (room 54) climbs OUT to loc(HARNAS).
    eng, w = _engine(54)
    out = _run(eng, "til uit")
    assert eng.room == loc_of(eng, HARNAS)
    assert eng.room == 21
    assert w.rooms[21].description in out


def test_til_harnas_in_armour_also_exits():
    # Branch C also fires for HARN (not just UIT) when inside the armour (room 54).
    eng, w = _engine(54)
    _run(eng, "til harnas")
    assert eng.room == 21


def test_til_ordinary_object_delegates_to_pak():
    # Branch E (else): an ordinary object -> generic PAK take, which prints "Ok".
    eng, w = _engine(1)                       # lantern (obj0) starts in room 1
    out = _run(eng, "til lantaarn")
    assert eng.obj_loc[LAMP] == CARRIED
    assert out.strip() == "Ok"


def test_til_armour_enter_exit_writes_no_flags_or_object_locations():
    # Faithfulness invariant (EXE 0x4bd7): the armour enter (Branch D, 0x4c60->0x4ca9)
    # and exit (Branch C, 0x4c26) touch ONLY the current-room var [0xe2e] -- there are
    # no flag writes and no object-location writes in the handler. Guard both.
    eng, w = _engine(21)                       # harnas's start room (loc(HARNAS)=21)
    state_before = dict(eng.state)
    locs_before = dict(eng.obj_loc)
    _run(eng, "trek harnas")                   # Branch D: climb IN -> room 54
    assert eng.room == 54
    _run(eng, "til uit")                       # Branch C: climb OUT -> room 21
    assert eng.room == 21
    assert eng.state == state_before           # no DGROUP flag mutated
    assert eng.obj_loc == locs_before          # no object relocated/consumed


def loc_of(eng, oid):
    return eng.obj_loc.get(oid)


# --------------------------------------------------------- Dracula combat verbs
# The decisive counter-blow drives the combat counter e74 to -1; the banish itself
# is applied by the (unported) end-of-turn routine, so these tests assert the
# faithful e74 / object writes, not a full banish.
def _dracula_in(eng, room, e74=2):
    eng.state["dde"] = room
    eng.state["e74"] = e74
    eng.state["e70"] = 0


def test_schijn_lamp_drives_dracula_back():
    # §4 SCHIJN: lamp on Dracula -> e74=0 + msg 174 (unless already at the kill phase).
    eng, w = _engine(22, carrying=[LAMP])
    _dracula_in(eng, 22)
    out = _run(eng, "schijn dracula")
    assert eng.state["e74"] == 0
    assert w.message_text(174) in out


def test_schijn_lamp_final_counterblow():
    # at the vulnerable phase (e74==1) the lamp lands the decisive blow (e74=-1).
    eng, w = _engine(22, carrying=[LAMP])
    _dracula_in(eng, 22, e74=1)
    _run(eng, "schijn dracula")
    assert eng.state["e74"] == -1


def test_gooi_knoflook_drives_dracula_back():
    # §4 GOOI KNOF: garlic -> e74=0 + msg 173.
    eng, w = _engine(22, carrying=[KNOFLOOK])
    _dracula_in(eng, 22)
    out = _run(eng, "gooi knoflook")
    assert eng.state["e74"] == 0
    assert w.message_text(173) in out


def test_toon_kruis_buys_a_turn():
    # §4 TOON KRUI: the cross in rm 24 -> e74=0 + msg 260.
    eng, w = _engine(24, carrying=[KRUIS])
    _dracula_in(eng, 24)
    out = _run(eng, "toon kruis")
    assert eng.state["e74"] == 0
    assert w.message_text(260) in out


def test_sla_wig_stakes_dracula():
    # §4 SLA WIG: the wig+hammer stake in rm 24 lands only when Dracula has been CALMED
    # (e74<=1, via TOON KRUIS) -> decisive blow (e74=-1), wig consumed. EXE 0x3c01.
    eng, w = _engine(24, carrying=[WIG, HAMER])
    _dracula_in(eng, 24, e74=1)                 # calmed
    _run(eng, "sla wig")
    assert eng.state["e74"] == -1
    assert eng.obj_loc[WIG] == LOC_NOWHERE


def test_sla_wig_fails_while_dracula_aggressive():
    # e74>1 (not yet calmed by TOON KRUIS) -> msg 263, no stake.
    eng, w = _engine(24, carrying=[WIG, HAMER])
    _dracula_in(eng, 24, e74=3)
    assert w.message_text(263) in _run(eng, "sla wig")
    assert eng.state["e74"] == 3                # unchanged


def test_sla_wig_without_hammer():
    # §4 SLA WIG missing the hammer -> msg 261.
    eng, w = _engine(24, carrying=[WIG])
    _dracula_in(eng, 24)
    assert w.message_text(261) in _run(eng, "sla wig")


def test_sla_dracula_directly_is_ineffective():
    # §4: hitting Dracula directly is useless (msg 170); msg 145 if he isn't here.
    eng, w = _engine(24)
    _dracula_in(eng, 24)
    assert w.message_text(170) in _run(eng, "sla dracula")
    eng, w = _engine(24)                       # Dracula absent (dde stays 255)
    assert w.message_text(145) in _run(eng, "sla dracula")


# ============================================================================
# End-to-end puzzle chains: a wired verb-event changes state, and the existing
# VERIFIED_NAMED navigation guards then honour it (verb + nav composed).
# ============================================================================
def test_window_puzzle_blocks_and_reopens_navigation():
    # GA RAAM crosses rooms 0<->6 only while the window is open (e3c==0).
    eng, w = _engine(0)
    eng.room = 0
    _run(eng, "ga raam")
    assert eng.room == 6                        # open at start -> can cross

    eng.room = 0
    _run(eng, "sluit raam")                     # e3c = -1 (closed)
    assert eng.state["e3c"] == -1
    _run(eng, "ga raam")
    assert eng.room == 0                         # blocked

    _run(eng, "open raam")                       # e3c = 0 (open again)
    _run(eng, "ga raam")
    assert eng.room == 6                          # crossable once more


def test_grave_passage_opens_after_pushing_stone():
    # DUW STEE @ rm 39 sets e42, then GA STEE crosses 39->37.
    eng, w = _engine(39)
    _run(eng, "ga steen")
    assert eng.room == 39                         # passage still shut
    _run(eng, "duw steen")
    assert eng.state["e42"] == 1
    _run(eng, "ga steen")
    assert eng.room == 37                          # now open


def test_iron_gate_passable_after_opening_from_room37():
    # OPEN HEK @ rm 37 sets e44, then GA TRAP crosses 37<->32.
    eng, w = _engine(37)
    _run(eng, "ga trap")
    assert eng.room == 37                          # gate shut
    _run(eng, "open hek")
    assert eng.state["e44"] == 1
    _run(eng, "ga trap")
    assert eng.room == 32                           # gate open, gewelf reachable


# --------------------------------------------------- room-31 secret-word password
DEUR_OPEN = 39


def test_room31_password_opens_door_when_dracula_defeated():
    # EXE 0x4f17: typing the secret in rm 31 with Dracula defeated (dde==257) opens
    # the sesam door (e48=1), places the "door open" object, and prints msg[266].
    eng, w = _engine(31)
    eng.state["dde"] = 257
    out = _run(eng, "incoronium")
    assert eng.state["e48"] == 1
    assert eng.obj_loc[DEUR_OPEN] == 31
    assert w.message_text(266) in out


def test_room31_password_silent_before_defeat():
    # secret typed but Dracula not yet defeated (dde!=257) -> the room stays silent (msg[265]).
    eng, w = _engine(31)                            # dde defaults to 255
    out = _run(eng, "incoronium")
    assert eng.state["e48"] == 0
    assert w.message_text(265) in out


def test_room31_secret_is_inert_in_other_rooms():
    # the word means nothing outside room 31.
    eng, w = _engine(0)
    out = _run(eng, "incoronium")
    assert eng.state["e48"] == 0
    assert w.message_text(266) not in out


def test_room31_password_then_ga_sesam_reaches_treasure_room():
    # after the password opens the door, GA SESAM crosses 31 -> 34.
    eng, w = _engine(31)
    eng.state["dde"] = 257
    _run(eng, "incoronium")
    _run(eng, "ga sesam")
    assert eng.room == 34


# ----------------------------------------------------------------------- SNIJ
# EXE 0x3203 (standalone; dispatched at 0x0d5d -> jmp 0x3203; NOT shared with KOOP).
# The kapmes (obj5) must be CARRIED as a universal gate; then the handler dispatches
# on the noun in EXE order TAK, HOUT, KRUI, BOOM, else. Only HOUT/KRUI with the wood
# carried carve it into the cross (obj7 -> LOC_NOWHERE, obj9 -> CARRIED, msg index
# 104). No flag writes, no navigation — every branch prints exactly one message.
TAK = 8


def test_snij_without_kapmes_is_barehanded():
    # Gate (0x3203): no kapmes carried -> "blote handen" (msg index 2), no carve even
    # with the wood in hand.
    eng, w = _engine(18, carrying=[HOUT])
    out = _run(eng, "snij hout")
    assert w.message_text(2) in out
    assert eng.obj_loc[HOUT] == CARRIED               # unchanged
    assert eng.obj_loc[KRUIS] == LOC_NOWHERE


def test_snij_hout_carves_cross():
    # SNIJ HOUT, kapmes + wood carried (0x328b) -> carve: msg 104, wood consumed,
    # cross now carried.
    eng, w = _engine(18, carrying=[KAPMES, HOUT])
    out = _run(eng, "snij hout")
    assert w.message_text(104) in out
    assert eng.obj_loc[HOUT] == LOC_NOWHERE
    assert eng.obj_loc[KRUIS] == CARRIED


def test_snij_kruis_also_carves_cross():
    # SNIJ KRUI with the wood carried performs the identical carve (EXE 0x32c3 -> 0x3278).
    eng, w = _engine(18, carrying=[KAPMES, HOUT])
    out = _run(eng, "snij kruis")
    assert w.message_text(104) in out
    assert eng.obj_loc[HOUT] == LOC_NOWHERE
    assert eng.obj_loc[KRUIS] == CARRIED


def test_snij_hout_in_room_must_be_taken():
    # SNIJ HOUT while the wood lies in the room (0x326f) -> "...pakken." (msg 3).
    eng, w = _engine(18, carrying=[KAPMES], placed={HOUT: 18})
    out = _run(eng, "snij hout")
    assert w.message_text(3) in out
    assert eng.obj_loc[HOUT] == 18                    # untouched
    assert eng.obj_loc[KRUIS] == LOC_NOWHERE


def test_snij_kruis_wood_in_room_needs_wood():
    # SNIJ KRUI with the wood in the room (0x32ba) -> the DIFFERENT msg 105 (not msg 3).
    eng, w = _engine(18, carrying=[KAPMES], placed={HOUT: 18})
    out = _run(eng, "snij kruis")
    assert w.message_text(105) in out
    assert eng.obj_loc[HOUT] == 18
    assert eng.obj_loc[KRUIS] == LOC_NOWHERE


def test_snij_hout_absent_when_no_wood():
    # SNIJ HOUT with no wood anywhere (0x3282) -> "Ik zie geen hout." (msg 103).
    eng, w = _engine(18, carrying=[KAPMES])           # HOUT default LOC_NOWHERE
    assert w.message_text(103) in _run(eng, "snij hout")


def test_snij_kruis_absent_when_no_wood():
    # SNIJ KRUI with no wood -> falls through (0x32c3 -> 0x3282) to msg 103.
    eng, w = _engine(18, carrying=[KAPMES])
    assert w.message_text(103) in _run(eng, "snij kruis")


def test_snij_tak_carried_is_useless():
    # SNIJ TAK carried (0x324c) -> "Met de tak valt niks te beginnen." (msg 102);
    # a branch cannot be carved into anything.
    eng, w = _engine(18, carrying=[KAPMES, TAK])
    out = _run(eng, "snij tak")
    assert w.message_text(102) in out
    assert eng.obj_loc[TAK] == CARRIED


def test_snij_tak_in_room_must_be_taken():
    # SNIJ TAK lying in the room (0x3230) -> "...pakken." (msg 3).
    eng, w = _engine(18, carrying=[KAPMES], placed={TAK: 18})
    assert w.message_text(3) in _run(eng, "snij tak")


def test_snij_tak_absent():
    # SNIJ TAK with no branch present (0x3243) -> "Ik zie geen tak hier." (msg 101).
    eng, w = _engine(18, carrying=[KAPMES])           # TAK default LOC_NOWHERE
    assert w.message_text(101) in _run(eng, "snij tak")


def test_snij_boom_sheds_splinters():
    # SNIJ BOOM (0x32d4) -> "Er dwarrelen wat snippertjes af." (msg 106).
    eng, w = _engine(18, carrying=[KAPMES])
    assert w.message_text(106) in _run(eng, "snij boom")


def test_snij_other_or_no_noun_is_pointless():
    # else branch (0x32dd): any other noun, or none, with the kapmes -> msg 107.
    eng, w = _engine(18, carrying=[KAPMES])
    assert w.message_text(107) in _run(eng, "snij steen")
    eng, w = _engine(18, carrying=[KAPMES])
    assert w.message_text(107) in _run(eng, "snij")


# ======================================================================
# DRAAG / PAS enter-harnas + the harnas fire-cross to the schatkamer.
# EXE: dispatcher 0x0928-0x0949 routes DRAAG (0x116c) and PAS (0x1164) to the
# enter-harnas handler 0x4ca9 (the noun is ignored) — the SAME body the engine
# historically wired under VRAAG (the real EXE VRAAG @0x2ab5 is the innkeeper;
# VRAAG is kept as-is per the task, DRAAG/PAS added here). The fire-cross lives in
# the movement handler (GA VUUR while inside the harnas, room 54): Branch A 0x19be
# (harnas 34->35, world[277]) and Branch B 0x1a0c (harnas 35->34, world[278]);
# only the harnas OBJECT location [0xca2] toggles, the player stays in room 54.
def test_draag_enters_harnas():
    # DRAAG in the harnas's room ([0xca2]=obj36 loc, init 21) -> room 54.
    eng, w = _engine(21)
    out = _run(eng, "draag harnas")
    assert eng.room == 54
    assert w.rooms[54].description in out


def test_draag_no_harnas_here():
    # DRAAG where there is no harnas -> msg 276 "Ik zie geen harnas hier."
    eng, w = _engine(0)
    assert w.message_text(276) in _run(eng, "draag harnas")


def test_pas_enters_harnas():
    # PAS routes to the identical enter-harnas handler (0x4ca9) as DRAAG.
    eng, w = _engine(21)
    _run(eng, "pas harnas")
    assert eng.room == 54


def test_pas_no_harnas_here():
    eng, w = _engine(0)
    assert w.message_text(276) in _run(eng, "pas harnas")


def test_ga_vuur_crosses_kruiskamer_to_schatkamer():
    # Branch A (0x19be): in the harnas (room 54) with the harnas on the kruiskamer
    # side (34), GA VUUR moves the harnas to the schatkamer side (35); world[277].
    # The player stays in room 54 (you then climb out with TREK/TIL UIT).
    eng, w = _engine(54, placed={HARNAS: 34})
    out = _run(eng, "ga vuur")
    assert eng.obj_loc[HARNAS] == 35
    assert eng.room == 54
    assert w.message_text(277) in out


def test_ga_vuur_crosses_schatkamer_back_to_kruiskamer():
    # Branch B (0x1a0c): harnas on the schatkamer side (35) -> GA VUUR moves it back
    # to 34 (world[278], the 'gebrande billen' / castle-shakes line). Stays in 54.
    eng, w = _engine(54, placed={HARNAS: 35})
    out = _run(eng, "ga vuur")
    assert eng.obj_loc[HARNAS] == 34
    assert eng.room == 54
    assert w.message_text(278) in out


def test_ga_vuur_no_cross_when_harnas_not_at_fire():
    # In the harnas but the harnas is not on either fire side (still at its start
    # room 21): GA VUUR performs no fire-cross; the harnas location is unchanged.
    eng, w = _engine(54, placed={HARNAS: 21})
    _run(eng, "ga vuur")
    assert eng.obj_loc[HARNAS] == 21
    assert eng.room == 54


def test_harnas_fire_endgame_reaches_schatkamer():
    # End-to-end: harnas positioned in the kruiskamer (34); DRAAG climbs in (room 54),
    # GA VUUR crosses the fire (harnas -> 35, world[277]), TIL UIT climbs out into the
    # schatkamer (room 35 == loc(HARNAS)) where the schatkist (obj13) lives.
    eng, w = _engine(34, placed={HARNAS: 34})
    _run(eng, "draag harnas")
    assert eng.room == 54
    out = _run(eng, "ga vuur")
    assert w.message_text(277) in out
    assert eng.obj_loc[HARNAS] == 35
    _run(eng, "til uit")
    assert eng.room == 35
    assert eng.obj_loc[SCHATKIST] == 35


def test_ga_vuur_death_unprotected_in_kruiskamer():
    # DEATH branch (0x1a4b): GA VUUR while physically standing in the kruiskamer (34),
    # NOT inside the harnas (player room != 54). No flag/object guard — walking into the
    # fire unprotected disintegrates you. EXE: mov [0xe34],0x119 (K=281 -> world[280]);
    # call 0x5564 (print); jmp 0x3ed3 (game-over hub) -> pr(280) + eng.dead.
    eng, w = _engine(34)
    out = _run(eng, "ga vuur")
    assert w.message_text(280) in out
    assert eng.dead is True


def test_ga_vuur_death_unprotected_in_schatkamer():
    # Same DEATH branch fires from the schatkamer side (35): after climbing OUT of the
    # harnas into room 35, walking back into the fire on foot kills you identically
    # (0x1a4b guards on room==34 OR room==35, symmetric, no object/flag guard).
    eng, w = _engine(35)
    out = _run(eng, "ga vuur")
    assert w.message_text(280) in out
    assert eng.dead is True


# ------------------------------------------------------------------ LUISTER (listen)
# EXE 0x3a8c (verb LUIST -> jmp 0x3a8c). Ignores the noun; branches on the current
# room ([0xe2e]) in EXE order: room 31 -> world[222] (the sesam-door pounding); room
# 13 -> the herberg two-men conversation counter [0xe9a] (inc, clamp to 3), printing
# world[135+e9a] = 136/137/138 for the 1st/2nd/3rd+ listen; any other room -> world[135]
# ('... absolute stilte ...'). No object or navigation effects; e9a is the only write.
def test_luister_room13_conversation_progression():
    # room 13, four successive LUISTER: 136, 137, 138, 138 (clamp); e9a = 1,2,3,3.
    eng, w = _engine(13)
    out = _run(eng, "luister")
    assert w.message_text(136) in out
    assert eng.state["e9a"] == 1
    out = _run(eng, "luister")
    assert w.message_text(137) in out
    assert eng.state["e9a"] == 2
    out = _run(eng, "luister")
    assert w.message_text(138) in out
    assert eng.state["e9a"] == 3
    out = _run(eng, "luister")
    assert w.message_text(138) in out                 # clamped: repeats forever
    assert eng.state["e9a"] == 3


def test_luister_room13_ignores_noun():
    # The handler branches on the room only; a noun is ignored -> still msg 136.
    eng, w = _engine(13)
    out = _run(eng, "luister mannen")
    assert w.message_text(136) in out
    assert eng.state["e9a"] == 1


def test_luister_room31_pounding():
    # room 31 -> world[222] (the sesam-door pounding); no e9a write.
    eng, w = _engine(31)
    out = _run(eng, "luister")
    assert w.message_text(222) in out
    assert eng.state.get("e9a", 0) == 0


def test_luister_other_room_silence():
    # any other room (e.g. 12) -> world[135] ('... absolute stilte ...'); no e9a write.
    eng, w = _engine(12)
    out = _run(eng, "luister")
    assert w.message_text(135) in out
    assert eng.state.get("e9a", 0) == 0


def test_luister_is_wired_not_unmapped():
    # game.py must dispatch 'luister' to the handler, not the canned _UNMAPPED reply.
    eng, w = _engine(13)
    out = _run(eng, "luister")
    assert w.message_text(136) in out
    assert eng.msg.named("cant") not in out


# ------------------------------------------------------------------ KOOP (buy)
# EXE 0x3a24 (verb KOOP dispatched at 0xd6b-0xd76 -> jmp 0x3a24). KOOP is entirely
# knoflook-framed: it only ever hands over the streng knoflook (obj3, loc-var
# [0xc60], start room 12) and rejects everything else. Branches in EXE order:
#   1 (0x3a24): room != knoflook-loc          -> msg 131 "Ik zie geen knoflook."
#   2 (0x3a39): NOT(noun~KNOF AND room==12)   -> msg 132 "Je kan het gewoon pakken hoor.."
#   3 (0x3a67): KNOF & room 12 & e84>0        -> msg 133 (calms), SET e84=0, no give
#   4 (0x3a80): KNOF & room 12 & e84<=0       -> msg 134 + "streng knoflook : gepakt."
def test_koop_knoflook_not_here_message():
    # Branch 1: KOOP where the garlic is not in the current room (obj3 starts in 12,
    # player in room 0) -> msg 131, no state change.
    eng, w = _engine(0)
    out = _run(eng, "koop knoflook")
    assert w.message_text(131) in out
    assert eng.obj_loc[KNOFLOOK] == 12                 # untouched


def test_koop_non_garlic_in_herberg_take_it_freely():
    # Branch 2: KOOP a non-garlic noun where the garlic lies (room 12) -> msg 132.
    eng, w = _engine(12)
    out = _run(eng, "koop brood")
    assert w.message_text(132) in out
    assert eng.obj_loc[KNOFLOOK] == 12


def test_koop_streng_synonym_rejected():
    # Branch 2: the synonym token 'STRE' (KOOP STRENG) is NOT accepted (the EXE
    # B$SCMP compares against 'KNOF'@0x1586 only) -> msg 132, garlic not bought.
    eng, w = _engine(12)
    out = _run(eng, "koop streng")
    assert w.message_text(132) in out
    assert eng.obj_loc[KNOFLOOK] == 12


def test_koop_knoflook_elsewhere_take_it_freely():
    # Branch 2: KOOP knoflook where the garlic lies in a room != 12 (place it in the
    # current room 5) -> "just pick it up" msg 132, not a buy.
    eng, w = _engine(5, placed={KNOFLOOK: 5})
    out = _run(eng, "koop knoflook")
    assert w.message_text(132) in out
    assert eng.obj_loc[KNOFLOOK] == 5


def test_koop_empty_noun_in_herberg():
    # Branch 2: KOOP alone (no noun) in room 12 -> noun does not prefix-match 'KNOF'
    # -> msg 132.
    eng, w = _engine(12)
    out = _run(eng, "koop")
    assert w.message_text(132) in out


def test_koop_knoflook_angry_waard_calms_first():
    # Branch 3: KOOP knoflook in room 12 with the waard angry (e84>0) -> msg 133,
    # e84 cleared, garlic NOT handed over this turn.
    eng, w = _engine(12)
    eng.state["e84"] = 1
    out = _run(eng, "koop knoflook")
    assert w.message_text(133) in out
    assert eng.state["e84"] == 0
    assert eng.obj_loc[KNOFLOOK] == 12                 # still in the herberg


def test_koop_knoflook_calm_waard_buys_it():
    # Branch 4: KOOP knoflook in room 12 with a calm waard (e84<=0) -> msg 134 THEN the
    # generic take (0x3a80 -> 0x1dcc) prints "Ok"; garlic now carried.
    eng, w = _engine(12)
    assert eng.state["e84"] == 0                        # default calm
    out = _run(eng, "koop knoflook")
    assert w.message_text(134) in out
    assert EXE.OK_TAKE in out
    assert eng.obj_loc[KNOFLOOK] == CARRIED


def test_koop_knoflook_two_step_when_angry():
    # The angry->calm->buy sequence: a first KOOP only calms (garlic stays), a second
    # KOOP (now e84==0) actually buys it. Faithful to branch 3 returning before give.
    eng, w = _engine(12)
    eng.state["e84"] = 2
    _run(eng, "koop knoflook")
    assert eng.obj_loc[KNOFLOOK] == 12                 # first KOOP: not yet bought
    assert eng.state["e84"] == 0
    out = _run(eng, "koop knoflook")
    assert w.message_text(134) in out
    assert eng.obj_loc[KNOFLOOK] == CARRIED            # second KOOP: bought


def test_koop_is_wired_not_unmapped():
    # game.py must dispatch 'koop' to the handler, not the canned _UNMAPPED reply.
    from engine.game import _UNMAPPED
    assert "koop" not in _UNMAPPED
    eng, w = _engine(12)
    out = _run(eng, "koop knoflook")
    assert eng.msg.named("cant") not in out


# ------------------------------------------------------------- BLAAS (blow dust)
# EXE handler 0x1b11: BLAAS STOF/KIST in room 14 (herberg zolder) reveals the book.
# Success iff room==14 AND noun in {STOF,KIST}; else msg 211 'pffffff'. On success,
# if the dusty chest (obj24) is still in room 14 -> msg 20, obj24->99, obj25->14;
# if already blown (obj24 loc != 14) -> msg 19 'Er is niets stoffigs hier.'.
def test_blaas_stof_reveals_book_chest():
    eng, w = _engine(14)
    out = _run(eng, "blaas stof")
    assert eng.obj_loc[KIST_STOF] == LOC_NOWHERE   # obj24 consumed
    assert eng.obj_loc[KIST_BOEK] == 14            # obj25 revealed into room 14
    assert w.message_text(20) in out               # "Onder het stof komt een boek..."


def test_blaas_kist_noun_also_reveals():
    # The KIST noun path (0x154c) triggers the same reveal as STOF (0x1554).
    eng, w = _engine(14)
    out = _run(eng, "blaas kist")
    assert eng.obj_loc[KIST_STOF] == LOC_NOWHERE
    assert eng.obj_loc[KIST_BOEK] == 14
    assert w.message_text(20) in out


def test_blaas_already_blown_nothing_dusty():
    # obj24 already gone from room 14 -> msg 19, obj25 NOT placed (stays 99).
    eng, w = _engine(14, placed={KIST_STOF: LOC_NOWHERE})
    out = _run(eng, "blaas stof")
    assert w.message_text(19) in out               # "Er is niets stoffigs hier."
    assert eng.obj_loc[KIST_BOEK] == 99             # unchanged
    assert eng.obj_loc[KIST_STOF] == LOC_NOWHERE


def test_blaas_wrong_room_pffff():
    eng, w = _engine(0)
    out = _run(eng, "blaas stof")
    assert w.message_text(211) in out               # "pffffff"
    assert eng.obj_loc[KIST_STOF] == 14             # no state change
    assert eng.obj_loc[KIST_BOEK] == 99


def test_blaas_no_noun_pffff():
    eng, w = _engine(14)
    out = _run(eng, "blaas")
    assert w.message_text(211) in out               # "pffffff"
    assert eng.obj_loc[KIST_STOF] == 14             # no state change


def test_blaas_is_wired_not_unmapped():
    from engine.game import _UNMAPPED
    assert "blaas" not in _UNMAPPED
    eng, w = _engine(14)
    out = _run(eng, "blaas stof")
    assert eng.msg.named("cant") not in out


def test_blaas_then_pak_boek_takes_the_book():
    # Downstream: once BLAAS reveals the book-chest (obj25 -> room 14), the
    # already-wired PAK BOEK row 3 takes the book (obj25 -> 99, obj4 -> CARRIED).
    eng, w = _engine(14)
    _run(eng, "blaas stof")
    out = _run(eng, "pak boek")
    assert eng.obj_loc[KIST_BOEK] == LOC_NOWHERE
    assert eng.obj_loc[BOEK] == CARRIED
    assert EXE.OK in out


# --------------------------------- winnability fixes (verify-playthrough breaks)
def test_ga_luik_descends_room1_to_kelder():
    # EXE 0x39b0: GA LUIK in the slaapkamer drops to the kelder (room 4) once the
    # hatch is revealed (e86!=0); otherwise "Welk luik bedoel je ?" and no move.
    eng, w = _engine(1)
    eng.state["e86"] = 0
    assert w.message_text(127) in _run(eng, "ga luik")
    assert eng.room == 1
    eng.state["e86"] = 1
    _run(eng, "ga luik")
    assert eng.room == 4


def test_pak_opened_coffin_empty_handed_takes_it():
    # EXE 0x1d66: at the opened coffin, carrying anything -> msg 237 (drop first);
    # empty-handed -> take it + msg 238 "Met veel moeite pak je de kist."
    eng, w = _engine(24, placed={DOODSKIST_OPEN: 24})
    eng.obj_loc[LAMP] = CARRIED                 # carrying something
    assert w.message_text(237) in _run(eng, "pak doodskist")
    assert eng.obj_loc[DOODSKIST_OPEN] == 24    # not taken

    eng, w = _engine(24, placed={DOODSKIST_OPEN: 24})
    for oid in list(eng.carried()):
        eng.obj_loc[oid] = 99                   # ensure empty-handed
    out = _run(eng, "pak doodskist")
    assert eng.obj_loc[DOODSKIST_OPEN] == CARRIED
    assert w.message_text(238) in out
