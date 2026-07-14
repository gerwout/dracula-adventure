"""One winning walkthrough, played in every registered language.

The walkthrough lives once, in Dutch (tests/unit/test_full_playthrough.WALKTHROUGH). Here
it is reduced to canonical engine tokens and re-rendered into each language from that
language's translation data, then played to the win. Adding a language is adding its CSV
to engine/data/i18n/ and its code to engine.i18n.AVAILABLE_LANGUAGES — no test changes.
"""
import re
import sys
from pathlib import Path

import pytest

from engine.game import new_game
from engine.io import ScriptedIO
from engine.data.model import CARRIED
from engine.i18n import AVAILABLE_LANGUAGES
from engine.parser import _NOUN_WORDS_NL
from engine.navigation import VERIFIED_NAMED

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_full_playthrough import WALKTHROUGH                      # noqa: E402
from i18n_walkthrough import (derive_canonical, render_walkthrough,  # noqa: E402
                              load_vocab, render)

ENGINE = Path(__file__).resolve().parents[2] / "engine"


def _carried(eng):
    return frozenset(o for o, v in eng.obj_loc.items() if v == CARRIED)


@pytest.mark.parametrize("lang", list(AVAILABLE_LANGUAGES))
def test_walkthrough_wins_in_every_language(lang):
    cmds = render_walkthrough(WALKTHROUGH, lang)
    eng = new_game(ScriptedIO([]), explore=True, lang=lang)
    eng.submit(" . ".join(cmds))
    assert eng.won, f"{lang}: ended in room {eng.room}, dead={eng.dead}"


def test_all_languages_stay_in_lockstep_with_dutch():
    # Every language must mirror the Dutch run state-for-state (same room + inventory
    # after each command) — the translation changes words, never behaviour.
    canonical = derive_canonical(WALKTHROUGH)
    vocabs = {lang: load_vocab(lang) for lang in AVAILABLE_LANGUAGES}
    engines = {lang: new_game(ScriptedIO([]), explore=True, lang=lang)
               for lang in AVAILABLE_LANGUAGES}
    for step in canonical:
        ref = None
        for lang, eng in engines.items():
            eng.submit(render(step, vocabs[lang]))
            state = (eng.room, _carried(eng))
            if ref is None:
                ref = state
            else:
                assert state == ref, f"{lang} diverged at {step}"
    assert all(e.won for e in engines.values())


def test_canonical_derivation_classifies_every_command():
    # Guards the DSL: if the Dutch walkthrough gains a verb/noun the deriver can't place,
    # this fails loudly instead of silently mis-rendering.
    steps = derive_canonical(WALKTHROUGH)
    assert len(steps) == len(WALKTHROUGH)
    for (verb, noun), cmd in zip(steps, WALKTHROUGH):
        assert verb is not None or noun == ("secret",), cmd


def test_every_scenery_ref_has_a_translation_alias():
    # The canonical fix makes noun_is()/navigation match a translated word ONLY via the
    # alias map, so EVERY fixed Dutch token the engine checks must have a noun: row (else
    # that interaction would be impossible in any non-Dutch language). This guarantees it.
    refs = set()
    for fname in ("verb_events.py", "navigation.py"):
        src = (ENGINE / fname).read_text(encoding="utf-8")
        refs |= set(re.findall(r'noun_is\([^,]+,\s*"([A-Z]+)"\)', src))
    refs |= {tok for _room, tok in VERIFIED_NAMED}          # named-navigation tokens
    refs.discard("STAA")  # reached only via the parser's GA-STAAN->STA rewrite, resolved by token
    missing = sorted(r for r in refs if r not in _NOUN_WORDS_NL)
    assert not missing, f"scenery tokens with no translatable noun: row: {missing}"
