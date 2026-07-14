"""Tests for the shipped engine/data/world.json asset and its faithful provenance."""
import hashlib
import json
from pathlib import Path

import pytest

from engine.data.loader import DEFAULT_TXT, load

WORLD_JSON = Path(__file__).resolve().parents[2] / "engine" / "data" / "world.json"


def test_world_json_exists_and_has_meta():
    d = json.loads(WORLD_JSON.read_text(encoding="utf-8"))
    assert d["meta"]["schema"] == 1
    assert d["meta"]["source"] == "DRACULA.TXT"
    assert d["meta"]["source_length"] == 103168
    assert len(d["meta"]["sha256"]) == 64
    for section in ("header", "rooms", "messages", "objects"):
        assert d[section], f"empty section: {section}"


@pytest.mark.skipif(not DEFAULT_TXT.exists(), reason="original DRACULA.TXT not available")
def test_world_json_is_a_faithful_serialisation_of_the_original():
    data = DEFAULT_TXT.read_bytes()
    d = json.loads(WORLD_JSON.read_text(encoding="utf-8"))
    assert d["meta"]["source_length"] == len(data)
    assert d["meta"]["sha256"] == hashlib.sha256(data).hexdigest()
    expect = load(data).to_dict()
    assert {k: d[k] for k in ("header", "rooms", "messages", "objects")} == expect


from engine.data.loader import load_file, load_json   # noqa: E402


def test_load_json_reconstructs_int_keys_and_counts():
    w = load_json(corrections=False)
    assert w.rooms and all(isinstance(k, int) for k in w.rooms)
    room_start, message_start, object_start, cont_start, _total = w.header
    assert len(w.rooms) == message_start - room_start
    assert len(w.messages) == object_start - message_start
    assert len(w.objects) == cont_start - object_start


def test_load_json_default_applies_corrections_in_code():
    corrected = load_json()                 # default: corrections on
    original = load_json(corrections=False)  # uncorrected base (as stored in world.json)
    assert "belandt" in corrected.message_text(144)
    assert "belant" in original.message_text(144)


def test_load_file_no_path_uses_world_json_and_carries_no_raw_bytes():
    w = load_file()
    assert w.rooms and w.messages and w.objects
    assert w.raw == b""      # JSON-loaded worlds have no pre-decode bytes


def test_embedded_nul_survives_json_and_renders_as_space():
    w = load_json(corrections=False)
    nul_ids = [mid for mid in (41, 42, 157, 207) if "\x00" in "\n".join(w.messages[mid])]
    assert nul_ids, "expected an embedded NUL in messages 41/42/157/207 to survive JSON"
    for mid in nul_ids:
        assert "\x00" not in w.message_text(mid)     # rendered as a space for frontends
