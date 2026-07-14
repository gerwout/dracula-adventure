"""Language-neutral rendering of the winning walkthrough.

The walkthrough is a sequence of *actions* — a verb plus a direction / object / scenery
noun — identified by the engine's canonical (Dutch) tokens. From those tokens we can
render the surface commands for ANY language by reading that language's vocabulary out
of the translation data. So one walkthrough drives the playthrough test in every
registered language, and adding a language needs no test changes at all.

``derive_canonical`` turns the human-readable Dutch walkthrough (tests/unit/
test_full_playthrough.WALKTHROUGH) into that token form; ``load_vocab`` reads a
language's words; ``render`` maps a canonical step back to a surface command.
"""
from pathlib import Path

from engine.data.loader import load_file
from engine.data.object_nouns import load_object_nouns_nl, noun_token
from engine.parser import (_VERB_TABLE, _DIR_TABLE, _NOUN_WORDS_NL)
from engine.i18n import SOURCE_LANG, _I18N_DIR
from tools import translate_core as core

# A handful of walkthrough nouns whose Dutch 4-char prefix does NOT identify the object
# the command acts on (they collide with a scenery token, or the object has no scenery
# alias): pin them to the object explicitly. Language-independent, so adding a language
# never touches this.
#   schep (shovel) -> obj29, but "schep"[:4] == SCHE == scherven (shards)
#   lamp/hamer/necklace name objects that have no scenery alias of their own
_OBJECT_OVERRIDE = {"schep": 29, "lamp": 0, "hamer": 32, "halsband": 19, "hals": 19}


def _verb_token(word: str) -> str:
    """The verb token a Dutch word denotes, by the parser's own rule (exact for <=2
    chars, else prefix; table order, so SLAAP wins over SLA)."""
    u = word.upper()
    for tok, _action in _VERB_TABLE:
        if (u == tok) if len(tok) <= 2 else (u[: len(tok)] == tok):
            return tok
    raise KeyError(f"no verb token for {word!r}")


def _dir_token(word: str):
    """The direction token a word denotes (parser rule: exact for <=2 chars, else
    prefix), or None if the word is not a direction."""
    u = word.upper()
    for tok, _idx in _DIR_TABLE:
        if (u == tok) if len(tok) <= 2 else (u[: len(tok)] == tok):
            return tok
    return None


def _scenery_token(word: str):
    """The longest canonical scenery token that is a prefix of `word` (kruisspin ->
    KRUISS before KRUI), or None."""
    u = word.upper()
    best = None
    for tok in _NOUN_WORDS_NL:
        if u[: len(tok)] == tok and (best is None or len(tok) > len(best)):
            best = tok
    return best


def derive_canonical(walkthrough, secret_word="incoronium"):
    """Turn a Dutch walkthrough (list of command strings) into canonical steps.

    Each step is ``(verb_token | None, noun)`` where noun is one of
    ``None`` | ``("dir", TOK)`` | ``("obj", id)`` | ``("scn", TOK)`` | ``("secret",)``.
    """
    steps = []
    for cmd in walkthrough:
        low = cmd.strip().lower()
        if low == secret_word:
            steps.append((None, ("secret",)))
            continue
        words = low.split()
        verb = _verb_token(words[0])
        if len(words) == 1:
            steps.append((verb, None))
            continue
        w = words[1]
        dtok = _dir_token(w)
        if dtok is not None:
            steps.append((verb, ("dir", dtok)))
        elif w in _OBJECT_OVERRIDE:
            steps.append((verb, ("obj", _OBJECT_OVERRIDE[w])))
        else:
            stok = _scenery_token(w)
            if stok is None:
                raise KeyError(f"cannot classify noun {w!r} in {cmd!r}")
            steps.append((verb, ("scn", stok)))
    return steps


class Vocab:
    """A language's words for rendering: verb/direction/object/scenery + the secret."""

    def __init__(self, verb, direction, obj, scenery, secret):
        self.verb, self.dir, self.obj, self.scn, self.secret = \
            verb, direction, obj, scenery, secret


def load_vocab(lang: str) -> Vocab:
    """Build a :class:`Vocab` for `lang` from the translation data — the Dutch source
    words for ``nl``, else the bundled CSV's language column."""
    if lang == SOURCE_LANG:
        rows = core.collect_rows(load_file(), languages=("en",))
        def val(r): return r["dutch"]
    else:
        rows = core.import_csv(_I18N_DIR / f"dracula_{lang}.csv")
        def val(r): return r.get(lang, "")

    verb, direction, obj, scenery, secret = {}, {}, {}, {}, ""
    for r in rows:
        kind, _, key = r["id"].partition(":")
        v = val(r)
        if kind == "verb":
            verb[key] = v
        elif kind == "dir":
            direction[key] = v
        elif kind == "objnoun":
            obj[int(key)] = v.split(",")[0].strip()      # first noun names the object
        elif kind == "noun":
            scenery[key] = v
        elif kind == "secret":
            secret = v
    return Vocab(verb, direction, obj, scenery, secret)


def render(step, vocab: Vocab) -> str:
    """Render one canonical step to a surface command in `vocab`'s language."""
    verb, noun = step
    if noun == ("secret",):
        return vocab.secret
    vw = vocab.verb[verb]
    if noun is None:
        return vw
    kind, key = noun
    word = {"dir": vocab.dir, "obj": vocab.obj, "scn": vocab.scn}[kind][key]
    return f"{vw} {word}"


def render_walkthrough(walkthrough, lang: str):
    """The full walkthrough rendered as surface commands for `lang`."""
    vocab = load_vocab(lang)
    return [render(step, vocab) for step in derive_canonical(walkthrough)]
