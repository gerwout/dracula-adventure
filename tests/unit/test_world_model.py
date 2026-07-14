"""Round-trip tests for World.to_dict()/from_dict() (the world.json (de)serialiser)."""
import json

from engine.data.model import GameObject, Room, World


def _tiny_world() -> World:
    rooms = {
        0: Room(id=0, exits=[1, 255, 255, 255, 255, 255, 255],
                lines=["de hal", "een lange gang"], first_record=101),
        1: Room(id=1, exits=[255, 0, 255, 255, 255, 255, 255],
                lines=["een kamer"], first_record=102),
    }
    messages = {0: ["hallo"], 1: ["met een \x00 blad"]}   # msg 1 carries an embedded NUL
    objects = {
        0: GameObject(id=0, tokens=["LANT"], name="lantaarn", attribute=3,
                      location=0, raw_text="/LANTlantaarn"),
        1: GameObject(id=1, tokens=[], name="~een lege plek", attribute=0,
                      location=99, raw_text=""),
    }
    return World(rooms=rooms, messages=messages, objects=objects,
                 header=[1, 101, 201, 301, 401])


def test_world_roundtrips_through_dict():
    w = _tiny_world()
    w2 = World.from_dict(w.to_dict())
    assert w2.rooms == w.rooms
    assert w2.messages == w.messages
    assert w2.objects == w.objects
    assert w2.header == w.header


def test_to_dict_is_json_native_and_preserves_nul_and_int_keys():
    w = _tiny_world()
    back = World.from_dict(json.loads(json.dumps(w.to_dict(), ensure_ascii=False)))
    assert back.messages[1] == ["met een \x00 blad"]     # NUL survives the JSON round-trip
    assert all(isinstance(k, int) for k in back.rooms)    # keys reconstructed as int
    assert all(isinstance(k, int) for k in back.objects)


def test_to_dict_excludes_raw_bytes():
    w = _tiny_world()
    d = w.to_dict()
    assert set(d) == {"header", "rooms", "messages", "objects"}
