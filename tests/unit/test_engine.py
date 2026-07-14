"""Unit tests for engine mechanics (state transitions, not provisional wording)."""
import pytest

from engine.game import CARRIED, Engine, new_game
from engine.io import ScriptedIO
from engine.messages import Messages


@pytest.fixture
def engine():
    return new_game(ScriptedIO([]))


def test_starts_in_house(engine):
    assert engine.room == 0


def test_movement_updates_room(engine):
    # Full-word directions require GA (bare "zuid" is rejected by the real game);
    # single letters move bare. See parser + test_parser for the verified rule.
    engine.submit("ga zuid")         # house -> slaapkamer
    assert engine.room == 1
    engine.submit("n")               # back to house (single-letter direction)
    assert engine.room == 0
    engine.submit("ga oost")         # -> hal
    assert engine.room == 2


def test_blocked_move_stays_put(engine):
    # house has no north exit
    engine.submit("ga noord")
    assert engine.room == 0


def test_take_and_drop_cycle(engine):
    engine.submit("ga zuid")         # slaapkamer, has the lantern (obj 0)
    engine.submit("pak lantaarn")
    assert 0 in engine.carried()
    assert engine.obj_loc[0] == CARRIED
    engine.submit("drop lantaarn")
    assert 0 not in engine.carried()
    assert engine.obj_loc[0] == 1    # dropped in the slaapkamer


def test_take_carries_between_rooms(engine):
    engine.submit("ga zuid")
    engine.submit("pak lantaarn")
    engine.submit("n")               # carry it to the house
    assert engine.obj_loc[0] == CARRIED
    assert 0 in engine.carried()


def test_object_resolution_by_token_prefix(engine):
    engine.submit("ga zuid")
    assert engine.resolve("lantaarn") == 0   # LANT
    assert engine.resolve("lamp") == 0       # LAMP
    assert engine.resolve("brand") == 0      # BRAN


def test_named_messages_resolve():
    m = Messages(new_game(ScriptedIO([])).world)
    for name in ("cant_go", "dont_understand", "what_mean", "nonsense"):
        assert m.named(name), f"message {name} did not resolve"
