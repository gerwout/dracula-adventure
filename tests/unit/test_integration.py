"""Integration-level checks over the whole decoded world + engine."""
from collections import deque

from engine.data.loader import load_file
from engine.data.model import NO_EXIT
from engine.game import new_game
from engine.io import ScriptedIO


def _reachable(world, start=0):
    seen = {start}
    q = deque([start])
    while q:
        r = q.popleft()
        for dest in world.rooms[r].exits:
            if dest != NO_EXIT and dest in world.rooms and dest not in seen:
                seen.add(dest)
                q.append(dest)
    return seen


def test_directional_reachability_is_stable():
    # Regression guard: 11 rooms reachable by pure directional movement from the
    # house. (The rest are gated behind special-event navigation — see STATUS.md.)
    w = load_file()
    assert len(_reachable(w)) == 11


def test_no_exit_points_to_placeholder_or_missing_room():
    w = load_file()
    for r in w.rooms.values():
        for dest in r.exits:
            if dest != NO_EXIT:
                assert dest in w.rooms


def test_walkthrough_route_follows_exit_table():
    # Driving a direction must land in exactly the exit-table destination.
    from engine.parser import direction_index
    io = ScriptedIO([])
    eng = new_game(io)
    for cmd in ["zuid", "noord", "west", "noord", "zuid", "noord"]:
        d = direction_index(cmd)
        expected = eng.world.rooms[eng.room].exit_to(d)
        if expected is None:
            continue
        eng.submit(f"ga {cmd}")       # full-word directions require GA
        assert eng.room == expected, f"{cmd!r} should go to {expected}, got {eng.room}"


def test_kelder_to_castle_dig_tunnel_route_is_traversable():
    # End-to-end regression guard for the GRAAF dig-tunnel network + DUW STEE route
    # (docs/verb-events.md §GRAAF/§DUW, navigation.VERIFIED_NAMED 39->37). Drives the
    # full player-facing turn loop (eng.submit, incl. end-of-turn) from the kelder
    # (room 4) through the sand tunnels into the graftombe under the castle (room 37),
    # then back up, then on into the castle gewelf (room 32). Expected room text is
    # read from the decoded world, never hardcoded.
    from engine.verb_events import SCHEP
    io = ScriptedIO([])
    eng = new_game(io)
    eng.obj_loc[SCHEP] = 200          # the schep must be carried to dig (row-1 gate)
    eng.room = 4                       # start in the kelder (dig-tunnel head)

    # Down the tunnel: 4 -(GRAAF any dir)-> 5 -(GRAAF N)-> 39.
    eng.submit("graaf west")
    assert eng.room == 5, "GRAAF from the kelder must tunnel down to the zandtunnel (5)"
    eng.submit("graaf noord")
    assert eng.room == 39, "GRAAF noord from the tunnel must reach the hard obstruction (39)"

    # The grave passage is shut until the stone is rotated.
    eng.submit("ga steen")
    assert eng.room == 39, "GA STEE before DUW must not move (39<->37 passage still shut)"
    eng.submit("duw steen")
    assert eng.state["e42"] == 1, "DUW STEE @ 39 must set e42 (opens the grave passage)"

    # Now the passage is open: 39 -> 37 (graftombe under the castle). The EXE prints
    # msg 16 (the stone slams shut behind you) and does NOT redescribe room 37 (0x16b9).
    io2 = ScriptedIO([]); eng.io = io2
    eng.submit("ga steen")
    assert eng.room == 37, "GA STEE after DUW must cross into the graftombe (37)"
    assert eng.world.message_text(16) in io2.text, "the stone slams shut (msg 16)"
    assert eng.world.rooms[37].lines[0] not in io2.text, "GA STEE does not redescribe 37"

    # Return path up the tunnel: 39 -zuid-> 5 -zuid-> 4 -omhoog-> 1.
    eng.room = 39
    eng.submit("ga zuid"); assert eng.room == 5, "39 zuid must return to the tunnel (5)"
    eng.submit("ga zuid"); assert eng.room == 4, "5 zuid must return to the kelder (4)"
    eng.submit("ga omhoog"); assert eng.room == 1, "4 omhoog must return to the slaapkamer (1)"

    # On into the castle from the graftombe: OPEN HEK (e44) then GA HEK -> gewelf (32).
    eng.room = 37
    eng.submit("ga hek"); assert eng.room == 37, "the iron gate is shut until OPEN HEK"
    eng.submit("open hek"); assert eng.state["e44"] == 1
    eng.submit("ga hek"); assert eng.room == 32, "OPEN HEK then GA HEK reaches the gewelf (32)"


def test_endgame_escape_delivers_schatkist_to_village_and_wins():
    # End-to-end composition proof that the game is WINNABLE via the intended escape.
    # After the treasure is in hand (schatkist obj13 carried) with the opened doodskist
    # (obj38) already positioned on the hillside ledge (room 26) from an earlier
    # empty-handed trip, the player rides the coffin home carrying the treasure:
    #   * traverse the castle back to the balcony by pure exit-table movement
    #     34 -west-> 31 -omhoog-> 30 -noord-> 22 -west-> 40 -zuid-> 23 -zuid-> 25,
    #   * KNOOP TOUW ties the rope to the balcony (obj12 -> room 25, flag e92),
    #   * GA TOUW descends the (bidirectional) rope 25 -> 26,
    #   * GA KIST slides the coffin — with the treasure aboard — into the village
    #     (EXE branch B 0x1ac0: obj38 -> room 11, ride inside as room 38),
    #   * GA UIT of the coffin lands in room 11 where end_of_turn Block D (0x2929)
    #     declares the win because the schatkist is carried.
    # The win requires the schatkist carried (Block D checks obj13 == CARRIED), which
    # the slide preserves — this is the only producer of the TROS ending messages[281].
    from engine.data.model import CARRIED
    io = ScriptedIO([])
    eng = new_game(io, explore=True)
    eng.room = 34                      # kruiskamer, just back through the fire
    eng.obj_loc[13] = CARRIED          # the schatkist (the win object)
    eng.obj_loc[1] = CARRIED           # the carryable touw (consumed by KNOOP)
    eng.obj_loc[38] = 26               # opened doodskist waiting on the ledge
    eng.obj_loc[12] = 99               # rope not yet tied to the balcony

    for direction, expect in [("west", 31), ("omhoog", 30), ("noord", 22),
                              ("west", 40), ("zuid", 23), ("zuid", 25)]:
        eng.submit(f"ga {direction}")
        assert eng.room == expect, f"ga {direction} should reach {expect}, got {eng.room}"

    eng.submit("knoop touw")
    assert eng.obj_loc[12] == 25 and eng.state.get("e92") == 1, "KNOOP ties the rope @25"

    eng.submit("ga touw")
    assert eng.room == 26, "GA TOUW descends the tied rope to the ledge (26)"

    eng.submit("ga kist")
    assert eng.room == 38 and eng.obj_loc[38] == 11, "GA KIST slides the coffin to the village"
    assert not eng.won, "still inside the coffin — not won until you climb out"

    io2 = ScriptedIO([]); eng.io = io2
    eng.submit("ga uit")
    assert eng.room == 11
    assert eng.won and not eng.running, "carrying the schatkist into room 11 wins"
    assert eng.world.message_text(281) in io2.text, "the TROS win ending prints"


def test_help_is_a_quip_not_the_rules():
    # HELP is a context quip (EXE 0x3010), not the "Spelregels" block. In normal play
    # (castle door still open) it is msg 89. The rules block is LEES BRIEFJE only.
    io = ScriptedIO(["help", "stop"])
    eng = new_game(io)
    eng.play()
    assert "Geen paniek..geen paniek.." in io.text
    assert "Spelregels van DRACULA ADVENTURE" not in io.text


def test_lees_briefje_shows_rules():
    # The "Spelregels" rules block is reached via LEES BRIEFJE (msg 201).
    io = ScriptedIO(["lees briefje", "stop"])
    eng = new_game(io)
    eng.play()
    assert "Spelregels van DRACULA ADVENTURE" in io.text
    assert "Velen hebben reeds getracht" in io.text


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    import engine.game as gmod
    monkeypatch.setattr(gmod, "SAVE_PATH", tmp_path / "save.json")
    io = ScriptedIO([])
    eng = new_game(io)
    eng.submit("ga zuid")
    eng.submit("pak lamp")
    eng.submit("bewaar")
    room_before, held_before = eng.room, sorted(eng.carried())
    # move on, then load should restore
    eng.submit("n")
    eng.submit("laad")
    assert eng.room == room_before
    assert sorted(eng.carried()) == held_before
