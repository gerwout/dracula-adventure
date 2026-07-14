"""Unit tests for the DRACULA.TXT loader / world model."""
import struct

import pytest

from engine.data.loader import load_file, parse_object_text
from engine.data.model import DIRECTIONS, NO_EXIT


@pytest.fixture(scope="module")
def world():
    return load_file()


def test_header_boundaries(world):
    assert world.header == [101, 201, 701, 801, 1289]


def test_section_sizes(world):
    assert len(world.rooms) == 100          # 100 room slots (0..99)
    assert len(world.messages) == 500       # 500 message slots
    assert len(world.objects) == 100        # 100 object slots


def test_room0_is_the_house(world):
    r = world.rooms[0]
    assert r.lines[0] == "Je bent nu in je eigen huis. Er is een slaapkamer op het zuiden"
    # exits: zuid->1, oost->2, west->11, rest none
    assert r.exits[0] == NO_EXIT            # noord
    assert r.exit_to(1) == 1                # zuid -> slaapkamer
    assert r.exit_to(2) == 2                # oost -> hal
    assert r.exit_to(3) == 11               # west
    assert r.exits[4] == r.exits[5] == r.exits[6] == NO_EXIT


def test_house_slaapkamer_reciprocity(world):
    # house south -> slaapkamer(1); slaapkamer north -> house(0)
    assert world.rooms[0].exit_to(1) == 1
    assert world.rooms[1].exit_to(0) == 0


def test_multiline_description_assembled(world):
    # the house description is 4 lines chained through the continuation pool
    assert len(world.rooms[0].lines) == 4
    assert world.rooms[0].lines[-1] == "Door een raam kan je een bos zien."


def test_object_tokens_and_placement(world):
    lamp = world.objects[0]
    assert lamp.tokens == ["LANT", "BRAN", "LAMP"]
    assert lamp.name == "kleine brandende lantaren"
    assert lamp.location == 1               # starts in the slaapkamer
    assert lamp.attribute == 40


def test_parse_object_text_variants():
    assert parse_object_text("/SCHA/KISTschatkist, vol met munten") == (
        ["SCHA", "KIST"], "schatkist, vol met munten")
    assert parse_object_text("Overbodig voorwerp") == ([], "Overbodig voorwerp")
    assert parse_object_text("/WIG houten wig") == (["WIG"], "houten wig")


def test_all_exit_targets_valid(world):
    for r in world.rooms.values():
        for dest in r.exits:
            if dest != NO_EXIT:
                assert dest in world.rooms


def test_message_zero(world):
    assert world.message_text(0) == "Doe niet zo achterlijk.."


def test_empty_object_slots_are_not_real(world):
    # the trailing all-zero object records must not count as objects in room 0
    assert all(o.is_real for o in world.objects_in(0))
    briefje = [o for o in world.objects_in(0)]
    assert any(o.name == "klein briefje" for o in briefje)


def test_roundtrip_record_count(world):
    # header[4] is the total record count (1289); it round-trips through world.json.
    # The raw byte-length (103168) is asserted by the guarded provenance test in
    # tests/unit/test_world_json.py (that one needs the original file, so it lives there).
    assert world.header[4] == 1289


def test_cp437_decoding(world):
    # ensure decoding does not raise and preserves plain ASCII rooms
    for r in world.rooms.values():
        assert isinstance(r.description, str)


def test_directions_length():
    assert len(DIRECTIONS) == 7
