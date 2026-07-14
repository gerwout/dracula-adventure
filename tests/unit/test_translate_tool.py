"""Unit tests for the translation tool (tools/) and the i18n seam (engine/i18n.py).

These run headlessly (no tkinter window): the data-gathering, static room
attribution, CSV/xlsx round-trip and the Translator are all pure functions.
"""
from pathlib import Path

import pytest

from engine.data.loader import load_file
from engine.i18n import Translator
from engine.parser import _DIR_TABLE, _VERB_TABLE
from tools import translate_core as core
from tools.room_names import room_name

ENGINE_DIR = Path(__file__).resolve().parents[2] / "engine"


@pytest.fixture(scope="module")
def world():
    return load_file()


@pytest.fixture(scope="module")
def rows(world):
    return core.collect_rows(world, languages=("en",), engine_dir=ENGINE_DIR,
                             room_name_fn=room_name)


# --------------------------------------------------------------------------- #
#  Data gathering
# --------------------------------------------------------------------------- #
def test_collect_includes_all_messages(world, rows):
    non_empty = [m for m in world.messages if world.message_text(m).strip()]
    msg_rows = [r for r in rows if r["type"] == "message"]
    assert len(msg_rows) == len(non_empty)
    ids = {r["id"] for r in msg_rows}
    for m in non_empty:
        assert f"msg:{m}" in ids


def test_collect_includes_all_verbs_and_directions(rows):
    verb_rows = [r for r in rows if r["type"] == "verb"]
    # one row per verb token + one per direction word
    assert len(verb_rows) == len(_VERB_TABLE) + len(_DIR_TABLE)
    ids = {r["id"] for r in verb_rows}
    for token, _ in _VERB_TABLE:
        assert f"verb:{token}" in ids
    for token, _ in _DIR_TABLE:
        assert f"dir:{token}" in ids


def test_collect_includes_externalised_lexicon(world, rows):
    # Everything that used to be hardcoded is now in the tool (the user's complaints:
    # the secret word 'incoronium' and the startup screen were missing before).
    by_id = {r["id"]: r for r in rows}
    assert by_id["secret:word"]["dutch"] == "incoronium"
    assert by_id["answer:yes"]["dutch"] == "J"
    assert by_id["answer:no"]["dutch"] == "N"
    assert by_id["ui:OK_TAKE"]["dutch"] == "Ok"
    assert by_id["ui:INV_HEADER"]["dutch"] == "Je draagt:"
    assert by_id["ui:TESTER_HELLO"]["dutch"] == "Hallo beste tester."
    # the startup title screen: the press-a-key line and the rewrite attribution
    intro_texts = [r["dutch"] for r in rows if r["type"] == "intro"]
    assert any("Druk een toets om te beginnen" in t for t in intro_texts)
    assert any("Gerwout van der Veen" in t for t in intro_texts)
    # the new content types are all present
    assert {"ui", "answer", "secret", "intro"} <= {r["type"] for r in rows}


def test_search_now_finds_incoronium_and_startup(world):
    # Regression for "search for incoronium returns nothing" and "the beginning
    # screen can't be found" — both are in the tool now, and substring search finds them.
    rows = core.collect_rows(world, languages=("English",))
    assert core.filter_rows(rows, "incoronium", "Nederlands")
    assert core.filter_rows(rows, "toets om te beginnen", "Nederlands")


def test_collect_includes_all_real_rooms(world, rows):
    room_rows = [r for r in rows if r["type"] == "room-text"]
    real = [rid for rid, rm in world.rooms.items()
            if not rm.is_placeholder and rm.description.strip()]
    assert len(room_rows) == len(real)
    ids = {r["id"] for r in room_rows}
    for rid in real:
        assert f"room:{rid}" in ids


def test_every_row_has_dutch_source_text(rows):
    for r in rows:
        assert r["dutch"].strip() != ""


# --------------------------------------------------------------------------- #
#  Descriptive room names
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("rid, needle", [
    (0, "huis"),
    (1, "slaapkamer"),
    (12, "herberg"),
    (13, "herberg"),
    (14, "zolder"),
])
def test_room_name_sane(world, rid, needle):
    assert needle in room_name(world, rid).lower()


# --------------------------------------------------------------------------- #
#  Static message -> room attribution
# --------------------------------------------------------------------------- #
def test_message_room_attribution(world):
    attrib = core.analyze_message_rooms(ENGINE_DIR)
    # room-specific: msg 214 (BEKIJK STEEN, room 14) and msg 45 (bird, rooms 7-11)
    assert core.rooms_to_str(attrib.get(214)) == "14"
    assert core.rooms_to_str(attrib.get(45)) == "7-11"
    # a parser-failure pool message is global -> "any"
    assert core.rooms_to_str(attrib.get(8)) == "any"


def test_attribution_reflected_in_rows(rows):
    by_id = {r["id"]: r for r in rows}
    assert by_id["msg:214"]["room"] == "14"
    # room_name carries the descriptive label of room 14 (the herberg attic)
    assert "zolder" in by_id["msg:214"]["room_name"].lower()
    assert by_id["msg:8"]["room"] == "any"
    assert by_id["msg:8"]["room_name"] == ""


def test_manual_room_overrides_pin_room_specific_messages(rows):
    # Messages the AST walk can't pin (object-location / flag / nav-table / early-return
    # / computed-index gated) are filled from the curated _MANUAL_ROOMS table, so the
    # tool shows the real room instead of "any".
    by = {r["id"]: r for r in rows}
    assert by["msg:20"]["room"] == "14"          # dust -> book, herberg attic
    assert by["msg:66"]["room"] == "39"          # wall-stone rotates, at the grave
    assert by["msg:97"]["room"] == "16"          # fill the bottle at the well
    assert by["msg:264"]["room"] == "24"         # the secret revealed after the stake
    assert by["msg:271"]["room"] == "34"         # the spider, in the kruiskamer
    assert by["msg:59"]["room"] == "12"          # innkeeper reveals the attic hatch
    assert by["msg:249"]["room"] == "22"         # Dracula patrol step
    assert by["msg:30"]["room"] != "any"         # chop wood spans the forest tree rooms
    # genuinely generic / dynamic lines must STAY "any"
    assert by["msg:8"]["room"] == "any"          # parser-failure random pool
    assert by["msg:113"]["room"] == "any"        # examine the (carriable) treasure chest
    assert by["msg:80"]["room"] == "any"         # open the (carriable) box
    assert by["msg:49"]["room"] == "any"         # "Dracula blocks the exits" (follows him)
    assert by["msg:166"]["room"] == "any"        # the reincarnate prompt


def test_message_objects_are_shown(rows):
    # A message that is ABOUT a specific object gets that object in the "object" column,
    # even when it can appear in any room (a carried/present object). msg 201 = the
    # Spelregels note -> the briefje (the user's example).
    by = {r["id"]: r for r in rows}
    assert "briefje" in by["msg:201"]["object"]
    assert "boek" in by["msg:109"]["object"]          # examine the book
    assert "schatkist" in by["msg:113"]["object"]     # examine the treasure chest
    assert "lantaren" in by["msg:175"]["object"]      # "you have no lamp" -> the lamp
    assert by["msg:201"]["room"] == "any"             # object context, not a fixed room
    # a purely generic message has no object, and object rows are a fixed column
    assert by["msg:8"]["object"] == ""                # parser-failure pool
    assert "object" in core.FIXED_COLUMNS and "object" not in core.languages_of(rows)


def test_manual_objects_reference_real_messages_and_objects(world):
    for mid, obj_ids in core._MANUAL_OBJECTS.items():
        assert world.message_text(mid).strip(), f"msg {mid} is empty"
        for oid in obj_ids:
            o = world.objects.get(oid)
            assert o is not None and o.is_real, f"msg {mid} -> invalid object {oid}"


def test_dead_messages_are_marked_unreachable(rows):
    # RE-confirmed dead messages (no emission path in the original game) are labelled
    # distinctly -- "dead" -- so translators can see they are never shown, instead of
    # being lumped in with the generic "any" messages.
    by = {r["id"]: r for r in rows}
    assert core.DEAD_MESSAGES                      # non-empty (146, 198, 93)
    for mid in core.DEAD_MESSAGES:
        r = by[f"msg:{mid}"]
        assert r["room"] == "dead", mid
        assert "onbereikbaar" in r["room_name"], mid


def test_manual_rooms_reference_real_messages_and_rooms(world):
    # Guard the curated table: every key is a real, non-empty message and every value
    # is a real (non-placeholder) room.
    for mid, room_ids in core._MANUAL_ROOMS.items():
        assert world.message_text(mid).strip(), f"msg {mid} is empty/not shown"
        for rid in room_ids:
            assert rid in world.rooms and not world.rooms[rid].is_placeholder, \
                f"msg {mid} -> invalid room {rid}"


# --------------------------------------------------------------------------- #
#  CSV / xlsx round-trip (must be lossless)
# --------------------------------------------------------------------------- #
def test_csv_roundtrip_lossless(rows, tmp_path):
    # simulate a couple of edits, incl. tricky characters
    edited = [dict(r) for r in rows]
    edited[0]["en"] = "Hello\nworld"
    edited[5]["en"] = 'quotes "and" comma, semicolon;'
    path = tmp_path / "t.csv"
    core.export_csv(edited, path)
    back = core.import_csv(path)
    assert back == edited


def test_csv_string_roundtrip_lossless(rows):
    text = core.export_csv_string(rows)
    assert core.import_csv_string(text) == rows


@pytest.mark.skipif(not core.xlsx_available(), reason="openpyxl not installed")
def test_xlsx_roundtrip_lossless(rows, tmp_path):
    edited = [dict(r) for r in rows]
    edited[0]["en"] = "Hello\nworld"
    path = tmp_path / "t.xlsx"
    core.export_xlsx(edited, path)
    assert core.import_xlsx(path) == edited


def test_multiple_language_columns(world):
    rows = core.collect_rows(world, languages=("en", "fr", "de"),
                             engine_dir=ENGINE_DIR, room_name_fn=room_name)
    assert core.languages_of(rows) == ["en", "fr", "de"]
    assert core.columns_of(rows) == core.FIXED_COLUMNS + ["en", "fr", "de"]


# --------------------------------------------------------------------------- #
#  i18n Translator seam
# --------------------------------------------------------------------------- #
def test_default_translator_is_noop():
    tr = Translator()
    assert tr.is_default()
    w = load_file(translator=tr)
    # byte-identical to a plain load
    assert w.message_text(4) == load_file().message_text(4)


def test_en_translation_overrides_message_only():
    dutch = load_file().message_text(4)
    tr = Translator.from_rows(
        [{"id": "msg:4", "en": "I would not do that if I were you."},
         {"id": "room:0", "en": "You are now in your own house."}],
        "en")
    assert not tr.is_default()
    w_en = load_file(translator=tr)
    assert w_en.message_text(4) == "I would not do that if I were you."
    assert w_en.rooms[0].lines[0] == "You are now in your own house."
    # nl stays unchanged on a fresh load
    assert load_file().message_text(4) == dutch


def test_translator_applies_lexicon_overrides_end_to_end():
    # A translation flows through to the running engine: UI strings, the secret word,
    # the J/N answer letters, AND the verb/direction input tokens — nothing hardcoded.
    from engine.game import Engine
    from engine.io import ScriptedIO
    from engine.parser import match_verb, direction_index

    tr = Translator.from_rows([
        {"id": "ui:OK_TAKE", "en": "Taken."},
        {"id": "answer:no", "en": "Q"},          # deliberately not the Dutch 'N'
        {"id": "secret:word", "en": "opensesame"},
        {"id": "verb:PAK", "en": "TAKE"},
        {"id": "dir:NOOR", "en": "NORTH"},
    ], "en")
    assert not tr.is_default()
    w = load_file(translator=tr)
    assert w.lexicon.ui("OK_TAKE") == "Taken."
    assert w.lexicon.answer("no") == "Q"
    assert w.lexicon.secret == "opensesame"

    eng = Engine(w, ScriptedIO([]))
    # the parser accepts the translated input words, and the old Dutch token is gone
    assert match_verb("TAKE", eng._verb_table) == "pak"
    assert match_verb("pak", eng._verb_table) is None
    assert direction_index("NORTH", eng._dir_table) is not None
    # the death prompt now ends on the translated 'no' letter 'Q'
    eng.room = 25
    eng.io = ScriptedIO(["q"])
    eng.submit("spring")
    assert eng.dead and not eng.running

    # nl stays byte-identical on a fresh default load
    assert load_file().lexicon.ui("OK_TAKE") == "Ok"


def test_translator_from_csv_roundtrip(world, tmp_path):
    rows = core.collect_rows(world, languages=("en",), engine_dir=ENGINE_DIR,
                             room_name_fn=room_name)
    by_id = {r["id"]: r for r in rows}
    by_id["msg:4"]["en"] = "Translated four."
    path = tmp_path / "dracula_en.csv"
    core.export_csv(rows, path)
    tr = Translator.from_csv(path, "en")
    assert tr.messages[4] == "Translated four."
    w_en = load_file(translator=tr)
    assert w_en.message_text(4) == "Translated four."


# --------------------------------------------------------------------------- #
#  The GUI module must import cleanly even without a display
# --------------------------------------------------------------------------- #
def test_gui_module_importable():
    import tools.translate_gui as g
    assert hasattr(g, "TranslatorApp")
    assert hasattr(g, "collect_rows")
    assert hasattr(g, "main")


def test_gui_build_rows_prefills_bundled_translations():
    # The tool must open showing the shipped translations, not blank columns: build_rows
    # pre-fills each language column (keyed by CODE, matching the game's loader) from its
    # engine/data/i18n/dracula_<code>.csv.
    from tools.translate_gui import build_rows
    rows = build_rows()
    by = {r["id"]: r for r in rows}
    assert by["verb:PAK"]["en"] == "take"
    assert by["obj:19"]["en"] == "golden necklace"
    assert by["noun:HEK"]["en"] == "gate"
    assert "Coffin News Network" in by["msg:281"]["en"]
    assert all(r.get("en") for r in rows), "every row should open pre-filled in English"


def test_filter_rows_by_language_substring():
    from tools import translate_core as core
    from engine.data.loader import load_file
    rows = core.collect_rows(load_file(), languages=("English",))
    # search "Dracula" in the source (Nederlands -> the 'dutch' key); the "object"
    # column is always searched too, so a hit is in the dutch OR the object text.
    hits = core.filter_rows(rows, "Dracula", "Nederlands")
    assert hits, "expected some Dutch strings mentioning Dracula"
    assert all("dracula" in (r["dutch"] + r.get("object", "")).lower() for r in hits)
    assert len(hits) < len(rows)                      # actually filtered
    # empty query returns everything; a nonsense query -> no hits
    assert core.filter_rows(rows, "", "Nederlands") == rows
    assert core.filter_rows(rows, "zzzznotfound", "Nederlands") == []
    # case-insensitive, and searches the chosen language column
    rows[0]["English"] = "The Dracula treasure"
    assert rows[0] in core.filter_rows(rows, "dracula", "English")


def test_object_names_are_in_the_table_and_searchable():
    from tools import translate_core as core
    from engine.data.loader import load_file
    rows = core.collect_rows(load_file(), languages=("English",))
    by = {r["id"]: r for r in rows}
    # object display names are now translatable rows (they used to be missing entirely)
    assert by["obj:19"]["dutch"] == "gouden halsband" and by["obj:19"]["type"] == "object"
    assert "gouden munten" in by["obj:13"]["dutch"]
    # so the walkthrough's "gouden halsband" / "gouden munten" are findable now
    assert "obj:19" in {r["id"] for r in core.filter_rows(rows, "halsband", "Nederlands")}
    assert {r["id"] for r in core.filter_rows(rows, "gouden munten", "Nederlands")} \
        >= {"obj:13", "msg:113"}
    # the object column itself is searched: a row related to the doodskist matches "dracula"
    obj_hits = [r for r in core.filter_rows(rows, "kruisspin", core.ANY_LANGUAGE)
                if "kruisspin" in r.get("object", "").lower()]
    assert obj_hits


def test_object_name_translation_flows_to_the_game():
    tr = Translator.from_rows([{"id": "obj:19", "en": "golden necklace"},
                               {"id": "obj:13", "en": "chest of gold coins"}], "en")
    assert not tr.is_default()
    w = load_file(translator=tr)
    assert w.objects[19].display_name == "golden necklace"
    assert w.objects[13].display_name == "chest of gold coins"
    # nl stays as the (corrected) original on a plain load
    assert load_file().objects[19].display_name == "gouden halsband"


def test_object_input_nouns_are_full_translatable_words(world):
    from engine.data.object_nouns import load_object_nouns_nl, noun_token
    rows = core.collect_rows(world, languages=("English",))
    by = {r["id"]: r for r in rows}
    # the FULL Dutch words the player types are translatable rows (not cryptic tokens)
    assert by["objnoun:3"]["dutch"] == "knoflook, streng"
    assert by["objnoun:3"]["type"] == "obj-noun"
    assert by["objnoun:3"]["object"] == "streng knoflook"
    # fidelity guard: the Dutch full words derive EXACTLY DRACULA.TXT's original tokens,
    # so the Dutch build's parser is unchanged.
    nouns = load_object_nouns_nl()
    for oid, o in world.objects.items():
        if o.is_real and o.tokens:
            assert oid in nouns, f"obj {oid} has tokens but no noun entry"
            assert [noun_token(w) for w in nouns[oid]] == list(o.tokens), oid


def test_translating_an_object_noun_makes_it_typeable_in_the_target_language():
    from engine.data.model import CARRIED
    from engine.game import Engine
    from engine.io import ScriptedIO
    tr = Translator.from_rows([{"id": "objnoun:3", "en": "garlic, string"}], "en")
    w = load_file(translator=tr)
    assert w.objects[3].tokens == ["GARL", "STRI"]     # knoflook -> garlic -> token GARL
    eng = Engine(w, ScriptedIO([]))
    eng.obj_loc[3] = CARRIED
    assert eng.resolve("garlic") == 3                  # the translated noun now resolves
    assert eng.resolve("garl") == 3                    # (parser matches the 4-char prefix)
    assert eng.resolve("knoflook") is None             # the Dutch noun no longer does
    assert load_file().objects[3].tokens == ["KNOF", "STRE"]   # nl unchanged


def test_verb_and_direction_rows_are_full_words(world):
    # The tool shows the FULL Dutch word the player types (pak, betreed, noord), not the
    # cryptic parser token (PAK, BETRE, NOOR) -- that is what a translator works with and
    # what the messages refer to.
    rows = core.collect_rows(world, languages=("en",), engine_dir=ENGINE_DIR,
                             room_name_fn=room_name)
    by = {r["id"]: r for r in rows}
    assert by["verb:PAK"]["dutch"] == "pak"
    assert by["verb:BETRE"]["dutch"] == "betreed"
    assert by["verb:BESCHRIJF"]["dutch"] == "beschrijf"
    assert by["dir:NOOR"]["dutch"] == "noord"
    assert by["dir:N"]["dutch"] == "n"                 # single-letter shortcut
    # fidelity guard: every verb/direction full word derives EXACTLY its original token
    # (its first len(token) chars, uppercased), so the Dutch parser is byte-identical.
    for token, _ in _VERB_TABLE:
        word = by[f"verb:{token}"]["dutch"]
        assert word[:len(token)].upper() == token, (token, word)
    for token, _ in _DIR_TABLE:
        word = by[f"dir:{token}"]["dutch"]
        assert word[:len(token)].upper() == token, (token, word)


def test_translating_a_verb_full_word_makes_it_parse_in_english():
    # The player types the full English word; the engine derives its parser token
    # (enter -> ENTE) exactly as it does for object nouns (garlic -> GARL), so the Dutch
    # word stops working and the English one starts.
    from engine.game import Engine
    from engine.io import ScriptedIO
    from engine.parser import match_verb, direction_index
    tr = Translator.from_rows([
        {"id": "verb:PAK", "en": "take"},              # a lowercase full word...
        {"id": "verb:BETRE", "en": "enter"},           # ...longer than its 5-char token
        {"id": "dir:NOOR", "en": "north"},
    ], "en")
    assert not tr.is_default()
    w = load_file(translator=tr)
    eng = Engine(w, ScriptedIO([]))
    assert match_verb("take", eng._verb_table) == "pak"        # PAK action
    assert match_verb("enter", eng._verb_table) == "ga"        # BETRE routes to 'ga'
    assert direction_index("north", eng._dir_table) is not None
    assert match_verb("pak", eng._verb_table) is None          # the Dutch word is gone
    # nl stays byte-identical on a plain default load
    assert match_verb("pak") == "pak" and match_verb("take") is None


def test_source_language_endonym_and_key():
    from tools import translate_core as core
    assert core.SOURCE_LANGUAGE == "Nederlands"
    assert core.language_key("Nederlands") == "dutch"
    assert core.language_key("English") == "English"
