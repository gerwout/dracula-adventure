"""Multi-word disambiguation echo (screenshot SS-6010, EXE 0x523).

Typing 3+ words prints "Ik neem aan dat je 'W1 W2' bedoelt." and then processes only
the first two words. E.g. `kijk door raam` -> the echo, then KIJK DOOR -> msg 122.
"""
from engine.data.loader import load_file
from engine.game import Engine
from engine.io import ScriptedIO
from engine.parser import parse_line


def _run(eng, line):
    eng.io = ScriptedIO([])
    for cmd in parse_line(line):
        eng.dispatch(cmd)
    return eng.io.text


def test_three_words_echo_assumption():
    eng = Engine(load_file(), ScriptedIO([]))
    eng.room = 0
    out = _run(eng, "kijk door raam")
    assert "Ik neem aan dat je 'KIJK DOOR' bedoelt." in out
    assert eng.world.message_text(122) in out        # then KIJK DOOR -> unmatched


def test_two_words_no_echo():
    eng = Engine(load_file(), ScriptedIO([]))
    eng.room = 0
    out = _run(eng, "kijk door")
    assert "Ik neem aan" not in out


def test_one_word_no_echo():
    eng = Engine(load_file(), ScriptedIO([]))
    eng.room = 0
    out = _run(eng, "inventaris")
    assert "Ik neem aan" not in out
