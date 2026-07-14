"""The parser-failure ("nothing matched") response — a faithful port of the
DRACULA.EXE no-match handler (0x0dba; see docs/parser-failure.md).

These pin the MECHANISM (random pool messages[6..9], room-0 help escalation, the
room-31 special, counter reset on a recognised command). The exact random *sequence*
for a specific playthrough additionally requires the full whole-game RND-draw order
(describes + end-of-turn + failures share one BASRUN RND stream) and is not asserted
here — see docs/parser-failure.md §4.5 and the bird bit-exact test for the RND itself.
"""
from engine.data.loader import load_file
from engine.game import new_game
from engine.io import ScriptedIO


def _run(cmds, room=0):
    io = ScriptedIO([])
    eng = new_game(io)
    eng.room = room
    outs = []
    for c in cmds:
        io.output.clear()
        eng.submit(c)
        outs.append(io.text.strip())
    return eng, outs


def test_unrecognised_input_uses_the_messages_6_to_9_pool():
    world = load_file()
    pool = {world.message_text(i) for i in (6, 7, 8, 9)}
    _eng, outs = _run(["flauwekul", "onzin", "xyzzy"])
    for o in outs:
        assert o in pool, o


def test_help_block_escalates_on_the_fourth_failure_in_room_0():
    world = load_file()
    eng, outs = _run(["flauwekul"] * 5)
    help_text = world.message_text(230)
    assert outs[3] == help_text                       # 4th consecutive failure -> help
    assert outs[0] != help_text and outs[4] != help_text
    assert eng.fail_counter == 1                       # reset on help, then the 5th +1


def test_recognised_command_resets_the_failure_counter():
    eng, _ = _run(["flauwekul", "flauwekul"])
    assert eng.fail_counter == 2
    eng.submit("kijk")                                 # a recognised verb
    assert eng.fail_counter == 0


def test_help_block_is_room_0_only():
    # In a non-0, non-31 room the counter still climbs but the help never fires.
    world = load_file()
    eng, outs = _run(["flauwekul"] * 6, room=2)
    assert world.message_text(230) not in outs
    assert eng.fail_counter == 6


def test_room_31_special_line():
    world = load_file()
    _eng, outs = _run(["flauwekul"], room=31)
    assert outs[0] == world.message_text(267)          # room-31 flavour, no pool/help
