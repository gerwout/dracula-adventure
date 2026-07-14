"""Drop-and-remember: the world remembers where every object lies.

In the original DRACULA.EXE an object's location lives in the per-object location
array ([0xc5a + 2*k]); PAK sets it to -1 (CARRIED), LEG/GOOI set it to the current
room, and the room-describe lists every object whose location == the current room.
Dropping an item, walking away and returning must therefore find it exactly where it
was left, ready to be picked up again — the engine keeps the same invariant in
`eng.obj_loc` (CARRIED == 200, LOC_NOWHERE == 99, else a room id; see
engine/data/model.py).

These tests drive real commands through Engine.submit (movement via `ga <dir>`,
drop via LEG and GOOI, take via PAK) and assert on both the observable room-describe
output and the underlying obj_loc, so the "the game remembers object locations"
property is pinned end-to-end, including across a BEWAAR/LAAD save round-trip.

Expected message / object-name strings are read from the loaded world (the gitignored
original data), never hardcoded, matching the rest of the suite. Rooms 0..3 are used
throughout: they are a self-contained house cluster (0 <-oost/west-> 2, 0 <-zuid/
noord-> 1, 0 <-omlaag/omhoog-> 3-ish) far from the Dracula patrol (dde=255) and the
spider room (34), so the end-of-turn routine stays dormant during the walk.
"""
from engine.data.loader import load_file
from engine.data.model import CARRIED, LOC_NOWHERE
from engine.game import Engine
from engine.io import ScriptedIO

# Object loader-indices (verified against the live object table, docs/verb-events.md §1).
LAMP, TOUW, BROOD = 0, 1, 14


def _fresh():
    """A pristine engine on the real game database."""
    return Engine(load_file(), ScriptedIO([]))


def _run(eng, line: str) -> str:
    """Drive one real command line through the full engine (incl. end-of-turn) and
    return everything it printed."""
    eng.io = ScriptedIO([])
    eng.submit(line)
    return eng.io.text


def _here_line(world, oid: int) -> str:
    """The room-describe line for a singular object: 'Er is een <name> hier.'"""
    return f"Er is een {world.objects[oid].display_name} hier."


# --------------------------------------------------------------------------- 1
def test_drop_places_item_in_room_and_describe_lists_it():
    """Carry an item, move to room B, DROP it: obj_loc == B and the room-describe
    now lists it."""
    world = load_file()
    eng = Engine(world, ScriptedIO([]))
    eng.room = 1                                   # bedroom: the lamp starts here
    assert "Ok" in _run(eng, "pak lamp")           # now carried
    assert eng.obj_loc[LAMP] == CARRIED

    _run(eng, "ga noord")                          # room 1 -> 0 (= room B)
    assert eng.room == 0
    out = _run(eng, "leg lamp")                    # DROP into room B
    assert "laten vallen" in out                   # the generic-drop reply
    assert eng.obj_loc[LAMP] == 0                  # remembered at room B

    # The describe now lists it on its own "Er is een ... hier." line.
    assert _here_line(world, LAMP) in _run(eng, "kijk")


# --------------------------------------------------------------------------- 2
def test_drop_leave_return_item_still_there_and_repickable():
    """Move AWAY to room C (item not listed there), then BACK to B: the item is still
    listed in B and can be PAK'd again (obj_loc -> CARRIED)."""
    world = load_file()
    eng = Engine(world, ScriptedIO([]))
    eng.room = 1
    _run(eng, "pak lamp")
    _run(eng, "ga noord")                          # to room 0 (= B)
    _run(eng, "leg lamp")
    assert eng.obj_loc[LAMP] == 0

    away = _run(eng, "ga oost")                    # room 0 -> 2 (= room C)
    assert eng.room == 2
    assert _here_line(world, LAMP) not in away     # not carried along, not in C
    assert eng.obj_loc[LAMP] == 0                  # still remembered at B

    back = _run(eng, "ga west")                    # room 2 -> 0, back to B
    assert eng.room == 0
    assert _here_line(world, LAMP) in back         # STILL there after the round-trip

    out = _run(eng, "pak lamp")                    # and pick-up-able again
    assert "Ok" in out
    assert eng.obj_loc[LAMP] == CARRIED
    # Once taken it is no longer listed on the floor.
    assert _here_line(world, LAMP) not in _run(eng, "kijk")


# --------------------------------------------------------------------------- 3
def test_several_objects_each_remember_their_own_room_leg_and_gooi():
    """Drop three different objects in three different rooms — one via GOOI, the rest
    via LEG — and confirm each independently remembers its own room and is listed
    only there."""
    world = load_file()
    eng = Engine(world, ScriptedIO([]))
    for oid in (LAMP, TOUW, BROOD):                # start with all three in hand
        eng.obj_loc[oid] = CARRIED

    eng.room = 0
    assert "laten vallen" in _run(eng, "leg lamp")     # LEG drop in room 0
    eng.room = 2
    assert "laten vallen" in _run(eng, "gooi touw")    # GOOI drop in room 2 (also drops)
    eng.room = 3
    assert "laten vallen" in _run(eng, "leg brood")    # LEG drop in room 3

    # Each object independently remembers its own room.
    assert eng.obj_loc[LAMP] == 0
    assert eng.obj_loc[TOUW] == 2
    assert eng.obj_loc[BROOD] == 3

    # And each is listed in its room and nowhere else.
    eng.room = 0
    d0 = _run(eng, "kijk")
    assert _here_line(world, LAMP) in d0
    assert _here_line(world, TOUW) not in d0
    assert _here_line(world, BROOD) not in d0

    eng.room = 2
    d2 = _run(eng, "kijk")
    assert _here_line(world, TOUW) in d2
    assert _here_line(world, LAMP) not in d2

    eng.room = 3
    d3 = _run(eng, "kijk")
    assert _here_line(world, BROOD) in d3
    assert _here_line(world, TOUW) not in d3


# --------------------------------------------------------------------------- 4
def test_non_carried_object_stays_in_start_room_and_is_pickupable():
    """The general 'world remembers object locations' property: an object never
    touched stays in its starting room, is listed there, and can be picked up."""
    world = load_file()
    eng = Engine(world, ScriptedIO([]))
    # The rope (obj1) starts in room 3 and has not been touched.
    assert eng.obj_loc[TOUW] == 3
    assert world.objects[TOUW].location == 3       # matches the database start loc

    eng.room = 3
    assert _here_line(world, TOUW) in _run(eng, "kijk")
    assert "Ok" in _run(eng, "pak touw")
    assert eng.obj_loc[TOUW] == CARRIED


# --------------------------------------------------------------------------- 5
def test_dropped_item_survives_save_and_load(tmp_path, monkeypatch):
    """Drop an item, BEWAAR (save), start a fresh game, LAAD (load): the dropped item
    is restored to the room it was left in (not its start room)."""
    import engine.game as game
    monkeypatch.setattr(game, "SAVE_PATH", tmp_path / "DRACULA.SAV.json")
    world = load_file()

    eng = Engine(world, ScriptedIO([]))
    eng.obj_loc[LAMP] = CARRIED
    eng.room = 0
    _run(eng, "leg lamp")                          # drop the lamp in room 0
    assert eng.obj_loc[LAMP] == 0
    _run(eng, "bewaar spel")                       # save
    assert (tmp_path / "DRACULA.SAV.json").exists()

    later = Engine(world, ScriptedIO([]))          # a fresh game
    assert later.obj_loc[LAMP] == 1                # lamp back at its start room (bedroom)
    _run(later, "laad spel")                       # load

    # The save remembered the lamp in room 0, not its start room.
    assert later.obj_loc[LAMP] == 0
    assert later.obj_loc[LAMP] != LOC_NOWHERE
    later.room = 0
    assert _here_line(world, LAMP) in _run(later, "kijk")
