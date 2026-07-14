"""Per-message coverage: an explicit unit test for every DRACULA.TXT message that the
rest of the suite (including the full playthrough) does NOT already exercise.

Each test drives the exact scenario that emits one otherwise-unshown message and asserts
it appears, using fast direct state setup (the in-memory equivalent of a BEWAAR/LAAD
jump) plus a deterministic RNG for the random-reaction pools. Together with the other
tests this guarantees every reachable message is shown by some test.
"""
from engine.data.model import CARRIED
from engine.data.loader import load_file
from engine.end_of_turn import run_end_of_turn
from engine.game import Engine
from engine.io import ScriptedIO
from engine.verb_events import BIJL_SCHERP, BOEK, HAMER, HARNAS, KNOFLOOK, WIG


class FakeRNG:
    """Deterministic RND: pops scripted values; yields 0.0 once exhausted."""
    def __init__(self, values):
        self.values = list(values)

    def _next(self):
        return self.values.pop(0) if self.values else 0.0

    def random(self):
        return self._next()

    def rnd(self, x=1.0):
        return self._next()


def _eng(room=0, rng=None, **flags):
    eng = Engine(load_file(), ScriptedIO([]))
    eng.room = room
    if rng is not None:
        eng.rng = rng
    eng.state.update(flags)
    return eng, eng.world


def _run(eng, cmd):
    io = ScriptedIO([])
    eng.io = io
    eng.submit(cmd)
    return io.text


# --------------------------------------------------------------- easy generics
def test_msg200_drop_without_a_noun():
    eng, w = _eng()
    assert w.message_text(200) in _run(eng, "leg")


def test_msg247_pak_something_already_in_hand():
    eng, w = _eng(1)
    eng.obj_loc[0] = CARRIED                       # the lamp (obj0), already carried
    assert w.message_text(247) in _run(eng, "pak lamp")


def test_msg282_open_the_already_open_front_door():
    eng, w = _eng(0)
    assert w.message_text(282) in _run(eng, "open deur")


def test_msg262_stake_at_dracula_without_the_wedge():
    eng, w = _eng(24, dde=24, e76=1, e70=1)        # the room-24 confrontation
    eng.obj_loc[HAMER] = CARRIED                    # hammer in hand, but NOT the wig
    assert w.message_text(262) in _run(eng, "sla wig")


# ----------------------------------------- DOOD WAARD pool (k=int(RND*5)+141, pr k-1)
def test_msg141_dood_waard_reaction():
    eng, w = _eng(12, rng=FakeRNG([0.25]))          # int(1.25)=1 -> k=142 -> msg 141
    assert w.message_text(141) in _run(eng, "dood waard")


def test_msg143_dood_waard_reaction():
    eng, w = _eng(12, rng=FakeRNG([0.65]))          # int(3.25)=3 -> k=144 -> msg 143
    assert w.message_text(143) in _run(eng, "dood waard")


def test_msg144_dood_waard_reaction():
    eng, w = _eng(12, rng=FakeRNG([0.85]))          # int(4.25)=4 -> k=145 -> msg 144
    assert w.message_text(144) in _run(eng, "dood waard")


# ------------------------------- GOOI BIJL subsequent hit (k=193+int(RND*3), pr k-1)
def test_msg193_gooi_bijl_at_angry_waard():
    eng, w = _eng(12, e84=1, rng=FakeRNG([0.5]))    # int(1.5)=1 -> k=194 -> msg 193
    eng.obj_loc[BIJL_SCHERP] = CARRIED
    assert w.message_text(193) in _run(eng, "gooi bijl")


def test_msg194_gooi_bijl_at_angry_waard():
    eng, w = _eng(12, e84=1, rng=FakeRNG([0.8]))    # int(2.4)=2 -> k=195 -> msg 194
    eng.obj_loc[BIJL_SCHERP] = CARRIED
    assert w.message_text(194) in _run(eng, "gooi bijl")


# ---------------------------- BEKIJK RAAM, kasteeltoren (room 29): pr(219+int(RND*3))
def test_msg220_moonless_window_view():
    eng, w = _eng(29, rng=FakeRNG([0.4]))           # int(1.2)=1 -> msg 220
    assert w.message_text(220) in _run(eng, "bekijk raam")


def test_msg221_moonlit_window_view():
    eng, w = _eng(29, rng=FakeRNG([0.7]))           # int(2.1)=2 -> msg 221
    assert w.message_text(221) in _run(eng, "bekijk raam")


# ------------------------ visor view from inside the harnas (room 54): pr(225+int*3)
def test_msg226_visor_view():
    eng, w = _eng(54, rng=FakeRNG([0.4]))           # int(1.2)=1 -> msg 226
    eng.obj_loc[HARNAS] = 21
    assert w.message_text(226) in _run(eng, "bekijk vizier")


def test_msg227_visor_view():
    eng, w = _eng(54, rng=FakeRNG([0.7]))           # int(2.1)=2 -> msg 227
    eng.obj_loc[HARNAS] = 21
    assert w.message_text(227) in _run(eng, "bekijk vizier")


# --------------------------------- Dracula endgame escalation (end-of-turn, e74 == 4)
def test_msg255_dracula_escalation():
    eng, w = _eng(24, dde=24, e76=1, e74=4, e70=1)
    io = ScriptedIO([])
    eng.io = io
    run_end_of_turn(eng)
    assert w.message_text(255) in io.text


# ------------------------ DOOD DRACULA when he is present: taunt K=int(RND*2)+172
def test_msg171_dood_dracula_taunt():
    eng, w = _eng(22, dde=22, e70=1, e76=0, rng=FakeRNG([0.2]))   # int(0.4)=0 -> msg 171
    assert w.message_text(171) in _run(eng, "dood dracula")


def test_msg172_dood_dracula_taunt():
    eng, w = _eng(22, dde=22, e70=1, e76=0, rng=FakeRNG([0.7]))   # int(1.4)=1 -> msg 172
    assert w.message_text(172) in _run(eng, "dood dracula")


# --------------- GOOI KAPMES (the knife) subsequent hit at the waard (room 12): +3
def test_msg195_gooi_kapmes_at_angry_waard():
    eng, w = _eng(12, e84=1, rng=FakeRNG([0.1]))    # int(0.3)=0 -> k=196 -> msg 195
    eng.obj_loc[5] = CARRIED                          # obj5 = zwaar kapmes
    assert w.message_text(195) in _run(eng, "gooi kapmes")


def test_msg196_gooi_kapmes_at_angry_waard():
    eng, w = _eng(12, e84=1, rng=FakeRNG([0.5]))    # int(1.5)=1 -> k=197 -> msg 196
    eng.obj_loc[5] = CARRIED
    assert w.message_text(196) in _run(eng, "gooi kapmes")


def test_msg197_gooi_kapmes_at_angry_waard():
    eng, w = _eng(12, e84=1, rng=FakeRNG([0.8]))    # int(2.4)=2 -> k=198 -> msg 197
    eng.obj_loc[5] = CARRIED
    assert w.message_text(197) in _run(eng, "gooi kapmes")
