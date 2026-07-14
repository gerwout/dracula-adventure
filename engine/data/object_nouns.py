"""Object parser-nouns as full words, so they can be translated.

The parser matches a typed noun by its first 4 characters (engine/parser.py rule), so
each object's parser token is just the first 4 chars of a full word. Storing the FULL
Dutch word the player types (object_nouns_nl.json) makes the noun translatable: the tool
shows "knoflook", a translator writes "garlic", and the engine derives that language's
token GARL = noun_token("garlic"). The Dutch defaults derive exactly DRACULA.TXT's
tokens, so the Dutch build is unchanged.
"""
from __future__ import annotations

import json
from pathlib import Path

TOKEN_LEN = 4
_PATH = Path(__file__).resolve().parent / "object_nouns_nl.json"


def noun_token(word: str) -> str:
    """The parser token for a full noun word: its first TOKEN_LEN chars, uppercased."""
    return word.strip()[:TOKEN_LEN].upper()


def load_object_nouns_nl() -> dict[int, list[str]]:
    """{object id -> [full Dutch words the player can type]} (empty on any load error)."""
    try:
        data = json.loads(_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out: dict[int, list[str]] = {}
    for key, words in data.get("nouns", {}).items():
        try:
            out[int(key)] = [str(w) for w in words]
        except (ValueError, TypeError):
            continue
    return out
