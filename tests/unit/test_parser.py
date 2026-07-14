"""Unit tests for the command parser."""
from engine.parser import (direction_index, match_verb, parse_line,
                           DIR_NOORD, DIR_ZUID, DIR_OOST, DIR_WEST,
                           DIR_OMHOOG, DIR_OMLAAG, DIR_ERUIT)


def test_direction_full_words():
    assert direction_index("noord") == DIR_NOORD
    assert direction_index("zuid") == DIR_ZUID
    assert direction_index("oost") == DIR_OOST
    assert direction_index("west") == DIR_WEST
    assert direction_index("omhoog") == DIR_OMHOOG
    assert direction_index("omlaag") == DIR_OMLAAG
    assert direction_index("eruit") == DIR_ERUIT


def test_direction_single_letters():
    assert direction_index("n") == DIR_NOORD
    assert direction_index("z") == DIR_ZUID
    assert direction_index("o") == DIR_OOST
    assert direction_index("w") == DIR_WEST


def test_direction_prefixes_disambiguate_up_down():
    # real tokens: OMHO/HOOG/H (up) and OMLA/LAAG/L (down)
    assert direction_index("omhoog") == DIR_OMHOOG
    assert direction_index("omho") == DIR_OMHOOG
    assert direction_index("hoog") == DIR_OMHOOG
    assert direction_index("h") == DIR_OMHOOG
    assert direction_index("omlaag") == DIR_OMLAAG
    assert direction_index("omla") == DIR_OMLAAG
    assert direction_index("laag") == DIR_OMLAAG
    assert direction_index("l") == DIR_OMLAAG


def test_verb_abbreviations():
    assert match_verb("i") == "inventaris"
    assert match_verb("k") == "kijk"
    assert match_verb("kijk") == "kijk"
    assert match_verb("inventaris") == "inventaris"


def test_verb_synonyms():
    for w in ("pak", "neem", "grijp", "raap"):
        assert match_verb(w) == "pak"
    for w in ("bekijk", "onderzoek"):
        assert match_verb(w) == "bekijk"


def test_bare_single_letter_direction_is_movement():
    # Single-letter directions (N/Z/O/W/H/L/E) are bare movement commands.
    cmds = parse_line("z")
    assert len(cmds) == 1
    assert cmds[0].verb == "ga"
    assert cmds[0].direction == DIR_ZUID


def test_bare_full_word_direction_is_not_a_command():
    # Verified via oracle: the real game rejects bare "zuid"/"noord" (they are
    # only valid as the noun after GA). So they must NOT parse as movement.
    for word in ("zuid", "noord", "oost", "west"):
        cmds = parse_line(word)
        assert cmds[0].verb is None, f"bare {word!r} must not be a command"
        assert cmds[0].direction is None
    # ...but "GA <word>" and the single letter both move.
    assert parse_line("ga zuid")[0].direction == DIR_ZUID
    assert parse_line("z")[0].direction == DIR_ZUID


def test_verb_plus_direction():
    cmds = parse_line("ga west")
    assert cmds[0].verb == "ga"
    assert cmds[0].direction == DIR_WEST


def test_multiple_commands_split_on_dot():
    cmds = parse_line("ga noord. pak lamp . i")
    assert [c.verb for c in cmds] == ["ga", "pak", "inventaris"]
    assert cmds[1].noun == "LAMP"       # the EXE uppercases the whole line


def test_unknown_verb():
    cmds = parse_line("xyzzy iets")
    assert cmds[0].verb is None
