"""Describe-time room-entry events (EXE routine 0x2399), and the message off-by-one.

Verified against the live DOSBox oracle: describing room 0 (the start room) prints,
between the static room text and the object listing, the "gat in het plafond" status
message. That message is world.messages[39] (EXE sets [0xe34]=40; the print routine
0x5564 applies a -1 section base, so EXE value K -> world.messages[K-1]).

Expected strings are read from the loaded world (the gitignored original data), never
hardcoded here, so no copyrighted game text lives in the repo.
"""
from engine.data.loader import load_file
from engine.game import Engine, new_game
from engine.io import ScriptedIO
from engine.room_events import run_room_events


def _describe(engine):
    io = ScriptedIO([])
    engine.io = io
    engine.describe_room()
    return io.text


def test_room0_describe_has_gat_event_between_text_and_objects():
    world = load_file()
    io = ScriptedIO(["stop"])
    new_game(io).play()
    out = io.text

    room0_text = world.rooms[0].description         # 4-line static text
    gat = world.message_text(39)                    # off-by-one-corrected event msg
    assert room0_text in out
    assert gat in out
    # order must be: static room text  ->  gat event  ->  object listing ("... hier.")
    assert out.index(room0_text) < out.index(gat)
    assert out.index(gat) < out.rindex("hier.")


def test_room0_gat_event_flips_with_ladder_flag():
    world = load_file()
    eng = Engine(world, ScriptedIO([]))

    # start state: no ladder placed (e3e == 0) -> "can't reach" message (messages[39])
    assert eng.state.get("e3e", 0) == 0
    out0 = _describe(eng)
    assert world.message_text(39) in out0
    assert world.message_text(40) not in out0

    # ladder placed (e3e == 1) -> "via a ladder you can climb up" (messages[40])
    eng.state["e3e"] = 1
    out1 = _describe(eng)
    assert world.message_text(40) in out1
    assert world.message_text(39) not in out1


def test_run_room_events_is_noop_for_rooms_without_rules():
    world = load_file()
    io = ScriptedIO([])
    run_room_events(1, {}, world, io)      # room 1 has no recovered describe events
    assert io.text == ""


def _events(room, world, **flags):
    from engine.room_events import run_room_events, FLAG_DEFAULTS
    st = dict(FLAG_DEFAULTS)
    st.update(flags)
    io = ScriptedIO([])
    run_room_events(room, st, world, io)          # NullRng -> no random blocks fire
    return io.text, st


def test_describe_chain_castle_door_rooms_20_21():
    # Computed print K = 2*(1-dee)+room+22 -> messages[K-1] (docs/room-events-analysis §4a).
    w = load_file()
    assert w.message_text(41) in _events(20, w, dee=1)[0]   # open
    assert w.message_text(43) in _events(20, w, dee=0)[0]   # closed
    assert w.message_text(42) in _events(21, w, dee=1)[0]
    assert w.message_text(44) in _events(21, w, dee=0)[0]


def test_describe_chain_gates_and_doors():
    w = load_file()
    assert w.message_text(51) in _events(32, w, e44=0)[0]   # gate closed
    assert w.message_text(50) in _events(32, w, e44=1)[0]   # gate open
    out37 = _events(37, w, e44=0)[0]
    assert w.message_text(52) in out37 and w.message_text(53) in out37
    assert w.message_text(55) not in _events(37, w)[0]      # 37 never prints 23's line
    assert w.message_text(54) in _events(23, w, df0=1)[0]   # room-23 door open (init)
    assert w.message_text(55) in _events(23, w, df0=0)[0]


def test_describe_chain_reveal_latches_and_ret():
    w = load_file()
    # room 11 well only after the room-28 latch (e6c) is set
    assert w.message_text(46) not in _events(11, w, e6c=0)[0]
    assert w.message_text(46) in _events(11, w, e6c=1)[0]
    # visiting room 28 sets the latch
    assert _events(28, w)[1]["e6c"] == 1
    # room 40 opens the room-23 door (sets df0) and prints nothing
    txt40, st40 = _events(40, w)
    assert txt40 == "" and st40["df0"] == 1


def test_describe_chain_dracula_presence():
    w = load_file()
    # msgs[49] ("blokkeert alle uitgangen") whenever you're in Dracula's room
    assert w.message_text(49) in _events(30, w, dde=30, e76=0)[0]
    assert w.message_text(49) not in _events(30, w, dde=255)[0]   # absent -> silent


def test_random_blocks_do_not_fire_under_nullrng():
    # NullRng returns 1.0 -> bird (RND>1.6) and Dracula spawn (RND<=0.6) both suppressed.
    w = load_file()
    assert w.message_text(45) not in _events(8, w)[0]            # no bird
    assert _events(25, w, e72=1)[1]["dde"] == 255                # no spawn


def test_bird_ambient_matches_live_game_bit_exact():
    # VERIFIED against the live DOSBox game (seed 5, two RND draws per describe):
    # re-describing room 11 shows the "vogel fluiten" bird exactly on describes
    # #4 and #10 of a fresh game — reproduced here by BasrunRNG + run_room_events.
    from engine.rng import BasrunRNG
    from engine.room_events import run_room_events, FLAG_DEFAULTS
    w = load_file()
    rng = BasrunRNG()                                   # seed 5, as the game starts
    birds = []
    for describe in range(1, 13):
        io = ScriptedIO([])
        run_room_events(11, dict(FLAG_DEFAULTS), w, io, rng)   # shared rng stream
        if "vogel fluiten" in io.text:
            birds.append(describe)
    assert birds == [4, 10, 12], birds


def test_message_off_by_one_index_39_is_the_gat_text():
    # Pin the off-by-one: the ceiling-hole text is at world.messages[39] (record 240),
    # i.e. what the EXE prints with [0xe34]=40. If someone "fixes" the loader base or
    # drops the -1, this catches the regression.
    world = load_file()
    assert "gat in het plafond" in world.message_text(39)
    assert "ladder" in world.message_text(40).lower()
