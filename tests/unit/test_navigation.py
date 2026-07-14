"""Tests for the opt-in reconstructed named-place navigation (explore mode)."""
from engine.data.loader import load_file
from engine.game import new_game
from engine.io import ScriptedIO
from engine.navigation import build_named_entries, resolve_named_place


def test_named_entries_key_cases():
    w = load_file()
    e = build_named_entries(w)
    assert resolve_named_place(e, 11, "herberg") == 12
    assert resolve_named_place(e, 19, "kasteel") == 20
    assert resolve_named_place(e, 0, "zolder") == 3
    assert resolve_named_place(e, 1, "kelder") == 4


def test_faithful_default_enters_recovered_named_place():
    # GA HERBERG (room 11 -> 12) is a RECOVERED faithful transition (VERIFIED_NAMED),
    # so it works in the default engine WITHOUT explore mode — matching the live game.
    io = ScriptedIO([])
    eng = new_game(io)            # explore defaults False
    eng.room = 11
    eng.submit("ga herberg")
    assert eng.room == 12
    assert "herberg de zwarte hand" in io.text


def test_faithful_default_rejects_unrecovered_named_place():
    # A named place NOT in the recovered table is still blocked in faithful mode
    # (only the opt-in explore heuristic would guess at it).
    io = ScriptedIO([])
    eng = new_game(io)
    eng.room = 1
    eng.submit("ga kelder")       # 'kelder' from room 1 is only a heuristic guess
    assert eng.room == 1
    assert "Daar kan je niet heen." in io.text


def test_explore_mode_enters_named_place():
    io = ScriptedIO([])
    eng = new_game(io, explore=True)
    eng.room = 11
    eng.submit("ga herberg")
    assert eng.room == 12
    assert "herberg de zwarte hand" in io.text


def test_explore_mode_betreed_synonym():
    io = ScriptedIO([])
    eng = new_game(io, explore=True)
    eng.room = 19
    eng.submit("betreed kasteel")
    assert eng.room == 20


def test_ga_bron_reaches_open_bos_when_tower_viewed():
    # GA BRON from the dorpsstraat (room 11) with the tower-roof latch [0xe6c]==1
    # opens the forest path to the open bos (room 15). EXE handler 0x3974 -> 0x397e.
    w = load_file()
    io = ScriptedIO([])
    eng = new_game(io)
    eng.state["e6c"] = 1                 # room-28 (glibberige torendak) already viewed
    eng.room = 11
    eng.submit("ga bron")
    assert eng.room == 15
    assert w.rooms[15].description in io.text     # room-15 static text, no extra message


def test_ga_bron_without_tower_view_gets_lost():
    # Without the latch (e6c==0, the init default) GA BRON in room 11 prints
    # messages[126] and random-teleports (EXE 0x3987). The exact 'lost' room is a
    # runtime QB array (0x101c), not statically recoverable, so we assert only the
    # message and that the player left room 11.
    w = load_file()
    io = ScriptedIO([])
    eng = new_game(io)
    assert eng.state["e6c"] == 0
    eng.room = 11
    eng.submit("ga bron")
    assert w.message_text(126) in io.text         # "Je raakt helemaal de weg kwijt..."
    assert eng.room != 11


def test_tower_view_latch_enables_bron_path():
    # Full walkthrough chain: GA RAAM from the kasteeltoren (29) describes the
    # glibberige torendak (28), which latches e6c (room_events #5); from then on
    # GA BRON in the dorpsstraat (11) reaches the open bos (15).
    io = ScriptedIO([])
    eng = new_game(io)
    eng.room = 29
    eng.submit("ga raam")
    assert eng.room == 28
    assert eng.state["e6c"] == 1
    eng.room = 11
    eng.submit("ga bron")
    assert eng.room == 15


def test_open_bos_east_reaches_waterbron_room():
    # Room 15 OOST -> room 16 (the waterbron/puzzle room) and room 16 WEST -> 15 are
    # plain exit-table entries; verify room 16 (GOOI MUNT / VUL FLES) is reachable.
    io = ScriptedIO([])
    eng = new_game(io)
    eng.room = 15
    eng.submit("ga oost")
    assert eng.room == 16
    eng.submit("ga west")
    assert eng.room == 15


def test_movement_synonym_routes_bron_special():
    # The parser maps KLIM/LOOP/BETRE/KRUIP/VOLG to verb 'ga', so BRON fires the
    # room-11 special for every movement verb (mirrors the EXE ga handler).
    io = ScriptedIO([])
    eng = new_game(io)
    eng.state["e6c"] = 1
    eng.room = 11
    eng.submit("klim bron")
    assert eng.room == 15


# --- VOLG / GA DRACULA — follow Dracula in the endgame chase --------------------
# EXE ga-handler DRAC/MAN follow block (@0x192a) + entry precondition (@0xe3e).
# Recovered statically from DRACULA.EXE; strings read from the loaded world.

def test_volg_dracula_follows_into_his_room():
    # DRAC/MAN block (0x192a): when de0==current room, VOLG/GA DRACULA moves the
    # player into Dracula's room [0xdde] and redescribes (no message). The following
    # end_of_turn patrol then steps Dracula one room further on.
    io = ScriptedIO([])
    eng = new_game(io)
    eng.room = 37
    eng.state["de0"] = 37          # Dracula just stepped away from room 37...
    eng.state["dde"] = 32          # ...into room 32
    eng.state["e76"] = 1           # chase active -> end_of_turn patrol advances him
    eng.submit("volg dracula")
    assert eng.room == 32          # followed into Dracula's (vacated) room
    assert eng.state["dde"] == 31  # patrol stepped Dracula 32 -> 31
    assert eng.state["de0"] == 32  # ...leaving room 32 for the next VOLG


def test_ga_man_is_a_follow_synonym():
    # Noun 'MAN' (@0x1534) also triggers the follow (prefix match via noun_is).
    io = ScriptedIO([])
    eng = new_game(io)
    eng.room = 30
    eng.state["de0"] = 30
    eng.state["dde"] = 22
    eng.state["e76"] = 1
    eng.submit("ga man")
    assert eng.room == 22


def test_full_chase_37_to_24_via_volg():
    # OPEN KIST in the graftombe (37) wakes Dracula (verb_events.open_ row 11: e76=1,
    # dde=37); repeated VOLG DRACULA walks the player 37->32->31->30->22->24 as the
    # end_of_turn patrol steps him one room ahead each turn.
    io = ScriptedIO([])
    eng = new_game(io)
    eng.room = 37
    eng.submit("open kist")             # chase-start; patrol then steps dde 37 -> 32
    assert eng.state["e76"] == 1
    rooms = []
    for _ in range(5):
        eng.submit("volg dracula")
        rooms.append(eng.room)
    assert rooms == [32, 31, 30, 22, 24]
    assert not eng.dead and not eng.won


def test_room24_confrontation_blocks_all_movement():
    # Entry precondition (0xe3e): room==[0xdde] blocks EVERY movement verb and prints
    # messages[228]. Room 24's only directional exit is OMHOOG->29, so without this the
    # player could walk out of the final confrontation.
    w = load_file()
    io = ScriptedIO([])
    eng = new_game(io)
    eng.room = 24
    eng.state["dde"] = 24
    eng.state["e76"] = 1
    eng.submit("ga omhoog")
    assert eng.room == 24
    assert w.message_text(228) in io.text


def test_volg_at_game_start_does_not_crash():
    # Regression: de0 must init to 255 (EXE [0xde0]=0xff @0x27c), not 0. With de0=0 a
    # player in room 0 (de0==room==0) typing VOLG DRACULA satisfies the follow guard
    # and jumps to world.rooms[dde=255] -> KeyError. With de0=255 the follow does not
    # fire and the move is refused.
    io = ScriptedIO([])
    eng = new_game(io)
    assert eng.state["de0"] == 255
    assert eng.room == 0
    eng.submit("volg dracula")          # must not raise
    assert eng.room == 0
    assert "Daar kan je niet heen." in io.text


# --- doodskist climb-in / slide / exit (the winning delivery mechanism) ---------
# EXE ga-handler branches: climb-in 0x1a87 (branch A), slide 0x1ac0 (branch B),
# and the room-38 coffin-interior exit 0x1004. All key on the OPENED doodskist
# (obj38) location [0xca6]; strings read from the loaded world.
DOODSKIST_OPEN = 38


def test_ga_kist_climbs_into_opened_coffin():
    # Branch A (0x1a87): GA KIST with the opened doodskist in the current room and
    # room != 26 -> climb inside (room 38); the coffin does NOT move, no message.
    io = ScriptedIO([])
    eng = new_game(io)
    eng.room = 37
    eng.obj_loc[DOODSKIST_OPEN] = 37             # opened coffin sits in Dracula's room
    eng.submit("ga kist")
    assert eng.room == 38                         # inside the coffin interior
    assert eng.obj_loc[DOODSKIST_OPEN] == 37      # no slide — the coffin stayed put


def test_ga_kist_in_room26_slides_to_village():
    # Branch B (0x1ac0): GA KIST in the ledge room (26) with the opened doodskist
    # there -> it slides down: obj38 -> room 11, slide line messages[279], room 38.
    w = load_file()
    io = ScriptedIO([])
    eng = new_game(io)
    eng.room = 26
    eng.obj_loc[DOODSKIST_OPEN] = 26
    eng.submit("ga kist")
    assert eng.obj_loc[DOODSKIST_OPEN] == 11
    assert w.message_text(279) in io.text
    assert eng.room == 38


def test_kruip_kist_synonym_slides():
    # KRUIP maps to 'ga' in the parser, so KRUIP KIST fires the same slide branch.
    io = ScriptedIO([])
    eng = new_game(io)
    eng.room = 26
    eng.obj_loc[DOODSKIST_OPEN] = 26
    eng.submit("kruip kist")
    assert eng.obj_loc[DOODSKIST_OPEN] == 11
    assert eng.room == 38


def test_ga_kist_without_coffin_present_is_refused():
    # No opened doodskist in the room -> the KIST branch's else fires with msg 18
    # (EXE 0x1b08), NOT the generic cant_go; no movement.
    io = ScriptedIO([])
    eng = new_game(io)
    eng.room = 26                                 # obj38 still at its init loc (99)
    eng.submit("ga kist")
    assert eng.room == 26
    assert eng.world.message_text(18) in io.text


def test_ga_uit_from_coffin_returns_to_its_location():
    # Room-38 exit (0x1004): after a plain climb-in (no slide) GA UIT returns you to
    # the room the coffin still occupies. Must run before exit_to (room-38 slot 6 = 99).
    io = ScriptedIO([])
    eng = new_game(io)
    eng.room = 37
    eng.obj_loc[DOODSKIST_OPEN] = 37
    eng.submit("ga kist")                         # climb in -> room 38
    assert eng.room == 38
    eng.submit("ga uit")                          # climb back out -> room 37
    assert eng.room == 37


def test_explore_reaches_more_rooms_than_directional():
    from collections import deque
    from engine.data.model import NO_EXIT
    w = load_file()
    e = build_named_entries(w)

    def reach(with_nav):
        seen = {0}
        q = deque([0])
        while q:
            r = q.popleft()
            nbrs = [d for d in w.rooms[r].exits if d != NO_EXIT and d in w.rooms]
            if with_nav:
                nbrs += [dest for (frm, k), dest in e.items() if frm == r]
            for d in nbrs:
                if d not in seen:
                    seen.add(d)
                    q.append(d)
        return seen

    assert len(reach(False)) < len(reach(True))
