"""Innkeeper (waard) interaction cluster — herberg rooms 12/13, zolder 14.

Faithful port of the DRACULA.EXE handlers verified against the disassembly:

  * VRAAG WAARD  = the two-men conversation (0x2ab5): reveals the zoldertrap ([0xe6e]).
  * GA/KLIM ZOLDER|TRAP (0x2b17): the guarded 12->14 climb.
  * GOOI BIJL|KAPMES at the waard (0x4a97): the anger latch [0xe84] + throw reactions.
  * DOOD/VERMO/LIQUI WAARD (0x3c74): increment [0xe84] + the random knife death.
  * PAK KNOFLOOK (0x39cc): the un-takeable garlic — anger, then the knife death.
  * GEEF MUNT (0x3fae): calms the angry waard (msg 182 then 189, clears [0xe84]).

Message indices are world.messages indices (EXE [0xe34]=K prints world.messages[K-1],
already applied). Expected strings are read from the loaded world, never hardcoded.
"""
from engine.data.loader import load_file
from engine.game import CARRIED, Engine
from engine.data.model import LOC_NOWHERE
from engine.io import ScriptedIO
from engine.parser import parse_line, match_verb

# Object loader-indices (docs/verb-events.md §1).
KNOFLOOK, KAPMES = 3, 5
BIJL_SCHERP, MUNT, BOTTE_BIJL = 10, 15, 28


class FakeRNG:
    """Deterministic RND source: pops the next scripted value on random()/rnd()."""
    def __init__(self, values):
        self.values = list(values)

    def random(self):
        return self.values.pop(0)

    def rnd(self, x=1.0):
        return self.values.pop(0)


def _engine(room, carrying=(), placed=None, rng=None):
    world = load_file()
    eng = Engine(world, ScriptedIO([]))
    eng.room = room
    for oid in carrying:
        eng.obj_loc[oid] = CARRIED
    for oid, loc in (placed or {}).items():
        eng.obj_loc[oid] = loc
    if rng is not None:
        eng.rng = rng
    return eng, world


def _run(eng, line):
    # Dispatch in isolation (no end-of-turn), like tests/unit/test_verb_events.py.
    eng.io = ScriptedIO([])
    for cmd in parse_line(line):
        eng.dispatch(cmd)
    return eng.io.text


# ------------------------------------------------------------ parser verb split
def test_dood_verbs_route_to_kill_handler_not_sla():
    # VERB MISMAP #2 fix: DOOD/VERMO/LIQUI get their own canonical 'dood'; the
    # blunt-force verbs stay on 'sla'.
    assert match_verb("dood") == "dood"
    assert match_verb("vermoord") == "dood"
    assert match_verb("liquideer") == "dood"
    assert match_verb("sla") == "sla"
    assert match_verb("stomp") == "sla"
    assert match_verb("schop") == "sla"


# ------------------------------------------------------------ VRAAG conversation
def test_vraag_waard_reveals_zoldertrap():
    # room 12, e6e==0, e84<=0 -> set e6e=1 and print the reveal (msg 59).
    eng, w = _engine(12)
    out = _run(eng, "vraag waard")
    assert eng.state["e6e"] == 1
    assert w.message_text(59) in out


def test_vraag_waard_already_revealed():
    # room 12, e6e!=0 -> "Ben je doof of zo" (msg 57), no state change.
    eng, w = _engine(12)
    eng.state["e6e"] = 1
    out = _run(eng, "vraag waard")
    assert w.message_text(57) in out
    assert eng.state["e6e"] == 1


def test_vraag_waard_angry_refuses():
    # room 12, e6e==0 but e84>0 -> the angry brush-off (msg 58); no reveal.
    eng, w = _engine(12)
    eng.state["e84"] = 1
    out = _run(eng, "vraag waard")
    assert w.message_text(58) in out
    assert eng.state["e6e"] == 0


def test_vraag_no_answer_elsewhere():
    # NOT(room==12 AND noun~=WAAR) -> "Niemand geeft antwoord." (msg 56).
    eng, w = _engine(0)
    assert w.message_text(56) in _run(eng, "vraag waard")
    # in room 12 but a different noun also gets msg 56.
    eng, w = _engine(12)
    assert w.message_text(56) in _run(eng, "vraag deur")


# ------------------------------------------------------- GA/KLIM ZOLDER | TRAP
def test_ga_zolder_hint_before_conversation():
    # e6e==0 -> the "ask the waard" hint (msg 60), no move.
    eng, w = _engine(12)
    out = _run(eng, "ga zolder")
    assert w.message_text(60) in out
    assert eng.room == 12


def test_ga_zolder_blocked_when_angry():
    # e6e!=0 but e84>0 -> the waard blocks you (msg 61), no move.
    eng, w = _engine(12)
    eng.state["e6e"] = 1
    eng.state["e84"] = 1
    out = _run(eng, "ga zolder")
    assert w.message_text(61) in out
    assert eng.room == 12


def test_ga_zolder_climbs_when_revealed_and_calm():
    # e6e!=0 AND e84<=0 -> climb to the zolder (room 14).
    eng, w = _engine(12)
    eng.state["e6e"] = 1
    _run(eng, "ga zolder")
    assert eng.room == 14


def test_klim_trap_uses_same_handler():
    # KLIM (->ga) with the TRAP noun routes to the same zolder handler.
    eng, w = _engine(12)
    eng.state["e6e"] = 1
    _run(eng, "klim trap")
    assert eng.room == 14


def test_vraag_then_ga_zolder_end_to_end():
    # Integration: VRAAG WAARD reveals the trap (e6e=1), then GA ZOLDER climbs.
    eng, w = _engine(12)
    _run(eng, "vraag waard")
    assert eng.state["e6e"] == 1
    _run(eng, "ga zolder")
    assert eng.room == 14


# ------------------------------------------------------------------- GOOI waard
def test_gooi_bijl_first_hit_sets_anger_and_drops():
    # First throw (e84==0): e84=1, the axe drops into room 12, msg 190.
    eng, w = _engine(12, carrying=[BIJL_SCHERP])
    out = _run(eng, "gooi bijl")
    assert eng.state["e84"] == 1
    assert eng.obj_loc[BIJL_SCHERP] == 12
    assert w.message_text(190) in out


def test_gooi_kapmes_first_hit_uses_msg_191():
    # KAPMES first throw -> the distinct kapmes message (191), kapmes drops in room 12.
    eng, w = _engine(12, carrying=[KAPMES])
    out = _run(eng, "gooi kapmes")
    assert eng.state["e84"] == 1
    assert eng.obj_loc[KAPMES] == 12
    assert w.message_text(191) in out


def test_gooi_blunt_axe_also_hits():
    # The blunt bijl (obj28) is thrown when the sharp one isn't carried.
    eng, w = _engine(12, carrying=[BOTTE_BIJL])
    out = _run(eng, "gooi bijl")
    assert eng.state["e84"] == 1
    assert eng.obj_loc[BOTTE_BIJL] == 12
    assert w.message_text(190) in out


def test_gooi_bijl_subsequent_hit_random_reaction():
    # Once angry (e84!=0): a random reaction K=193+INT(RND*3); no e84 change, no death,
    # and (the EXE re-drop being unreachable) the axe stays in hand.
    eng, w = _engine(12, carrying=[BIJL_SCHERP], rng=FakeRNG([0.0]))
    eng.state["e84"] = 1
    out = _run(eng, "gooi bijl")
    assert eng.state["e84"] == 1
    assert eng.dead is False
    assert eng.obj_loc[BIJL_SCHERP] == CARRIED
    assert w.message_text(192) in out          # K=193 -> index 192


def test_gooi_bijl_not_carried_falls_to_generic_drop():
    # Not carrying the axe -> the generic drop path (EXE jmp 0x1f32): "niet bij je".
    eng, w = _engine(12)
    out = _run(eng, "gooi bijl")
    assert eng.state["e84"] == 0
    assert w.message_text(23) in out


def test_gooi_knoflook_room12_does_not_hit_waard():
    # GOOI KNOF (slot 4) in room 12 does NOT hit the waard -> generic drop, no anger.
    eng, w = _engine(12, carrying=[KNOFLOOK])
    _run(eng, "gooi knoflook")
    assert eng.state["e84"] == 0
    assert eng.obj_loc[KNOFLOOK] == 12         # dropped generically, not a waard hit


# ------------------------------------------------------- DOOD / VERMO / LIQUI
def test_dood_waard_increments_anger_and_prints():
    # room 12: e84++ and a random reaction K=INT(RND*5)+141; K=141 (rng 0.0) -> msg 140.
    eng, w = _engine(12, rng=FakeRNG([0.0]))
    out = _run(eng, "dood waard")
    assert eng.state["e84"] == 1
    assert eng.dead is False
    assert w.message_text(140) in out


def test_dood_waard_knife_death_on_k143():
    # K==143 (rng 0.5 -> INT(2.5)=2, +141) is the knife death: msg 142 + game over.
    eng, w = _engine(12, rng=FakeRNG([0.5]))
    out = _run(eng, "dood waard")
    assert w.message_text(142) in out
    assert eng.dead is True


def test_vermoord_waard_routes_same_as_dood():
    # VERMO also reaches the kill handler's waard branch.
    eng, w = _engine(12, rng=FakeRNG([0.0]))
    out = _run(eng, "vermoord waard")
    assert eng.state["e84"] == 1
    assert w.message_text(140) in out


def test_dood_dracula_elsewhere_delegates_to_hit():
    # A non-waard kill target falls back to the SLA hit handler: Dracula absent -> msg 145.
    eng, w = _engine(24)
    out = _run(eng, "dood dracula")
    assert w.message_text(145) in out
    assert eng.dead is False


# --------------------------------------------------------------- PAK KNOFLOOK
def test_pak_knoflook_first_attempt_angers_waard():
    # room 12 (garlic present), e84==0 -> e84=1, msg 129.
    eng, w = _engine(12)
    out = _run(eng, "pak knoflook")
    assert eng.state["e84"] == 1
    assert w.message_text(129) in out
    assert eng.obj_loc[KNOFLOOK] == 12         # not taken


def test_pak_knoflook_second_attempt_prints_129_and_130():
    # e84==1 -> e84=2, msg 129 THEN msg 130.
    eng, w = _engine(12)
    eng.state["e84"] = 1
    out = _run(eng, "pak knoflook")
    assert eng.state["e84"] == 2
    assert w.message_text(129) in out
    assert w.message_text(130) in out


def test_pak_knoflook_third_attempt_is_fatal():
    # e84>1 -> the knife death (msg 142), game over.
    eng, w = _engine(12)
    eng.state["e84"] = 2
    out = _run(eng, "pak knoflook")
    assert w.message_text(142) in out
    assert eng.dead is True


def test_pak_knoflook_wrong_room():
    # room != garlic-loc -> "Ik zie geen knoflook." (msg 128), no anger.
    eng, w = _engine(0)
    out = _run(eng, "pak knoflook")
    assert w.message_text(128) in out
    assert eng.state["e84"] == 0


def test_pak_knoflook_elsewhere_is_generic_take():
    # If the garlic is anywhere but room 12, PAK takes it normally (prints "Ok").
    eng, w = _engine(5, placed={KNOFLOOK: 5})
    out = _run(eng, "pak knoflook")
    assert eng.obj_loc[KNOFLOOK] == CARRIED
    assert "Ok" in out


# --------------------------------------------------------------- GEEF MUNT fix
def test_geef_munt_angry_prints_182_then_189_and_calms():
    # e84>0: coin consumed, msg 182 THEN msg 189, e84 cleared.
    eng, w = _engine(12, carrying=[MUNT])
    eng.state["e84"] = 1
    out = _run(eng, "geef munt")
    assert eng.obj_loc[MUNT] == LOC_NOWHERE
    assert w.message_text(182) in out
    assert w.message_text(189) in out
    assert eng.state["e84"] == 0


def test_geef_munt_calm_prints_182_only():
    # e84<=0: coin consumed, only msg 182 (not the calming line 189).
    eng, w = _engine(12, carrying=[MUNT])
    out = _run(eng, "geef munt")
    assert eng.obj_loc[MUNT] == LOC_NOWHERE
    assert w.message_text(182) in out
    assert w.message_text(189) not in out
