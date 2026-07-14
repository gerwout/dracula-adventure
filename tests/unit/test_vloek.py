"""Profanity handling — the `vloek` handler (DRACULA.EXE 0x3d6c).

The parser routes the profanity group {GODVE, SHIT, KUT, KLOOT, KANKE, GOD, FUCK,
GEDVE} to `vloek`, which prints a RANDOM rebuke chosen as
``[0xe34] = INT(RND * 5) + 155`` -> world.messages[154..158] (the message off-by-one).
"""
from engine.data.loader import load_file
from engine.game import new_game
from engine.io import ScriptedIO
from engine.parser import match_verb


SWEARS = ("kut", "kanker", "klootzak", "godverdomme", "shit", "fuck", "god", "kloot")


def test_all_profanity_words_route_to_vloek():
    for w in SWEARS:
        assert match_verb(w) == "vloek", w


def test_profanity_prints_a_rebuke_from_the_pool():
    world = load_file()
    pool = {world.message_text(i) for i in range(154, 159)}
    io = ScriptedIO([])
    eng = new_game(io)
    for w in SWEARS:
        io.output.clear()
        eng.submit(w)
        assert io.text.strip() in pool, (w, io.text)


def test_profanity_pool_is_exactly_five_messages_and_all_reachable():
    world = load_file()
    pool = {world.message_text(i) for i in range(154, 159)}
    io = ScriptedIO([])
    eng = new_game(io)
    seen = set()
    for _ in range(80):                 # enough draws to hit all 5 with seed 5
        io.output.clear()
        eng.submit("kut")
        seen.add(io.text.strip())
    assert seen == pool                  # every rebuke appears, nothing outside the pool


def test_non_profanity_word_is_not_treated_as_a_swear():
    world = load_file()
    pool = {world.message_text(i) for i in range(154, 159)}
    io = ScriptedIO([])
    eng = new_game(io)
    eng.submit("stront")                 # not one of the 8 tokens
    assert io.text.strip() not in pool
