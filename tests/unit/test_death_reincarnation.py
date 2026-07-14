"""Death -> the J/N reincarnation prompt (EXE 0x3ed3 hub -> 0x3eff restart).

On death the game prints the 'dodenrijk' + reincarnate prompt (messages[166]) and
reads a J/N answer:
  * the localized 'no' letter (lexicon answers.no, Dutch 'N') ends the game;
  * anything else prints POEFF (messages[167]) and fully restarts to the start room
    with default state — the faithful equivalent of the EXE INT 3Eh fn 0x0d restart.
The answer letters come from the lexicon, so a translation (English Y/N) applies with
no code change. Verified against DRACULA.EXE (0x3ed3 hub, N-compare const 0x13cc).
"""
import pytest

from engine.data.loader import load_file
from engine.data.model import CARRIED
from engine.game import Engine, START_ROOM
from engine.io import ScriptedIO

LAMP = 0   # obj0, carried at start of a fresh game? use a concrete object we place


class _FakeRNG:
    def __init__(self, values):
        self.values = list(values)

    def _next(self):
        return self.values.pop(0) if self.values else 0.0

    def random(self):
        return self._next()

    def rnd(self, x=1.0):
        return self._next()


def _death_engine(room, rng=None, **flags):
    eng = Engine(load_file(), ScriptedIO([]))
    eng.room = room
    if rng is not None:
        eng.rng = rng
    eng.state.update(flags)
    return eng


# Every death path that can end the game, and the command that triggers it. The J/N
# reincarnation prompt is a single shared hub (Engine._game_over), so this replays them
# all and confirms each honours a SINGLE keypress (no Enter) -- like the original.
_DEATH_SCENARIOS = [
    ("balcony jump",  lambda: (_death_engine(25), "spring")),
    ("kruiskamer fire", lambda: (_death_engine(34), "ga vuur")),
    ("innkeeper knife", lambda: (_death_engine(12, rng=_FakeRNG([0.5])), "dood waard")),
]


@pytest.mark.parametrize("name,factory", _DEATH_SCENARIOS,
                         ids=[s[0] for s in _DEATH_SCENARIOS])
def test_every_death_reincarnates_on_a_single_J_keypress(name, factory):
    eng, cmd = factory()
    w = eng.world
    eng.io = ScriptedIO(["j"])           # exactly ONE key queued -- no Enter, no 2nd read
    eng.submit(cmd)
    assert eng.dead is False, name        # the death was consumed by the reincarnation
    assert w.message_text(166) in eng.io.text, name   # the 'toets J of N' prompt
    assert w.message_text(167) in eng.io.text, name   # POEFF -> the single 'J' acted
    assert eng.restart and eng.running, name          # full restart armed
    # The prompt read exactly ONE key: the queue is empty, and it never had to read a
    # second time (which is what "press Enter after J" would require).
    assert eng.io._commands == [], name


@pytest.mark.parametrize("name,factory", _DEATH_SCENARIOS,
                         ids=[s[0] for s in _DEATH_SCENARIOS])
def test_every_death_ends_the_game_on_N(name, factory):
    eng, cmd = factory()
    w = eng.world
    eng.io = ScriptedIO(["n"])
    eng.submit(cmd)
    assert w.message_text(166) in eng.io.text, name
    assert w.message_text(167) not in eng.io.text, name   # 'N' -> no POEFF, no restart
    assert eng.dead and not eng.running, name


def _dead_engine(answers):
    """A fresh engine standing on the fatal balcony (room 25); SPRING there is a
    lethal jump (EXE 0x2b84 -> hub 0x3ed3). ``answers`` feeds the J/N prompt (submit
    is called with the literal 'spring', so the io queue holds only the answer)."""
    eng = Engine(load_file(), ScriptedIO([]))
    eng.room = 25
    eng.io = ScriptedIO(list(answers))
    return eng, eng.world


def test_no_answer_ends_the_game():
    eng, w = _dead_engine(["n"])
    eng.submit("spring")
    assert w.message_text(218) in eng.io.text      # the balcony death line
    assert w.message_text(166) in eng.io.text      # the reincarnate prompt
    assert w.message_text(167) not in eng.io.text  # NO POEFF — we did not reincarnate
    assert eng.dead and not eng.running


def test_yes_answer_reincarnates_and_restarts():
    eng, w = _dead_engine(["j"])
    eng.submit("spring")
    assert w.message_text(166) in eng.io.text      # the prompt
    assert w.message_text(167) in eng.io.text      # POEFF — the reincarnation line
    assert eng.running                              # the game keeps going
    assert not eng.dead
    assert eng.room == START_ROOM                   # full restart back to the house
    # A full restart: signal the frontend to re-show the opening title screen rather
    # than dropping straight into the room (the EXE re-enters init, showing 0x52df).
    assert eng.restart


def test_reincarnation_replays_the_opening_title_screen(monkeypatch):
    # The play() loop treats reincarnation as a full restart: it re-shows the opening
    # press-a-key title screen (EXE INT 3Eh fn 0x0d -> re-init -> 0x52df) before
    # resuming, instead of jumping straight back into the room.
    eng = Engine(load_file(), ScriptedIO([]))
    # Each fresh screen starts on the fatal balcony so a bare 'spring' kills at once.
    orig_start = eng.start

    def start_on_balcony():
        eng.room = 25
        orig_start()

    monkeypatch.setattr(eng, "start", start_on_balcony)
    # spring (die) -> J (reincarnate) -> spring (die again) -> N (quit for real)
    eng.io = ScriptedIO(["spring", "j", "spring", "n"])
    eng.play()
    press_key = "Druk een toets om te beginnen"
    # the title screen appears TWICE: the initial screen + the reincarnation restart
    assert eng.io.text.count(press_key) == 2
    assert not eng.running


def test_any_non_no_answer_reincarnates():
    # The EXE only tests the 'no' letter; everything else reincarnates.
    for ans in (["ja"], ["x"], ["garbage"]):
        eng, w = _dead_engine(ans)
        eng.submit("spring")
        assert w.message_text(167) in eng.io.text
        assert eng.running and not eng.dead


def test_exhausted_input_ends_the_game():
    # ScriptedIO with nothing queued returns the "stop" sentinel -> end (no reincarnate),
    # preserving the pre-existing death behaviour for headless/scripted play.
    eng, w = _dead_engine([])
    eng.submit("spring")
    assert w.message_text(166) in eng.io.text
    assert w.message_text(167) not in eng.io.text
    assert eng.dead and not eng.running


def test_reincarnation_resets_inventory_and_state():
    eng, w = _dead_engine(["j"])
    # Carry something and dirty some state before dying.
    some_obj = next(oid for oid, o in w.objects.items() if o.is_real)
    eng.obj_loc[some_obj] = CARRIED
    eng.fail_counter = 3
    eng.submit("spring")
    # After reincarnation every object is back at its start location (nothing carried).
    assert eng.obj_loc[some_obj] == w.objects[some_obj].location
    assert eng.carried() == []
    assert eng.fail_counter == 0


def test_no_letter_comes_from_the_lexicon_not_hardcoded():
    # Retarget the 'no' letter (as a translation would) and confirm the engine honours
    # it: 'x' now ends the game, while the old Dutch 'n' would reincarnate.
    eng, w = _dead_engine(["x"])
    eng.lex.apply_overrides(answers={"no": "X"})
    eng.submit("spring")
    assert eng.dead and not eng.running            # 'x' is the new 'no' -> ends

    eng2, w2 = _dead_engine(["n"])
    eng2.lex.apply_overrides(answers={"no": "X"})
    eng2.submit("spring")
    assert eng2.running and not eng2.dead           # 'n' is no longer 'no' -> reincarnates
