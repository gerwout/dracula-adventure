"""Validation for player-supplied save identifiers (name / PIN / slot).

Pure, no I/O. The web layer calls these BEFORE any value reaches the save store,
so malformed or hostile input is rejected up front. See spec §3.
"""
from __future__ import annotations

import re
import unicodedata

_IDENT_RE = re.compile(r"[A-Za-z0-9 _-]{1,24}")
_PIN_RE = re.compile(r"[0-9]{6,12}")


def _normalize(s: str) -> str:
    return unicodedata.normalize("NFKC", s).strip(" \t")


def normalize_name(name: str) -> str:
    return _normalize(name)


def normalize_slot(slot: str) -> str:
    return _normalize(slot)


def valid_name(name) -> bool:
    return isinstance(name, str) and bool(_IDENT_RE.fullmatch(_normalize(name)))


def valid_pin(pin) -> bool:
    return isinstance(pin, str) and bool(_PIN_RE.fullmatch(pin))


def valid_slot(slot) -> bool:
    return isinstance(slot, str) and bool(_IDENT_RE.fullmatch(_normalize(slot)))
