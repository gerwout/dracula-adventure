"""End-of-turn routine (EXE 0x269e) — Dracula combat, spider timer, treasure win.

Faithful port; tests drive the Engine + the run_end_of_turn entry point and assert
the DGROUP-flag / death / win state the original mutates each turn. Message strings
are read from the loaded world, never hardcoded.
"""
from engine.data.loader import load_file
from engine.data.model import CARRIED
from engine.end_of_turn import run_end_of_turn
from engine.game import Engine
from engine.io import ScriptedIO

SCHATKIST, SPIN, DOODSKIST_OPEN = 13, 34, 38


def _eng(room, **flags):
    eng = Engine(load_file(), ScriptedIO([]))
    eng.room = room
    eng.state.update(flags)
    return eng, eng.world


def _eot(eng):
    eng.io = ScriptedIO([])
    run_end_of_turn(eng)
    return eng.io.text


# --------------------------------------------------------- block A: your room
def test_banish_when_counterblow_landed():
    # e74<0 while standing in Dracula's room -> banish: e70=1, dde=255, msg[149].
    eng, w = _eng(22, dde=22, e70=0, e74=-1)
    out = _eot(eng)
    assert eng.state["e70"] == 1
    assert eng.state["dde"] == 255
    assert w.message_text(149) in out


def test_escalates_while_dracula_on_you():
    # in Dracula's room, no counter-blow -> the combat counter climbs.
    eng, w = _eng(22, dde=22, e70=0, e74=2)
    _eot(eng)
    assert eng.state["e74"] == 3
    assert not eng.dead


def test_noop_when_dracula_absent():
    # default game (dde=255): end-of-turn changes nothing and prints nothing.
    eng, w = _eng(0)
    assert eng.state["dde"] == 255
    assert _eot(eng) == ""
    assert not eng.dead and not eng.won


# --------------------------------------------------------- block B: patrol walk
def test_patrol_steps_one_room_and_prints_when_seen():
    # e76 set, Dracula at 37, you are at 37 -> he steps 37->32, opens the gate (e44),
    # records de0=37, and (you see him) prints the transition line msg[253].
    eng, w = _eng(37, dde=37, e76=1)
    out = _eot(eng)
    assert eng.state["dde"] == 32
    assert eng.state["e44"] == 1
    assert eng.state["de0"] == 37
    assert w.message_text(253) in out


def test_patrol_is_silent_when_not_in_his_room():
    # same step, but you are elsewhere -> he still moves, no line is printed.
    eng, w = _eng(5, dde=37, e76=1)
    out = _eot(eng)
    assert eng.state["dde"] == 32
    assert w.message_text(253) not in out


def test_patrol_reaches_room24_arms_bedroom_door():
    # 22->24 arms e46 (bedroom door) and resets the combat counter to 2.
    eng, w = _eng(24, dde=22, e76=1)
    _eot(eng)
    assert eng.state["dde"] == 24
    assert eng.state["e46"] == -1
    assert eng.state["e74"] == 2


# ------------------------------------------------ block B: room-24 confrontation
def test_confrontation_escalates_with_messages():
    eng, w = _eng(24, dde=24, e76=1, e74=3, e70=1)
    out = _eot(eng)
    assert w.message_text(254) in out
    assert eng.state["e74"] == 4


def test_confrontation_defeat_sets_dracula_defeated():
    # the decisive stake (e74<0) in room 24 -> Dracula defeated: dde=257, e76=0, msg[264].
    eng, w = _eng(24, dde=24, e76=1, e74=-1, e70=1)
    out = _eot(eng)
    assert eng.state["dde"] == 257
    assert eng.state["e76"] == 0
    assert w.message_text(264) in out
    assert not eng.dead and not eng.won      # defeat unlocks the endgame, not game over


def test_defeat_reveals_the_secret_word():
    # 0x4de7: after the defeat message the dust spells out the room-31 secret word.
    eng, w = _eng(24, dde=24, e76=1, e74=-1, e70=1)
    out = _eot(eng)
    assert "incoronium" in out.lower()
    assert "Vaag kun je de tekst" in out      # the EXE dust-reveal framing


def test_confrontation_death_at_phase_7():
    eng, w = _eng(24, dde=24, e76=1, e74=7, e70=1)
    out = _eot(eng)
    assert w.message_text(256) in out
    assert eng.dead


# ----------------------------------------------------------- block C: the spider
def test_spider_warns_then_kills():
    eng, w = _eng(34, e7a=2)
    out = _eot(eng)
    assert w.message_text(270) in out
    assert eng.state["e7a"] == 3
    assert not eng.dead
    eng, w = _eng(34, e7a=4)
    out = _eot(eng)
    assert w.message_text(269) in out
    assert eng.dead


# --------------------------------------------------------- block D: treasure win
def test_treasure_to_house_wins():
    eng, w = _eng(11)
    eng.obj_loc[SCHATKIST] = CARRIED
    out = _eot(eng)
    assert w.message_text(281) in out
    assert eng.won


# ----------------------------------------------------------- turn-loop wiring
def test_submit_runs_end_of_turn_each_command():
    # a neutral command triggers end-of-turn; a lethal state ends the game.
    eng, w = _eng(24, dde=24, e76=1, e74=7, e70=1)
    eng.io = ScriptedIO([])
    eng.submit("kijk")
    assert eng.dead
    assert not eng.running


def test_combat_verb_now_banishes_end_to_end():
    # SCHIJN with the lamp at the vulnerable phase drives e74 to -1 (verb), and the
    # end-of-turn that follows in the same submit() banishes Dracula.
    eng, w = _eng(22, dde=22, e70=0, e74=1)
    eng.obj_loc[0] = CARRIED                 # lamp in hand
    eng.io = ScriptedIO([])
    eng.submit("schijn dracula")
    assert eng.state["e70"] == 1
    assert eng.state["dde"] == 255
    assert w.message_text(149) in eng.io.text


# --------------------------------------------------- block A: computed-message death
class _FixedRNG:
    """Deterministic RND source (returns a fixed value on random()/rnd())."""
    def __init__(self, v):
        self.v = v

    def random(self):
        return self.v

    def rnd(self, x=1.0):
        return self.v


def test_block_a_phase5_prints_approach_and_escalates():
    # EXE 0x26ea: Block A gate holds AND e74==5 -> print CINT(RND*1 + 148.0), i.e.
    # world.messages[147] or [148] (a Dracula-approach line), then escalate e74->6.
    # NON-fatal. With RND=0.0 the CINT rounds to 148 -> messages[147].
    eng, w = _eng(22, dde=22, e70=0, e74=5)
    eng.rng = _FixedRNG(0.0)
    out = _eot(eng)
    assert w.message_text(147) in out
    assert eng.state["e74"] == 6
    assert not eng.dead


def test_block_a_phase5_high_rng_prints_upper_message():
    # RND=0.7 -> CINT(148.7)=149 -> messages[148] (the 'begint te lachen' line).
    eng, w = _eng(22, dde=22, e70=0, e74=5)
    eng.rng = _FixedRNG(0.7)
    out = _eot(eng)
    assert w.message_text(148) in out
    assert eng.state["e74"] == 6
    assert not eng.dead


def test_block_a_phase6_prints_death_climax_and_dies():
    # EXE 0x2714: Block A gate holds AND e74==6 -> print CINT(RND*1 + 152.0), i.e.
    # world.messages[151] or [152] (the neck-bite death climax), then DEATH ([0xdf6]).
    # With RND=0.0 the CINT rounds to 152 -> messages[151].
    eng, w = _eng(22, dde=22, e70=0, e74=6)
    eng.rng = _FixedRNG(0.0)
    out = _eot(eng)
    assert w.message_text(151) in out
    assert eng.dead


def test_block_a_phase6_high_rng_prints_upper_message():
    # RND=0.7 -> CINT(152.7)=153 -> messages[152] (the 'bijt je in je nek' collapse).
    eng, w = _eng(22, dde=22, e70=0, e74=6)
    eng.rng = _FixedRNG(0.7)
    out = _eot(eng)
    assert w.message_text(152) in out
    assert eng.dead


def test_block_a_full_escalation_2_to_death():
    # e74 starts at 2 on spawn; a stalled player (never counter-blows) escalates
    # 2->3->4->5(print approach)->6(print death+die), one step per turn.
    eng, w = _eng(22, dde=22, e70=0, e74=2)
    eng.rng = _FixedRNG(0.0)
    _eot(eng); assert eng.state["e74"] == 3 and not eng.dead
    _eot(eng); assert eng.state["e74"] == 4 and not eng.dead
    out5 = _eot(eng)
    assert eng.state["e74"] == 5 and not eng.dead and out5 == ""     # e74:4->5, silent
    out6 = _eot(eng)
    assert eng.state["e74"] == 6 and not eng.dead                    # e74:5->6, approach line
    assert w.message_text(147) in out6
    out7 = _eot(eng)
    assert eng.dead                                                  # e74==6 -> death climax
    assert w.message_text(151) in out7


# ---------------------------------------------- shared game-over hub (EXE 0x3ed3)
def test_game_over_hub_prints_dodenrijk_after_death():
    # Every death lands on the 0x3ed3 hub: after the death-specific line, the shared
    # 'dodenrijk' + reincarnation prompt (messages[166]) prints, then the game ends.
    eng, w = _eng(24, dde=24, e76=1, e74=7, e70=1)
    eng.io = ScriptedIO([])
    eng.submit("kijk")
    assert w.message_text(256) in eng.io.text     # the death-specific line
    assert w.message_text(166) in eng.io.text     # the shared dodenrijk hub
    assert eng.dead and not eng.running


def test_doodskist_slide_delivers_schatkist_and_wins():
    # Full doodskist-slide ending. On the hillside ledge (room 26) with the OPENED
    # doodskist (obj38) dropped there and the schatkist in hand, GA KIST slides you
    # down into the village (EXE branch B 0x1ac0): the coffin object relocates to
    # room 11, the slide line (messages[279]) prints, and you ride inside (room 38).
    # GA UIT of the coffin interior (EXE room-38 exit 0x1004) lands you where the
    # coffin now sits (room 11), where end_of_turn Block D declares the win.
    eng, w = _eng(26)
    eng.obj_loc[DOODSKIST_OPEN] = 26
    eng.obj_loc[SCHATKIST] = CARRIED
    eng.io = ScriptedIO([])
    eng.submit("ga kist")                        # slide down the hill
    assert eng.room == 38                         # riding inside the coffin
    assert eng.obj_loc[DOODSKIST_OPEN] == 11      # the coffin slid to the village
    assert eng.obj_loc[SCHATKIST] == CARRIED      # the treasure rides along untouched
    assert w.message_text(279) in eng.io.text
    assert not eng.won                            # not won yet — still inside the coffin
    eng.io = ScriptedIO([])
    eng.submit("ga uit")                          # climb out into the village
    assert eng.room == 11
    assert w.message_text(281) in eng.io.text     # the TROS ending
    assert eng.won and not eng.running


def test_win_does_not_print_dodenrijk_hub():
    # A win prints the full ending (messages[281]) but NOT the death hub (messages[166]).
    eng, w = _eng(11)
    eng.obj_loc[SCHATKIST] = CARRIED
    eng.io = ScriptedIO([])
    eng.submit("kijk")
    assert w.message_text(281) in eng.io.text
    assert w.message_text(166) not in eng.io.text
    assert eng.won and not eng.running


# --------------------------------------- the remaining lose-states via submit()
# End-to-end coverage: a real submit() of each verb-death must print the death line,
# route through the shared game-over hub (messages[166]), and stop the game — WITHOUT
# ever running the 0x269e end-of-turn (a verb-death `jmp 0x3ed3` bypasses it).
GIF_FLES = 33          # obj33, the blue poison bottle ([0xc9c]); carried == drinkable

def test_submit_spring_balcony_room25_ends_game():
    # (a) Balcony JUMP death (EXE 0x2b46 -> 0x2b84 -> 0x3ed3): SPRING off the balcony
    # (room 25) prints messages[218] (">>>>> B A F F <<<<< … Je sterft na enige
    # ogenblikken.") then the dodenrijk hub (messages[166]); running goes False.
    eng, w = _eng(25)
    eng.io = ScriptedIO([])
    eng.submit("spring")
    assert w.message_text(218) in eng.io.text     # the balcony death line
    assert w.message_text(166) in eng.io.text     # the shared dodenrijk hub
    assert eng.dead and not eng.running
    assert eng.room == 25                          # the fatal jump does not move you


def test_submit_ga_vuur_fire_room34_ends_game():
    # (c) Fire death (EXE 0x1a4b -> 0x1a7b -> 0x3ed3): GA VUUR on foot in the kruiskamer
    # (room 34, not inside the harnas) prints messages[280] (the desintegratie line)
    # then the dodenrijk hub (messages[166]); running goes False, no room change.
    eng, w = _eng(34)
    eng.io = ScriptedIO([])
    eng.submit("ga vuur")
    assert w.message_text(280) in eng.io.text     # the fire death line
    assert w.message_text(166) in eng.io.text     # the shared dodenrijk hub
    assert eng.dead and not eng.running
    assert eng.room == 34


def test_submit_drink_poison_does_not_end_game():
    # (b) Poison DRINK is a FAITHFUL latent bug — it never kills (verified vs the
    # disassembly: 0x234b sets [0xdf6]=-1, but 0x269e's opening `mov [0xdf6],0` wipes it
    # before the 0x0311 death-check). A real submit() therefore prints only the giftig
    # line (messages[36]), NOT the dodenrijk hub, and the game keeps running.
    eng, w = _eng(2)
    eng.obj_loc[GIF_FLES] = CARRIED
    eng.io = ScriptedIO([])
    eng.submit("drink water")
    assert w.message_text(36) in eng.io.text      # the giftig-water flavour line
    assert w.message_text(166) not in eng.io.text  # NO dodenrijk hub — no death
    assert eng.state["df6"] == -1                  # the poison latch is set (0x234b) …
    assert not eng.dead and eng.running            # … but the player lives on (EXE-faithful)
