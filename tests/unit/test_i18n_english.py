"""The bundled English build: coverage, tone, and that the translated words parse.

The full playthrough (in every language, English included) lives in
test_playthrough_i18n.py; here we check the English-specific things — that the CSV
covers every string, that the flagged special-tone messages read the way they should,
and that the translated verbs/directions/object-nouns/scenery-nouns actually parse.
"""
from pathlib import Path

from engine.data.loader import load_file
from engine.game import new_game
from engine.io import ScriptedIO
from engine.i18n import AVAILABLE_LANGUAGES, builtin_translator
from tools import translate_core as core

ENGINE_DIR = Path(__file__).resolve().parents[2] / "engine"


# --------------------------------------------------------------------------- #
#  Registry + coverage
# --------------------------------------------------------------------------- #
def test_language_registry_has_dutch_and_english():
    assert AVAILABLE_LANGUAGES["nl"] == "Nederlands"
    assert AVAILABLE_LANGUAGES["en"] == "English"


def test_languages_are_discovered_from_the_csv_files(tmp_path):
    # The registry is DISCOVERED from engine/data/i18n/ -- the Dutch source plus each
    # dracula_<code>.csv -- so adding a language is literally dropping in a CSV (which
    # names itself via ui:LANGUAGE_NAME), with no code change.
    import csv
    from engine.i18n import available_languages
    assert available_languages() == {"nl": "Nederlands", "en": "English"}
    p = tmp_path / "dracula_it.csv"
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "it"])
        w.writerow(["ui:LANGUAGE_NAME", "Italiano"])
    langs = available_languages(tmp_path)
    assert langs["it"] == "Italiano"        # discovered from the file, self-named
    assert langs["nl"] == "Nederlands"      # the source is always present


def test_builtin_translator_nl_is_noop_en_is_not():
    assert builtin_translator("nl") is None            # the source language needs none
    tr = builtin_translator("en")
    assert tr is not None and not tr.is_default()


def test_english_csv_translates_every_row():
    # Every translatable string the tool collects has a non-empty English value in the
    # shipped CSV — nothing is left in Dutch by omission.
    tr = builtin_translator("en")
    world = load_file()
    rows = core.collect_rows(world, languages=("en",), engine_dir=ENGINE_DIR)
    ids = {r["id"] for r in rows}
    covered = (set(f"msg:{k}" for k in tr.messages) | set(f"room:{k}" for k in tr.rooms)
               | set(f"obj:{k}" for k in tr.objects)
               | set(f"objnoun:{k}" for k in tr.object_nouns)
               | set(f"verb:{k}" for k in tr.verbs) | set(f"dir:{k}" for k in tr.dirs)
               | set(f"noun:{k}" for k in tr.nouns) | set(f"ui:{k}" for k in tr.ui)
               | set(f"answer:{k}" for k in tr.answers)
               | ({"secret:word"} if tr.secret else set())
               | set(f"intro:{k}" for k in tr.intro) | ({"intro:header"} if tr.header else set()))
    missing = ids - covered
    # msg:94 is a language-neutral cipher grid kept verbatim (equal to the Dutch), so it
    # may not appear as a distinct override; everything else must be covered.
    assert missing <= {"msg:94"}, f"untranslated rows: {sorted(missing)[:20]}"


def test_english_special_tone_messages():
    w = load_file(translator=builtin_translator("en"))
    assert "You are carrying:" in w.lexicon.ui("INV_HEADER")
    # the archaic vampire handbook (msg 91) reads as Early-Modern English
    assert "Vampyres have beene" in w.message_text(91)
    # the CNN / Coffin News Network gag replaces the Dutch TROS gag (msg 281)
    assert "Coffin News Network" in w.message_text(281)
    # the computer-slang tone is kept (msg 6)
    assert "compewter" in w.message_text(6)


# --------------------------------------------------------------------------- #
#  Parsing: the translated input words work, and Dutch tokens do NOT leak in
# --------------------------------------------------------------------------- #
def test_translated_verbs_dirs_object_nouns_parse():
    from engine.parser import match_verb, direction_index
    from engine.data.model import CARRIED
    eng = new_game(ScriptedIO([]), lang="en")
    assert match_verb("take", eng._verb_table) == "pak"
    assert match_verb("examine", eng._verb_table) == "bekijk"
    assert match_verb("pak", eng._verb_table) is None          # the Dutch verb is gone
    assert direction_index("north", eng._dir_table) is not None
    assert direction_index("out", eng._dir_table) is not None
    eng.obj_loc[3] = CARRIED
    assert eng.resolve("garlic") == 3                          # translated object noun
    assert eng.resolve("knoflook") is None


def test_scenery_nouns_match_only_via_the_alias_map():
    # Under a translation, noun_is matches ONLY through the target-language alias, never
    # the raw Dutch prefix — so 'gate' means the grating (HEK), not the Dutch GAT/'hole',
    # and 'bedroom' the bedroom (SLAA), not 'bed'.
    from engine import verb_events
    w = load_file(translator=builtin_translator("en"))
    verb_events.set_noun_canon(w.lexicon.noun_canon)
    try:
        assert verb_events.noun_is("door", "DEUR")
        assert verb_events.noun_is("chest", "KIST")
        assert verb_events.noun_is("coffin", "DOOD")
        assert verb_events.canon_token("gate") == "HEK"        # not GAT
        assert not verb_events.noun_is("gate", "GAT")          # the Dutch token does not leak in
        assert not verb_events.noun_is("bedroom", "BED")       # 'bedroom' is not 'bed'
        assert verb_events.noun_is("deur", "DEUR") is False     # a Dutch word no longer matches
    finally:
        verb_events.set_noun_canon(None)
