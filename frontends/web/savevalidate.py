"""Validation for player-supplied save identifiers (name / PIN / slot).

Pure, no I/O. The web layer calls these BEFORE any value reaches the save store,
so malformed or hostile input is rejected up front. See spec §3.
"""
from __future__ import annotations

import re
import unicodedata

_NAME_RE = re.compile(r"^[A-Za-z0-9 _-]{1,24}$")
_PIN_RE = re.compile(r"^[0-9]{6,12}$")
_SLOT_RE = re.compile(r"^[A-Za-z0-9 _-]{1,24}$")


def normalize_name(name: str) -> str:
    return unicodedata.normalize("NFKC", name).strip()


def normalize_slot(slot: str) -> str:
    return unicodedata.normalize("NFKC", slot).strip()


def valid_name(name) -> bool:
    return isinstance(name, str) and bool(_NAME_RE.match(normalize_name(name)))


def valid_pin(pin) -> bool:
    return isinstance(pin, str) and bool(_PIN_RE.match(pin))


def valid_slot(slot) -> bool:
    return isinstance(slot, str) and bool(_SLOT_RE.match(normalize_slot(slot)))
