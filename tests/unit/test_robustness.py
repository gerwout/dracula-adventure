"""The engine must never crash on any input, across every verb group."""
from engine.game import new_game
from engine.io import ScriptedIO


ALL_VERB_SAMPLES = [
    "kijk", "k", "i", "inventaris", "lijst",
    "ga west", "noord", "z", "omhoog", "omlaag", "eruit",
    "pak lamp", "neem bijl", "grijp touw", "raap munt",
    "drop lamp", "leg bijl", "zet doos",
    "gooi bijl", "werp mes", "geef munt", "toon boek", "show hamer", "houdt kruis",
    "bekijk bed", "onderzoek kist", "beschrijf deur", "lees briefje",
    "schijn lamp", "beschijn deur",
    "dood dracula", "vermoord waard", "sla spin", "stomp man", "schop deur",
    "trap hek", "hak boom", "kap hout",
    "vraag waard", "pas harnas", "draag harnas",
    "breek stok", "scheur papier", "vernietig kist",
    "graaf noord", "schep zand", "spring gat", "druk knop", "duw steen", "blaas fluit",
    "gil", "roep waard", "schreeuw", "brul",
    "godverdomme", "shit", "kut", "fuck", "kanker",
    "sluit deur", "til kist", "trek touw", "open luik",
    "wacht", "rust", "slaap", "bevestig touw", "hang ladder", "knoop touw", "zeg sesam",
    "help", "hulp", "sesam", "hokus", "hocus",
    "vul fles", "eet brood", "drink water", "snij hout", "koop munt", "luister", "sta op",
    "bug", "fout",
    "", "   ", "xyzzy plugh", "a.b.c", "pak", "ga", "onzin woord hier",
]


def test_engine_never_crashes_on_any_verb():
    io = ScriptedIO(ALL_VERB_SAMPLES + ["stop"])
    eng = new_game(io)
    eng.play()          # must complete without raising
    # every input produced *some* response (no silent swallow that loops forever)
    assert io.text.strip()


def test_multi_command_lines_all_execute():
    io = ScriptedIO(["ga zuid. pak lamp. i. n", "stop"])
    eng = new_game(io)
    eng.play()
    assert "Ok" in io.text
    assert "Je draagt:" in io.text
