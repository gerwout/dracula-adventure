"""Tests for VERIFIED-from-disassembly behaviour folded into the engine.

Covers two RE findings:
* the room object-listing wording ("Er is een … hier." / "Er zijn …, … hier.");
* the conditional named-navigation transitions, which are faithful and therefore
  active in the DEFAULT engine (no explore mode).
"""
from engine.game import new_game
from engine.io import ScriptedIO
from engine.navigation import VERIFIED_NAMED, resolve_verified


# --------------------------------------------------------- object-listing wording
def test_object_listing_singular_wording():
    io = ScriptedIO([])
    eng = new_game(io)
    # Exactly one named object visible in the current room.
    eng.obj_loc = {35: eng.room}          # 35 = 'klein briefje'
    eng.describe_room()
    assert "Er is een klein briefje hier." in io.text
    assert "Er zijn" not in io.text


def test_object_listing_multiple_objects_one_line_each():
    # VERIFIED against the live game (hal/slaapkamer): each object present is on
    # its OWN line as "Er is een <name> hier." — there is NO comma-joined form.
    io = ScriptedIO([])
    eng = new_game(io)
    eng.obj_loc = {35: eng.room, 0: eng.room}   # 'klein briefje', 'kleine brandende lantaren'
    eng.describe_room()
    assert "Er is een klein briefje hier." in io.text
    assert "Er is een kleine brandende lantaren hier." in io.text
    assert "Er zijn" not in io.text              # no plural-join for singular objects


def test_object_listing_marker_articles():
    # Leading name markers select the article (EXE 0x4f5e): '@' -> plural,
    # '~' -> bare sentence. Object 27 = '@scherven', object 39 = '~De vreemd...'.
    io = ScriptedIO([])
    eng = new_game(io)
    w = eng.world
    if w.objects[27].name.startswith("@"):
        eng.obj_loc = {27: eng.room}
        eng.describe_room()
        assert "Er zijn scherven hier." in io.text
        assert "@" not in io.text                # marker stripped from output
    io2 = ScriptedIO([]); eng2 = new_game(io2)
    if w.objects[39].name.startswith("~"):
        eng2.obj_loc = {39: eng2.room}
        eng2.describe_room()
        bare = w.objects[39].display_name
        assert bare in io2.text
        assert f"Er is een {bare}" not in io2.text
        assert "~" not in io2.text


# ------------------------------------------------- verified conditional navigation
def _state_satisfying(guard):
    """A flag state that makes `guard` (a 'flag<op>value' string) hold."""
    from engine.navigation import _FLAG_INIT
    st = dict(_FLAG_INIT)
    if guard:
        import re
        key, op, val = re.fullmatch(r"(\w+)(==|!=)(-?\d+)", guard).groups()
        st[key] = int(val) if op == "==" else int(val) + 1
    return st


def test_resolve_verified_covers_every_transition():
    # Each recovered transition returns its destination when the guard is satisfied.
    for (room, noun), (dest, guard) in VERIFIED_NAMED.items():
        assert resolve_verified(room, noun.lower(), _state_satisfying(guard)) == dest


def test_resolve_verified_respects_guards():
    # A guarded transition does NOT fire when its flag condition fails.
    from engine.navigation import _guard_ok
    guarded = [(r, n, dest, g) for (r, n), (dest, g) in VERIFIED_NAMED.items() if g]
    assert guarded, "expected some flag-guarded transitions"
    for room, noun, dest, guard in guarded:
        import re
        key, op, val = re.fullmatch(r"(\w+)(==|!=)(-?\d+)", guard).groups()
        bad = dict(_state_satisfying(guard))
        bad[key] = int(val) + (1 if op == "==" else 0)   # break the guard
        assert resolve_verified(room, noun.lower(), bad) is None


def test_verified_sit_down_default_engine():
    io = ScriptedIO([])
    eng = new_game(io)                    # explore defaults False
    eng.room = 12
    eng.submit("ga zitten")               # go-verb + non-direction noun ZITT
    assert eng.room == 13


def test_verified_climb_tree_hut_default_engine():
    for verb in ("ga", "klim"):           # both reach do_go with noun BOOM
        io = ScriptedIO([])
        eng = new_game(io)
        eng.room = 17
        eng.submit(f"{verb} boom")
        assert eng.room == 18


def test_verified_door_stairs_hole_window_default_engine():
    cases = [(27, "ga deur", 21), (21, "ga trap", 22),
             (33, "ga gat", 30), (29, "ga raam", 28)]
    for guard, line, target in cases:
        io = ScriptedIO([])
        eng = new_game(io)
        eng.room = guard
        eng.submit(line)
        assert eng.room == target, f"{line!r} from {guard} should reach {target}"


def test_verified_stand_up_default_engine():
    # The parser routes "ga staan" / "sta op" to the STA verb; do_sta must
    # honour the verified STAA[13]->12 transition on the real command path.
    for line in ("ga staan", "sta op"):
        io = ScriptedIO([])
        eng = new_game(io)
        eng.room = 13
        eng.submit(line)
        assert eng.room == 12, f"{line!r} from room 13 should reach 12"


def test_stand_up_does_nothing_elsewhere():
    io = ScriptedIO([])
    eng = new_game(io)
    eng.room = 0
    eng.submit("ga staan")
    assert eng.room == 0


def test_verified_transition_does_not_fire_from_wrong_room():
    # ZITT only sits you down from the herberg (room 12); elsewhere it is blocked.
    io = ScriptedIO([])
    eng = new_game(io)
    eng.room = 0
    eng.submit("ga zitten")
    assert eng.room == 0
    assert "Daar kan je niet heen." in io.text
