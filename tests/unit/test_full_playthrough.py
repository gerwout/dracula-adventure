"""Full start-to-finish playthrough of Dracula Avontuur: a fresh game -> WON.

The strongest integration test in the suite: it drives the ENTIRE game from a new
game (room 0, empty-handed) to the winning TROS ending in a single verified sequence
of 188 in-game commands, exercising every major subsystem end to end -- the parser and
named/special navigation, the full puzzle state machine (tower activation, the RNG
Dracula spawn, the multi-turn patrol + stake, the Sesam door, the spider, the armour
vehicle through the fire), the carry limit, and the coffin-slide win. If any of those
regresses, this stops reaching room 11 with the treasure.

The command line doubles as a manual "watch it win" demo: paste it (as one line, on the
CLI or in the GUI after the title screen) and the game plays itself to the ending.
"""
from engine.data.model import CARRIED
from engine.game import new_game
from engine.io import ScriptedIO

# The verified winning walkthrough, one command per element (joined with " . ").
WALKTHROUGH = [
    # 1. house: note, spade via the window, lamp, coin; empty the milk bottle
    'pak briefje',
    'ga raam',
    'pak schep',
    'ga raam',
    'ga zuid',
    'pak lamp',
    'ga noord',
    'ga oost',
    'pak munt',
    'pak fles',
    'drink melk',
    'leg briefje',
    # 2. herberg: buy the garlic, blow the dust off the Vampier Handboeck
    'ga west',
    'ga west',
    'ga herberg',
    'ga zitten',
    'luister',
    'luister',
    'ga staan',
    'koop knoflook',
    'vraag waard',
    'ga zolder',
    'blaas stof',
    'pak boek',
    'lees boek',
    'leg boek',
    'ga omlaag',
    # 3. forest: the cleaver and the wooden wedge in the tree hut
    'ga eruit',
    'ga noord',
    'ga oost',
    'ga west',
    'ga omhoog',
    'pak kapmes',
    'pak wig',
    # 4. castle: stash spares, fetch the ladder, view the well, activate + banish Dracula, leave (door slams)
    'ga omlaag',
    'ga noord',
    'ga oost',
    'ga west',
    'leg wig',
    'leg kapmes',
    'leg munt',
    'leg schep',
    'ga noord',
    'ga kasteel',
    'ga kasteel',
    'ga west',
    'ga zuid',
    'ga omlaag',
    'ga omlaag',
    'ga poort',
    'pak ladder',
    'ga west',
    'ga omhoog',
    'ga omhoog',
    'ga omhoog',
    'ga raam',
    'ga omlaag',
    'ga omlaag',
    'leg ladder',
    'ga gat',
    'ga west',
    'ga omhoog',
    'bekijk toren',
    'ga omlaag',
    'ga oost',
    'ga omlaag',
    'schijn dracula',
    'gooi knoflook',
    'pak ladder',
    'ga noord',
    'ga oost',
    'ga deur',
    'ga omlaag',
    'ga omlaag',
    'leg knoflook',
    'pak munt',
    # 5. poison the well: throw the coin in, fill the (emptied) bottle
    'ga bron',
    'ga oost',
    'gooi munt',
    'vul fles',
    'ga west',
    'ga west',
    'ga huis',
    'ga slaap',
    # 6. sleep -> cellar via the bed-hatch: the axe and (from the box) the hammer
    'slaap',
    'schijn bed',
    'open luik',
    'ga luik',
    'pak bijl',
    'open doos',
    'pak hamer',
    'ga omhoog',
    'ga noord',
    'ga west',
    'pak kapmes',
    'ga noord',
    # 7. forge the cross: hack wood from the tree, carve it with the cleaver
    'ga oost',
    'ga west',
    'ga omhoog',
    'hak boom',
    'pak hout',
    'snij hout',
    'leg bijl',
    'leg kapmes',
    'ga omlaag',
    'ga noord',
    'ga oost',
    'ga west',
    'ga huis',
    # 8. the rope: ladder to the ceiling gat -> attic -> take the rope
    'leg ladder',
    'ga gat',
    'pak touw',
    'ga omlaag',
    'ga west',
    'pak schep',
    'pak wig',
    'ga huis',
    'ga zuid',
    # 9. dig into the tomb: reclaim spade + wedge, tunnel from the cellar
    'ga luik',
    'graaf west',
    'graaf noord',
    'duw steen',
    'ga steen',
    'leg schep',
    'open kist',
    'volg dracula',
    'volg dracula',
    'volg dracula',
    'volg dracula',
    # 10. open the coffin, follow Dracula to room 24, show the cross, stake the wedge
    'volg dracula',
    'toon kruis',
    'sla wig',
    'kijk',
    'pak halsband',
    'leg kruis',
    'leg hamer',
    'ga omhoog',
    # 11-12. fetch the armour, open the Sesam door with 'incoronium', poison the spider
    'ga omlaag',
    'ga noord',
    'ga oost',
    'pak harnas',
    'ga west',
    'ga zuid',
    'ga omlaag',
    'incoronium',
    'ga sesam',
    'gooi fles',
    'leg harnas',
    'draag harnas',
    'ga vuur',
    # 13. don the armour, cross the fire to the treasure chamber, take the chest
    'trek harnas',
    'pak schatkist',
    'draag harnas',
    'ga vuur',
    'trek harnas',
    # 14. coffin ride home: tie the rope, position the empty coffin, ride it down with the treasure
    'ga west',
    'ga omhoog',
    'ga noord',
    'ga west',
    'ga zuid',
    'ga zuid',
    'knoop touw',
    'leg lamp',
    'leg schat',
    'leg hals',
    'ga noord',
    'ga eruit',
    'ga oost',
    'ga zuid',
    'ga omlaag',
    'ga omlaag',
    'open hek',
    'ga hek',
    'pak doodskist',
    'ga hek',
    'ga omhoog',
    'ga omhoog',
    'ga noord',
    'ga west',
    'ga zuid',
    'ga zuid',
    'ga touw',
    'leg doodskist',
    'ga touw',
    'pak schat',
    'ga touw',
    'ga kist',
    'ga uit',
]


def test_full_playthrough_reaches_the_win():
    io = ScriptedIO([])
    eng = new_game(io, explore=True)
    eng.submit(" . ".join(WALKTHROUGH))       # the whole game as one chained command
    assert eng.won, f"expected a win; ended in room {eng.room}, dead={eng.dead}"
    assert eng.room == 11                      # delivered to the dorpsstraat
    assert eng.obj_loc[13] == CARRIED          # the schatkist (obj13) rode home carried
    assert not eng.running                     # the win ends the game
    assert eng.world.message_text(281) in io.text   # the TROS win ending prints


def test_walkthrough_is_188_commands():
    # Guard the documented length so edits stay intentional.
    assert len(WALKTHROUGH) == 188


def test_full_playthrough_faithful_also_wins():
    # The same winning path must complete on the true, uncorrected 1982 text.
    io = ScriptedIO([])
    eng = new_game(io, explore=True, corrections=False)
    eng.submit(" . ".join(WALKTHROUGH))
    assert eng.won, f"faithful mode: expected a win; room {eng.room}, dead={eng.dead}"
    assert eng.room == 11
    assert eng.obj_loc[13] == CARRIED
