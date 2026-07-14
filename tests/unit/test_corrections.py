"""Curated Dutch spelling corrections (engine/data/corrections_nl.json).

The 1982 original has occasional typos. The default ('Gemoderniseerde') build corrects
them in the DISPLAYED text (messages / room descriptions / object names) while the
ORIGINAL text is always preserved and recoverable by loading with corrections disabled.
See loader.apply_corrections.
"""
from engine.data.loader import _load_corrections, load_file


def test_corrections_applied_in_displayed_text():
    w = load_file()                                  # default = modernised
    assert "belandt" in w.message_text(144) and "belant" not in w.message_text(144)
    assert "langzaam" in w.message_text(143)
    assert "onmiddellijk" in w.message_text(31)
    assert "reïncarneer" in w.message_text(166)
    assert "geïnteresseerd" in w.message_text(213)
    assert "agressief" in w.message_text(281) and "aggressief" not in w.message_text(281)
    assert "van jou te maken" in w.message_text(152)
    assert "zuidwaarts" in w.rooms[22].description \
        and "zuidwaards" not in w.rooms[22].description
    assert "dienst doet" in w.rooms[36].description
    assert "vlijmscherpe" in w.objects[10].display_name \
        and "vlijmsscherpe" not in w.objects[10].display_name


def test_original_text_is_preserved_and_recoverable():
    # The true 1982 text is the base stored in world.json and is recoverable by loading
    # with corrections disabled (the fixes live in code, never baked into the data).
    orig = load_file(corrections=False)
    assert "belant" in orig.message_text(144)
    assert "zuidwaards" in orig.rooms[22].description
    assert "vlijmsscherpe" in orig.objects[10].display_name


def test_every_correction_targets_a_real_original_string():
    orig = load_file(corrections=False)               # the 'wrong' string must exist
    corr = _load_corrections()
    assert corr["messages"] and corr["rooms"] and corr["objects"]
    for mid, subs in corr["messages"].items():
        for old, _new in subs:
            assert old in orig.message_text(mid), f"msg {mid}: {old!r} not in original"
    for rid, subs in corr["rooms"].items():
        for old, _new in subs:
            assert old in orig.rooms[rid].description, f"room {rid}: {old!r} not found"
    for oid, subs in corr["objects"].items():
        for old, _new in subs:
            assert old in orig.objects[oid].display_name, f"obj {oid}: {old!r} not found"
