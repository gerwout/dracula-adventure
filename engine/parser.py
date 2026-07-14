"""Command parser for the 2-word Dutch adventure grammar.

Faithfully reconstructed from the EXE (docs/exe-map.md):

* Tokenizer: read a line, UPPERCASE it, split into commands on '.', split each
  command into words on ' '; first word = verb, second = noun.
* Match rule: a stored token T matches an input word W by *prefix of T's stored
  length* — W[:len(T)] == T. Tokens of length <= 2 (single-letter abbreviations
  like K, I and direction letters) require exact equality to avoid shadowing.
  The table is scanned in stored order; first hit wins.
* Verb table, direction words and the exit order (NZOWHLE) are taken verbatim
  from the decoded EXE tables.
"""
from __future__ import annotations

from dataclasses import dataclass

# Exit-vector direction indices (order NZOWHLE, cross-confirmed with the TXT).
DIR_NOORD, DIR_ZUID, DIR_OOST, DIR_WEST, DIR_OMHOOG, DIR_OMLAAG, DIR_ERUIT = range(7)

# Direction table (stored token -> exit index), in a safe scan order.
_DIR_TABLE: list[tuple[str, int]] = [
    ("NOOR", DIR_NOORD), ("N", DIR_NOORD),
    ("ZUID", DIR_ZUID), ("Z", DIR_ZUID),
    ("OOST", DIR_OOST), ("O", DIR_OOST),
    ("WEST", DIR_WEST), ("W", DIR_WEST),
    ("OMHO", DIR_OMHOOG), ("HOOG", DIR_OMHOOG), ("H", DIR_OMHOOG),
    ("OMLA", DIR_OMLAAG), ("LAAG", DIR_OMLAAG), ("L", DIR_OMLAAG),
    ("ERUI", DIR_ERUIT), ("UIT", DIR_ERUIT), ("E", DIR_ERUIT),
]

# The FULL Dutch word the player types for each direction token. The parser only
# compares a word's first len(token) characters, so each stored token is just that
# many letters of the full word (NOOR = "noord"[:4]). Storing the whole word makes
# directions translatable (noord -> north); single-letter shortcuts (N, Z, ...) have
# no fuller word and map to the letter itself. Verified: word[:len(token)].upper()
# reproduces every token, so the Dutch parser is unchanged. See engine/i18n.py.
_DIR_WORDS_NL: dict[str, str] = {
    "NOOR": "noord", "N": "n",
    "ZUID": "zuid", "Z": "z",
    "OOST": "oost", "O": "o",
    "WEST": "west", "W": "w",
    "OMHO": "omhoog", "HOOG": "hoog", "H": "h",
    "OMLA": "omlaag", "LAAG": "laag", "L": "l",
    "ERUI": "eruit", "UIT": "uit", "E": "e",
}

# Verb table in stored order: (stored token, canonical action).
# Structural/artifact tokens from the EXE array are omitted.
_VERB_TABLE: list[tuple[str, str]] = [
    ("GA", "ga"), ("BETRE", "ga"), ("KRUIP", "ga"), ("LOOP", "ga"),
    ("KLIM", "ga"), ("VOLG", "ga"),
    ("KIJK", "kijk"), ("K", "kijk"),
    ("BEKIJ", "bekijk"), ("BESCHRIJF", "bekijk"), ("ONDER", "bekijk"),
    ("PAK", "pak"), ("GRIJP", "pak"), ("NEEM", "pak"), ("RAAP", "pak"),
    ("LEG", "leg"), ("ZET", "leg"), ("DROP", "leg"),
    ("GOOI", "gooi"), ("WERP", "gooi"),
    ("SHOW", "toon"), ("TOON", "toon"), ("HOUDT", "toon"), ("GEEF", "geef"),
    ("SCHIJ", "schijn"), ("BESCHIJN", "schijn"),
    # SLAAP (sleep) must precede the 3-char SLA (hit): the EXE dispatch uses exact
    # B$SCMP equality so "SLAAP" and "SLA" never collide there, but this table's
    # prefix rule would otherwise let "SLA" shadow "SLAAP" — so the more-specific
    # token is listed first.
    ("SLAAP", "slaap"),
    # DOOD/VERMO/LIQUI route to the EXE KILL handler (0x3c2c) — the innkeeper knife
    # death lives there — NOT the blunt-force hit handler 0x3afe that SLA/STOMP/… use.
    ("DOOD", "dood"), ("VERMO", "dood"), ("LIQUI", "dood"), ("SLA", "sla"),
    ("STOMP", "sla"), ("SCHOP", "sla"), ("TRAP", "sla"),
    ("HAK", "hak"), ("KAP", "hak"),
    ("VRAAG", "vraag"), ("PAS", "pas"), ("DRAAG", "draag"),
    ("FOUT", "bug"), ("BUG", "bug"), ("COMMA", "commentaar"), ("KOMMA", "commentaar"),
    ("BREEK", "breek"), ("SCHEU", "breek"), ("VERNI", "breek"),
    ("GRAAF", "graaf"), ("SCHEP", "graaf"),
    ("SPRIN", "spring"), ("DRUK", "duw"), ("DUW", "duw"), ("BLAAS", "blaas"),
    ("GIL", "gil"), ("ROEP", "gil"), ("SCHRE", "gil"), ("BRUL", "gil"),
    ("GODVE", "vloek"), ("SHIT", "vloek"), ("KUT", "vloek"),
    ("KLOOT", "vloek"), ("KANKE", "vloek"), ("GOD", "vloek"),
    ("FUCK", "vloek"), ("GEDVE", "vloek"),
    ("SLUIT", "sluit"), ("TIL", "til"), ("TREK", "trek"), ("OPEN", "open"),
    ("SAVE", "bewaar"), ("BEWAA", "bewaar"), ("SPEL", "bewaar"),
    ("LOAD", "laad"), ("LAAD", "laad"),
    # STOP/QUIT/EIND/OP/HOU all reach the EXE quit handler (0x496c). HOU (0x12ce) is a
    # distinct token from HOUDT (0x10ec -> TOON), listed earlier so it wins by prefix.
    ("QUIT", "stop"), ("EIND", "stop"), ("STOP", "stop"),
    ("HOU", "stop"), ("OP", "stop"),
    ("WACHT", "wacht"), ("RUST", "wacht"),   # SLAAP is listed earlier (before SLA)
    ("BEVES", "bevestig"), ("HANG", "hang"), ("KNOOP", "knoop"), ("ZEG", "zeg"),
    ("HELP", "help"), ("HULP", "help"),
    ("LIJST", "inventaris"), ("INVEN", "inventaris"), ("I", "inventaris"),
    ("LEES", "lees"),
    ("SESAM", "sesam"), ("HOKUS", "sesam"), ("HOCUS", "sesam"),
    ("VUL", "vul"), ("EET", "eet"), ("DRINK", "drink"), ("SNIJ", "snij"),
    ("KOOP", "koop"), ("LUIST", "luister"), ("STA", "sta"),
    # The hidden tester-feedback command: a single "/" (EXE dispatch 0x906 -> 0x5664).
    ("/", "tester"),
]

# The FULL Dutch word the player types for each verb token (the imperative betreed, not
# the 5-char BETRE the parser actually stores). Same rule as _DIR_WORDS_NL: word[:len(token)]
# is the token, so the Dutch parser is byte-identical, and a translator replaces whole
# words (betreed -> enter) from which the engine derives that language's token. K, I
# and "/" are shortcuts with no fuller word and map to themselves. (COMMA/KOMMA keep
# the literal token as their word: "commentaar"[:5] would be "comme", not "COMMA".)
_VERB_WORDS_NL: dict[str, str] = {
    "GA": "ga", "BETRE": "betreed", "KRUIP": "kruip", "LOOP": "loop",
    "KLIM": "klim", "VOLG": "volg",
    "KIJK": "kijk", "K": "k",
    "BEKIJ": "bekijk", "BESCHRIJF": "beschrijf", "ONDER": "onderzoek",
    "PAK": "pak", "GRIJP": "grijp", "NEEM": "neem", "RAAP": "raap",
    "LEG": "leg", "ZET": "zet", "DROP": "drop",
    "GOOI": "gooi", "WERP": "werp",
    "SHOW": "show", "TOON": "toon", "HOUDT": "houdt", "GEEF": "geef",
    "SCHIJ": "schijn", "BESCHIJN": "beschijn",
    "SLAAP": "slaap",
    "DOOD": "dood", "VERMO": "vermoord", "LIQUI": "liquideer", "SLA": "sla",
    "STOMP": "stomp", "SCHOP": "schop", "TRAP": "trap",
    "HAK": "hak", "KAP": "kap",
    "VRAAG": "vraag", "PAS": "pas", "DRAAG": "draag",
    "FOUT": "fout", "BUG": "bug", "COMMA": "comma", "KOMMA": "komma",
    "BREEK": "breek", "SCHEU": "scheur", "VERNI": "vernietig",
    "GRAAF": "graaf", "SCHEP": "schep",
    "SPRIN": "spring", "DRUK": "druk", "DUW": "duw", "BLAAS": "blaas",
    "GIL": "gil", "ROEP": "roep", "SCHRE": "schreeuw", "BRUL": "brul",
    "GODVE": "godverdomme", "SHIT": "shit", "KUT": "kut",
    "KLOOT": "klootzak", "KANKE": "kanker", "GOD": "god",
    "FUCK": "fuck", "GEDVE": "gedverdomme",
    "SLUIT": "sluit", "TIL": "til", "TREK": "trek", "OPEN": "open",
    "SAVE": "save", "BEWAA": "bewaar", "SPEL": "spel",
    "LOAD": "load", "LAAD": "laad",
    "QUIT": "quit", "EIND": "einde", "STOP": "stop",
    "HOU": "hou", "OP": "op",
    "WACHT": "wacht", "RUST": "rust",
    "BEVES": "bevestig", "HANG": "hang", "KNOOP": "knoop", "ZEG": "zeg",
    "HELP": "help", "HULP": "hulp",
    "LIJST": "lijst", "INVEN": "inventaris", "I": "i",
    "LEES": "lees",
    "SESAM": "sesam", "HOKUS": "hokus", "HOCUS": "hocus",
    "VUL": "vul", "EET": "eet", "DRINK": "drink", "SNIJ": "snijd",
    "KOOP": "koop", "LUIST": "luister", "STA": "sta",
    "/": "/",
}

# Scenery / interaction nouns the engine's handlers test by a FIXED Dutch token
# (verb_events.noun_is(noun, "KIST"), the named-navigation tables, ...) rather than by a
# translatable object token. To let a translation drive those too, each canonical Dutch
# token is listed with the full Dutch word the player types; a translation supplies the
# target word (kist -> chest), from which engine/i18n derives the alias CHES -> KIST that
# verb_events.canon_token / noun_is consult. word[:len(token)] reproduces every token, so
# the Dutch build is unchanged. (Many overlap object nouns; that is fine — this is the
# scenery/interaction side, kept independent of object resolution.)
_NOUN_WORDS_NL: dict[str, str] = {
    "ALLE": "alles",       # take/drop ALL
    "DEUR": "deur", "LUIK": "luik", "RAAM": "raam", "HEK": "hek", "GAT": "gat",
    "STEE": "steen", "BOOM": "boom", "GRON": "grond", "ZAND": "zand", "STOF": "stof",
    "BLOE": "bloed", "VLEK": "vlek", "VOET": "voetstappen", "SPOR": "sporen",
    "CIRK": "cirkel", "VIZI": "vizier", "TEKS": "tekst", "INSC": "inscriptie",
    "VREE": "vreemde", "TORE": "toren", "EETK": "eetkamer", "ROOS": "rooster",
    "SESA": "sesam", "BED": "bed", "SLAP": "slapen", "SLAA": "slaapkamer",
    "ZITT": "zitten", "KAST": "kasteel", "TRAP": "trap", "ZOLD": "zolder",
    "BRON": "bron", "WAAR": "waard", "MAN": "man", "HAL": "hal", "VUUR": "vuur",
    "UIT": "uit", "PIN": "pin", "DRAC": "dracula", "DOOD": "doodskist",
    # scenery aliases that also name an object (open/examine the same word):
    "KIST": "kist", "SCHA": "schat", "LADD": "ladder", "MUNT": "munt", "FLES": "fles",
    "BOEK": "boek", "KNOF": "knoflook", "TOUW": "touw", "HARN": "harnas", "DOOS": "doos",
    "TAK": "tak", "HOUT": "hout", "KRUI": "kruis", "BROO": "brood", "WATE": "water",
    "MELK": "melk", "WIG": "wig", "KAPM": "kapmes", "BIJL": "bijl", "SCHE": "scherven",
    "BRIE": "briefje", "SPIN": "spin", "KRUISS": "kruisspin",
    # named-navigation place words (engine/navigation.VERIFIED_NAMED) that are neither an
    # object nor scenery examined above -- needed so GA <place> works in the target language:
    "HERB": "herberg", "HUIS": "huis", "POOR": "poort", "GANG": "gang", "RUIM": "ruimte",
    "UITG": "uitgang", "LINK": "links", "PAD": "pad", "BINN": "binnenplaats",
    "KERK": "kerkhof", "STAA": "staan",
}

MOVE_VERBS = {"ga"}


def _match(word: str, table: list[tuple[str, object]]):
    w = word.upper()
    for token, val in table:
        if len(token) <= 2:
            if w == token:
                return val
        elif w[:len(token)] == token:
            return val
    return None


def direction_index(word: str, table=None) -> int | None:
    return _match(word, table if table is not None else _DIR_TABLE)


def match_verb(word: str, table=None) -> str | None:
    return _match(word, table if table is not None else _VERB_TABLE)


def translated_tables(verb_overrides=None, dir_overrides=None):
    """Build (verb_table, dir_table) with each source TOKEN swapped for its translated
    token (original -> translated maps). Empty maps reproduce the Dutch defaults exactly,
    so default play parses identically; a translation makes the parser accept the
    translated input words (and, via the lexicon, J/N -> Y/N etc.)."""
    vo, do = verb_overrides or {}, dir_overrides or {}
    verb_table = [(vo.get(tok, tok), action) for tok, action in _VERB_TABLE]
    dir_table = [(do.get(tok, tok), idx) for tok, idx in _DIR_TABLE]
    return verb_table, dir_table


@dataclass
class Command:
    raw: str
    verb: str | None
    verb_word: str
    noun: str | None
    direction: int | None
    # For 3+ word input the EXE echoes "Ik neem aan dat je '<assumed>' bedoelt." and
    # then processes only the first two words (EXE 0x523); None otherwise.
    assumed: str | None = None


def _classify(words: list[str], verb_table=None, dir_table=None) -> Command:
    raw = " ".join(words)
    first = words[0]
    noun = words[1] if len(words) > 1 else None
    # 3+ words -> the game assumes the first two (EXE 0x523) and echoes them.
    assumed = f"{words[0]} {words[1]}" if len(words) > 2 else None

    verb = match_verb(first, verb_table)

    # A bare SINGLE-LETTER direction (N/Z/O/W/H/L/E) is a movement command.
    # Full direction WORDS are NOT commands on their own: the real game rejects
    # bare "zuid"/"noord" ("Ik begrijp er helemaal niets van." / "Eh, wat bedoel
    # je ?") and only accepts them as the noun after GA. Single letters are the
    # movement verbs (exact-match). Verified via the DOSBox oracle (2026-07-12).
    if verb is None and len(first) == 1:
        bare_dir = direction_index(first, dir_table)
        if bare_dir is not None:
            return Command(raw, "ga", first, None, bare_dir, assumed=assumed)

    # "GA STAAN" -> stand.
    if verb == "ga" and noun and noun.upper().startswith("STA"):
        return Command(raw, "sta", first, noun, None, assumed=assumed)

    if verb in MOVE_VERBS:
        dn = direction_index(noun, dir_table) if noun else None
        return Command(raw, "ga", first, noun, dn, assumed=assumed)

    return Command(raw, verb, first, noun, None, assumed=assumed)


def parse_line(line: str, verb_table=None, dir_table=None) -> list[Command]:
    """Parse an input line into commands. ``verb_table``/``dir_table`` default to the
    Dutch module tables; the engine passes translated tables (parser.translated_tables)
    so a translation parses the player's translated input words."""
    commands: list[Command] = []
    for segment in line.upper().split("."):
        words = segment.split()
        if words:
            commands.append(_classify(words, verb_table, dir_table))
    return commands
