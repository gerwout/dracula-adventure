"""Named access to the message table decoded from DRACULA.TXT.

The engine refers to responses by semantic name; each name resolves to a message
by a unique substring so we stay robust to any index off-by-ones while we confirm
the exact verb->message mapping from the EXE. Where the original clearly uses a
specific index we can pin it later.
"""
from __future__ import annotations


# semantic name -> unique substring that identifies the message
_NAMED = {
    "nonsense":        "Doe niet zo achterlijk",
    "cant":            "Dat gaat niet.",
    "cant_go":         "Daar kan je niet heen.",
    "cant_reach":      "Daar kan je niet bij. Het gat zit te hoog.",
    "dont_understand": "Ik begrijp er helemaal niets van.",
    "not_quite":       "Ik geloof niet dat ik je helemaal goed begrijp.",
    "what_mean":       "Eh, wat bedoel je ?",
    "not_carrying":    "Dat heb je helemaal niet bij je.",
    "take_what":       "Ik zou natuurlijk ook wel willen weten wat je zou willen pakken.",
    "drop_what":       "Moet ik soms bepalen wat je weg wilt gooien ?",
    "nothing_special": "Ik zie er niets bijzonders aan.",
    "too_heavy_total": "Dat wordt te zwaar, je zult eerst iets moeten laten",
    "grab_first":      "Dat gaat niet, je zult het eerst moeten  pakken.",
    "with_bare_hands": "Wou je dat met je blote handen proberen ??",
    "sleep_q":         "Heb je geen slaap na deze opwindende avonturen?",
    "take_it_freely":  "Je kan het gewoon pakken hoor..",
}


# Generic parser responses that live in the EXE itself (not DRACULA.TXT),
# recovered verbatim from the disassembly (docs/exe-map.md §8). The Dutch text now
# lives in engine/data/strings_nl.json (the externalised lexicon) — these class
# attributes mirror the Dutch defaults so direct `EXE.OK`-style access stays
# byte-identical, while the running engine reads a per-World copy via `eng.lex`
# (engine/data/lexicon.py) so a translation can override any of them. Offsets kept
# for provenance.
from .data.lexicon import DEFAULT as _LEX


class EXE:
    OK_TAKE = _LEX.ui("OK_TAKE")     # a single PAK success (EXE 0x1e17, string 0x1592)
    TAKEN = _LEX.ui("TAKEN")         # PAK ALLE per-item line only (EXE 0x1e40, "<name> : gepakt.")
    DROPPED = _LEX.ui("DROPPED")     # "<object name> : laten vallen."
    INV_HEADER = _LEX.ui("INV_HEADER")
    INV_EMPTY = _LEX.ui("INV_EMPTY")
    NO_SEE_A = _LEX.ui("NO_SEE_A")   # "Ik zie geen <noun> hier."
    NO_SEE_B = _LEX.ui("NO_SEE_B")
    ASSUME_A = _LEX.ui("ASSUME_A")   # "Ik neem aan dat je '<x>' bedoelt."
    ASSUME_B = _LEX.ui("ASSUME_B")
    PRESS_KEY = _LEX.ui("PRESS_KEY")
    LOAD_ERROR = _LEX.ui("LOAD_ERROR")
    OK = _LEX.ui("OK")
    # The hidden tester-feedback logbook, reached by typing "/" (EXE 0x5664).
    TESTER_HELLO = _LEX.ui("TESTER_HELLO")
    TESTER_INSTR = _LEX.ui("TESTER_INSTR")
    TESTER_PROMPT = _LEX.ui("TESTER_PROMPT")


class Messages:
    def __init__(self, world):
        self.world = world
        self._text = {mid: "\n".join(lines) for mid, lines in world.messages.items()}
        self._named: dict[str, int] = {}
        for name, needle in _NAMED.items():
            self._named[name] = self._find(needle)

    def _find(self, needle: str) -> int | None:
        for mid, text in self._text.items():
            if needle in text:
                return mid
        return None

    def by_index(self, mid: int) -> str:
        return self._text.get(mid, "")

    def named(self, name: str) -> str:
        mid = self._named.get(name)
        return self._text.get(mid, "") if mid is not None else ""
