"""Build the bundled English translation of Dracula Avontuur.

This script holds the authored English for every translatable string and writes the
tool-format CSV ``engine/data/i18n/dracula_en.csv`` (which the game loads for the "en"
language and which the translation tool can import/edit). Re-run it after changing a
translation or after the set of rows changes:

    python tools/build_translation_en.py

It fails loudly if any row is left untranslated, if any Dutch full word no longer
derives its parser token, or if two translated input words collide on their derived
token in a way that would shadow a real command.

Translation notes (deliberate, tone-preserving choices):
  * msg 91  — the vampire handbook is Middle-Dutch; rendered in archaic Early-Modern
              English ("Vampyres have beene, sithence the memorie of manne...").
  * msg 6 / 188 — the folksy "kompjoetertje" computer-slang is kept ("compewter").
  * msg 281 — the Dutch broadcaster gag TROS (Transylvania Radio Omroep Stichting) is
              carried over as CNN (Coffin News Network): a real broadcaster with a
              vampire re-expansion.
  * msg 5  — the "say" tongue-loop is kept as an English say-loop.
  * msg 87 — dialect ("Grab what ye can grab").
  * msg 94 — a language-neutral letter-grid cipher, kept verbatim.
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "engine" / "data" / "i18n" / "dracula_en.csv"

# Rows kept byte-identical to the Dutch source (language-neutral ciphers / art).
VERBATIM = {"msg:94"}

EN: dict[str, str] = {
    # ---- messages ------------------------------------------------------------
    "msg:0": "Don't be so daft..",
    "msg:1": "That won't work.",
    "msg:2": "Were you going to try that with your bare hands ??\nI suggest you find some tools.",
    "msg:3": "That won't work, you'll have to pick it up first.",
    "msg:4": "I wouldn't do that if I were you.",
    "msg:5": "Well now, I say that if you say that I should say that,\nthen I say that you want to say that I\nmust say to say.",
    "msg:6": "I don't believe I quite understand you.\n( I'm only a little compewter you know, and my memory\nhasn't been so great lately either )",
    "msg:7": "I don't believe I quite understand you.",
    "msg:8": "I can't make any sense of that at all.",
    "msg:9": "Eh, what do you mean ?",
    "msg:10": "You can't go there.",
    "msg:11": "You can't reach that. The hole is too high up.",
    "msg:12": "The tree is too smooth to climb and you can't reach the first\nbranches. Slowly you slide back down...",
    "msg:13": "The heavy outer door is shut and there is no way\nleft to get it open.",
    "msg:14": "Which ladder ?",
    "msg:15": "You can't reach it, and the wall offers no\nhandhold.",
    "msg:16": "The stone through which you came in slams\nshut and can no longer be made out.",
    "msg:17": "The stone has slid back into place.",
    "msg:18": "I don't think you can go there.",
    "msg:19": "There is nothing dusty here.",
    "msg:20": "From under the dust a book appears.",
    "msg:21": "That is absolutely impossible to lift.",
    "msg:22": "That's getting too heavy, you'll have to drop\nsomething first.",
    "msg:23": "You aren't carrying that at all.",
    "msg:24": "The bottle shatters on the ground.",
    "msg:25": "The ladder reaches up to the hole and stands firmly\nenough to climb.",
    "msg:26": "When you throw the coin into the well the water\nof the well turns a strange blue colour. The\nwater now bubbles far more fiercely than before. A black shadow\ndarts across the bottom, but the water slowly grows\na little clearer again.",
    "msg:27": "The ladder just reaches the hole.",
    "msg:28": "I don't see any trees at all.",
    "msg:29": "The axe has become too blunt.",
    "msg:30": "You chop off a large piece of wood.",
    "msg:31": "You only dig up a few bones, but they crumble to dust\nthe moment you touch them.",
    "msg:32": "The ground is too hard to dig.",
    "msg:33": "Give a direction in which you want to dig.",
    "msg:34": "Which ladder do you mean ?",
    "msg:35": "Glug..glug..glug..burpp...",
    "msg:36": "The blue-coloured water is highly poisonous. After a few\nseconds your breath catches, then you writhe on the ground with\ncramp. You die after a few minutes..",
    "msg:37": "It has a strange aftertaste.",
    "msg:38": "Mmmm, delicious. I was rather hungry from all this\ntalking.",
    "msg:39": "There is a hole in the ceiling, but you can't reach it.\nThe hole is big enough to climb through.",
    "msg:40": "By way of a ladder you could climb up.",
    "msg:41": "The heavy door of the castle is open.",
    "msg:42": "The heavy door to the outside is open.",
    "msg:43": "The heavy, cobweb-covered door is shut.",
    "msg:44": "The heavy door to the outside is shut.",
    "msg:45": "In the distance you hear a bird whistling.",
    "msg:46": "Far off in the forest you can see a well.",
    "msg:47": "You see the narrow attic stairs behind a cupboard.",
    "msg:48": "Suddenly the door moves and slams shut with a bang.",
    "msg:49": "Dracula stands before you and blocks every exit.\nHe stares at you terrifyingly. When he smiles you\nsee a pair of sharp fangs that make his intentions\nquite clear.",
    "msg:50": "The gate is open, you can go down the stairs.",
    "msg:51": "The iron gate is shut.",
    "msg:52": "In front of the stairs is an iron gate",
    "msg:53": "The iron gate is shut.",
    "msg:54": "while the door through which you can get out is open.",
    "msg:55": "while on a closed door at the back a text can be\nread.",
    "msg:56": "Nobody answers.",
    "msg:57": "He says 'Are you deaf or something' and goes on with his\nwork.",
    "msg:58": "He hisses 'Clear off, before I really lose my temper'.\nYou see him grab something.",
    "msg:59": "He says ' There's an attic staircase behind that cupboard there,'\nand if you look closely you can see the stairs too.",
    "msg:60": "You don't see it, but perhaps you're not looking properly. The innkeeper\nmight well know more, too, don't you think?",
    "msg:61": "The innkeeper says 'Nothing doing, little man'\nand comes at you.",
    "msg:62": "Iaaaaaaahhhh...",
    "msg:63": "hop.....hop....hop..",
    "msg:64": "He glares at you angrily.",
    "msg:65": "The stone won't turn any further.",
    "msg:66": "One of the stones in the wall turns away and you\nsee a coffin behind the stone. You can crawl through the\nhole that has now appeared.",
    "msg:67": "Nothing at all happens.",
    "msg:68": "The window is already open.",
    "msg:69": "I don't see a 'hatch'.",
    "msg:70": "The hatch is already open.",
    "msg:71": "The hatch creaks and with great effort you get it\nopen far enough to just squeeze through.",
    "msg:72": "The gate is already open.",
    "msg:73": "The gate seems to be stuck fast.",
    "msg:74": "The gate opens at the slightest push.",
    "msg:75": "The chest is open!",
    "msg:76": "You see a wooden hatch at the bottom.",
    "msg:77": "I don't see a hatch.",
    "msg:78": "The hatch opens.",
    "msg:79": "The hatch is stuck fast.",
    "msg:80": "The box is already open.",
    "msg:81": "A hammer falls out.",
    "msg:82": "I don't quite see how I'd open that.",
    "msg:83": "I don't think that's necessary.",
    "msg:84": "You aren't even carrying it.",
    "msg:85": "To what ?",
    "msg:86": "The rope is firmly tied to the balcony.",
    "msg:87": "Grab what ye can grab.",
    "msg:88": "Aren't you sleepy after these thrilling adventures?",
    "msg:89": "Don't panic..don't panic..",
    "msg:90": "You do have to be carrying that, then.",
    "msg:91": "      -------  V A M P Y R E   H A N D B O O K E -------\n\nVampyres have beene, sithence the memorie of manne and tymes of olde,\nthe parasytes of mankinde. They have neede everie daye\nof freshe bloode, and have thus alreadie manie folke\nslayne and done to deathe. In the course of tymes\ncerteyne propertyes of the vampyre are becomme knowne. Thus\nis the vampyre sore afeard of the almightie crosse, the whiche is best\nfashioned of woode. They can scarce abyde nor endure\nthe light of daye. Garlicke doth likewyse seeme to\naffright a vampyre. Once did a certeyne seeker,\nwhereof in later tymes never no more was\nherde, essaye to smyte the vampyre in his daye-slumber with a\nwoodden pinne through the herte. The folke doe saye this myghte\nslaye the vampyre wholie and entyrelie. Later were in this wyse\nthe moste of vampyres slayne, but the strongeste kindred of the\nvampyres, dracula, hath beene able to survyv...\n\n   -- the text groweth further illegible --",
    "msg:92": "I don't see any text.",
    "msg:93": "There's really not much to read here.",
    "msg:95": "How did you mean to fill that ?",
    "msg:96": "With what ?",
    "msg:97": "There's already milk in it.",
    "msg:98": "The bottle is still full of water.",
    "msg:99": "You aren't carrying a bottle.",
    "msg:100": "The bottle slowly fills..",
    "msg:101": "I don't see a branch here.",
    "msg:102": "There's nothing to be done with the branch.",
    "msg:103": "I don't see any wood.",
    "msg:104": "After some carving the piece of wood takes the shape\nof a cross.",
    "msg:105": "You need a piece of wood for that.",
    "msg:106": "A few shavings flutter off.",
    "msg:107": "That's pointless.",
    "msg:108": "The wedge is very sharp....",
    "msg:109": "It is an old, heavy, thick, battered book with a leather\ncover. Some pages have been torn out and others are entirely\nfaded.",
    "msg:110": "With the machete you can cut and work wood.",
    "msg:111": "You would fit inside it exactly.",
    "msg:112": "The rope is strong enough to hoist an elephant with.",
    "msg:113": "The chest is full of very old coins, valuable in their day.",
    "msg:114": "Which bed did you have in mind ?",
    "msg:115": "The bed is heavy and not so easily lifted or\nmoved. For the rest there is, at first\nglance, nothing special about it...",
    "msg:116": "Under the bed a small wooden hatch can be seen. An\niron ring is nailed to the hatch so you\nshould be able to open it easily.",
    "msg:117": "The hatch can be opened simply by pulling on\nthe iron ring that is riveted to the hatch.",
    "msg:118": "The hatch is very sturdy and probably\ncan't be broken.",
    "msg:119": "You can see what is happening in the castle tower, you see\na wooden chest standing. Light comes in through a small\nwindow. A moment later you see a man in a black cloak\ncoming up the stairs. He glances dangerously in your direction.\nThen he laughs and opens the chest. A moment later he steps\ninto the chest and the lid falls shut.",
    "msg:120": "From here you can see what is happening in the dining room. There is\na large table. There is a small hunched little fellow walking about the\ndining room with a candlestick. When he leaves the room it goes\npitch dark there and you see nothing more...",
    "msg:121": "As far as I can tell there's nothing special about it.",
    "msg:122": "I see nothing special about it.",
    "msg:123": "It's hard to fall asleep here because the\nground is very hard.",
    "msg:124": "You wake early in the morning, fit again.",
    "msg:125": "You wake in the middle of the night from a rumbling\nthat seems to come from under the bed. When you step out\nof the bed the thumping vanishes as if by magic.",
    "msg:126": "You lose your way completely...",
    "msg:127": "Which hatch do you mean ?",
    "msg:128": "I don't see any garlic.",
    "msg:129": "The innkeeper says ' What's that doing there ? ' He comes\nat you and knocks the garlic out of your hands. He picks\nit up and puts it back where it lay. The people in the\ninn look at you with annoyance.",
    "msg:130": "Then the innkeeper rolls up a sleeve and hits you square in\nyour face. Blood streams from your nose. The mood\nturns very tense.",
    "msg:131": "I don't see any garlic.",
    "msg:132": "You can just pick it up, you know..",
    "msg:133": "The innkeeper growls and seems to grow a little calmer. Several\npeople turn their backs to you again.",
    "msg:134": "The innkeeper says 'You can have the garlic, you know,\nwe've got plenty of it.' He hands the string to you.",
    "msg:135": "... absolute silence ...",
    "msg:136": "Two men sit talking :\n\n '..... Well, yesterday was another good haul, eh ??\n\n 'You can say that again, two at once. And there's nothing we\n  can do about it.. oh, eh, good day stranger..'\n\n Of course you have no idea what it's about and say nothing back.\n The two carry on with their conversation:\n\n 'You know, something must have happened up in the attic of this\n  inn as well '\n\n 'Yes, I heard about that, the innkeeper isn't keen to talk about it. He\n  hasn't really spoken the same since...'",
    "msg:137": "The two men are still talking:\n\n '... Hey! Isn't that the one who was sitting here listening\n  last time too ?'\n\n 'I think so.' He turns toward you and says:\n\n 'Are you looking for trouble ??",
    "msg:138": "Everyone sitting at the table gets up and\nwalks to another table. You are now sitting alone at the table.",
    "msg:139": "Which rope ?",
    "msg:140": "The innkeeper grows very angry and hits you straight on the jaw, and\nyou reel back. Then you charge at him and kick him just as\nhe's about to throw a knife. The knife whizzes past your ears\nand grazes your shoulder. The innkeeper, who had doubled over, slowly\nstraightens up again, takes back his knife and waits..",
    "msg:141": "The innkeeper is knocked back against a table when you hit him in the stomach. He\ncomes right back, however, grabs you by the collar and throws\nyou into the air. When you come down you strike your jaw on the\ncounter. Half unconscious you see the innkeeper coming at you.",
    "msg:142": "The innkeeper grabs a knife and drives it with enormous force into your\nhand. You fall down and as you try, groaning with pain, to get\nup the innkeeper kicks you to the ground, pulls the knife out of your\nhand and slits your throat. You try to say something, but\nafter a few seconds you pass out.",
    "msg:143": "The innkeeper walks off for a moment and comes back with a heavy wooden\nbeam. One of the men in the inn stands up and grabs hold of you.\nThe innkeeper swings and as he tries to hit you in the face you duck\ndown. The beam strikes the fellow holding you with a dull\nblow to the neck. Bleeding, he runs out of the inn while the innkeeper\nswings again. The beam lands with great force on your knee\nas you try to dodge the blow. You quickly get up and\ngive the innkeeper such a blow to the face that he\nslowly staggers backward. He recovers quickly, however..",
    "msg:144": "The innkeeper runs off and seems afraid. He grabs a\nmeat knife, however, and now comes at you menacingly. You manage to kick the\nknife out of his hand, but he shoves you away and you\nland with your back against the hard wall and he grabs the knife again.",
    "msg:145": "That one isn't here.",
    "msg:146": "This text WAS the PROVISIONAL ending of the adventure..",
    "msg:147": "Dracula slowly comes closer.",
    "msg:148": "Dracula looks at you and begins to laugh. As he\ncomes closer you hear him mutter something about breakfast\nor some such.",
    "msg:149": "Dracula now attacks and sweeps his cloak menacingly through the\nair. His sharp fangs are now visible; you back away\ncarefully. Then he attacks and tries to bite your neck.\nSuddenly he stiffens and falls to the ground. His body first turns\ngrey and black smoke surrounds him. When the smoke clears nothing\nof his body remains.\nFar off, however, you hear a sinister laugh.",
    "msg:150": "Dracula dodges every attack with ease.\nA strange look in his eyes makes you freeze and\ndracula begins to snicker.",
    "msg:151": "As Dracula comes at you, you try to run away.\nHe seems to keep changing places, however, and each\ntime stands before you again. Then he bites and you fall down... A strange feeling\ncomes over you, memories grow fainter...you..you know nothing more\nand no longer have any control over yourself. Another spirit seems to have\ntaken control of your body. Vaguely you're aware of\nyour present habits, such as sleeping in a strange, wooden chest. Somewhere\nyou have the feeling you'll never see the sun again. In fact you no longer\neven know whether you're alive.......",
    "msg:152": "Dracula attacks you at once and bites your neck. You fall\ndown and can no longer move. You just catch him kneeling.\nSlowly you bleed dry while dracula laughs (and drinks). I even believe\nDracula had no wish to make a successor of you; presumably\nyou were merely his lunch.",
    "msg:153": "AAAAAAAAAAAARGGGHHHH",
    "msg:154": "What appalling language in this establishment..",
    "msg:155": "why don't you go and catch the bat-plague.",
    "msg:156": "Appalling!",
    "msg:157": "Had a Christian upbringing, no doubt ?   That's what I thought.",
    "msg:158": "I refuse to listen to any more insults of this\nkind.",
    "msg:159": "There is no lid on the chest.",
    "msg:160": "What kind of chest ?",
    "msg:161": "The castle door cannot be moved by any means.",
    "msg:162": "There is no lock on the door and the wind blows the door open again.",
    "msg:163": "The door slams shut into the lock.",
    "msg:164": "The door falls shut, but slowly swings open again.",
    "msg:165": "It won't budge at all.",
    "msg:166": "\n      +++ Welcome to the realm of the dead +++\n\nDo you want me to reincarnate you ? (press Y or N)",
    "msg:167": "Ok, but don't blame me if something goes wro..\n\n         --- P O O F F ---\n\nYou are surrounded by orange smoke and as it clears\nyou are.......",
    "msg:168": "The hatch is stuck fast.",
    "msg:169": "What kind of hatch ?",
    "msg:170": "Dracula dodges every attack with ease. A strange\nlook in his eyes makes you freeze while Dracula\nbegins to snicker.",
    "msg:171": "Dracula sizes you up calmly and doesn't stir a muscle.\nYour attacks seem to have no effect.",
    "msg:172": "'I do like a spicy little snack' Dracula snickers and\ncomes toward you. Strangely enough your attacks have\nno effect.",
    "msg:173": "Dracula hisses and recoils. He is clearly\nrepelled by the smell of the garlic. He recovers,\nhowever, fairly quickly.",
    "msg:174": "He can hardly bear the light and falls down. With his hands\nover his eyes he tries to get up again.",
    "msg:175": "You aren't carrying the lamp!",
    "msg:176": "You see a deserted castle tower, dimly lit\nby a small window. A heavy wooden chest stands to one\nside.",
    "msg:179": "That's very generous, but you do have to mention\nwhat you want to give.",
    "msg:180": "It is not accepted.",
    "msg:181": "You aren't carrying the coin.",
    "msg:182": "The innkeeper takes the coin and says:\n\n  ' Thanks, but the coin isn't worth anything at all '",
    "msg:183": "Little bug\n\nSo you want to comment on how things are going.\nThat's fine. type in your name first...",
    "msg:184": "Now type in what's on your mind. Give an empty\nline with only '.' on it to stop.",
    "msg:185": "I'm now putting all the data into DRACULA.SAV.....",
    "msg:186": "I'm now fetching all the data from DRACULA.SAV......",
    "msg:187": "Do you want to stop playing now ?\nShall I quickly save the game for you, so that you\ncan carry on later where you left off? (press Y or N)",
    "msg:188": "A voice says ' Vtoc error on @Acct 31/5.8: Can't access file '\nI'll just translate that for you, because those compewters these days\nspeak the strangest tongues. He's trying to say that you can't go back\nto an old spot that you saved with the 'save' command.\nMaybe you should put a different disk in, or did you not save anything\nat all? Then it gets rather difficult for me.",
    "msg:189": "It seems the innkeeper is growing a little calmer.",
    "msg:190": "The axe whizzes past the innkeeper's head and he goes berserk.\nHe grabs the axe and hurls it back with unbelievable force.\nYou dodge, however, and the axe hits someone behind you. That person runs\nscreaming out of the inn and quickly vanishes.",
    "msg:191": "The innkeeper quickly dodges the knife and picks it up. He examines it\ncalmly, hands it back and says 'I wouldn't do that\nagain..'",
    "msg:192": "The axe misses the innkeeper by a metre. He grabs it and\nthrows it back. The axe strikes a wooden pillar. With great effort you pull\nthe axe out of the wood again.",
    "msg:193": "The axe off the ground.",
    "msg:194": "The axe hits someone and clangs against the wall. The man who\nwas hit runs screaming out of the inn.",
    "msg:195": "The knife lands quivering in a wooden beam.",
    "msg:196": "The knife lands on the ground.",
    "msg:197": "The innkeeper is lightly hit and the knife now lies on the ground.",
    "msg:198": "Dracula dodges the weapon with ease and it falls\nto the ground. Dracula doesn't move a muscle..",
    "msg:199": "I would of course also like to know what you'd want to take.",
    "msg:200": "Am I supposed to decide what you want to throw away ?",
    "msg:201": "        ******* Rules of DRACULA ADVENTURE *******\n\nMany have already tried to find the treasure of Lord Dracula, few have\nreturned. So you want to try it too...then you need to know the following:\n\nType commands after the -> and use two words. If for example you want\nto go west, type GO WEST and press the RETURN key. If\nyou want to see where you are, type for example LOOK. I know a number\nof english words with which you must make sentences of at most two words.\nThe aim of the game is to find the great treasures. It will become clear whether\nyou're at the end of the adventure or not. If you want to walk somewhere\nyou can, where it is indicated, walk in the compass directions,\nso GO NORTH,SOUTH,EAST,WEST,UP,DOWN or OUT.\nThen, if the direction is not clear, you can also go toward a\ncertain object. If for example there is a house, you can try\nENTER HOUSE or GO HOUSE. Other commands are:\nINVENTORY, to see what you're carrying, EXAMINE or INSPECT, to look at something\nclosely, SAVE GAME, to store the current state and\nLOAD GAME to fetch it back again. You can also abbreviate various commands.\nThus I is the same as INVENTORY, L the same as LOOK and\nfor example W the same as GO WEST. You can give several commands on one\nline if you separate them with a period, so e.g. GO NORTH.TAKE CHRISTMASTREE.\n\n                      * * * * good luck * * * *",
    "msg:202": "Which paper ?",
    "msg:203": "The little window is too small to climb through.",
    "msg:204": "Take a leached solid oak bed ?? I don't think\nyou could even lift it!",
    "msg:205": "Mhhhhhnnnnggggg...No, it won't work.",
    "msg:206": "There is no lid on the chest.",
    "msg:207": "Pure craftsmanship. The joinery is carved in beautiful\nmotifs depicting fruit, various household\nobjects and, on the front, an inscription in a strange language.",
    "msg:208": "Nothing special really, considering that there was\nprobably a stove standing here once.",
    "msg:209": "It reads \"set pen eos tiam nnmai tsoen eptes\".",
    "msg:210": "Nice try, but that's an old and worn-out magic word.",
    "msg:211": "pffffff",
    "msg:212": "I reckon...B-positive\n(though of course you can never be quite sure)",
    "msg:213": "If you want to read something I know full well you're only\ninterested in the contents. In other words: don't bother!",
    "msg:214": "\n         I N C O R E  A U T O M A T I S E R I N G\n\n              Your supplier of quality software\n\n                 *\n         *              *\n                               *              *\n\n\n\n                                 *           *\n\n                   Surf to www.cosninix.com/dracula",
    "msg:215": ".. time passes ...",
    "msg:216": "       +--------------------------------+\n       !  D R A C U L A   C A S T L E   !\n       !                                !\n       ! Report to porter, please give  !\n       ! your blood type. Opening hours:!\n       !                                !\n       !  Monday-Saturday 0.00-6.00     !\n       !      Closed on Sundays         !\n       +--------------------------------+",
    "msg:217": "They are heavy bootprints, and here and there pawprints\nof various animals.",
    "msg:218": "Iaaaaaahhhhhhhhhhh.....\n\n        >>>>> B A F F <<<<<\n\nAlas, I think this jump asked a bit too much of you.\nYou die after a few moments.",
    "msg:219": "You see the forest, lit by a full moon just emerging\nfrom behind the clouds.",
    "msg:220": "It is pitch dark outside. With great effort you can make out the contours\nof the forest and some light that seems to come from the direction of the village.",
    "msg:221": "The moon just emerges from behind the clouds and lights the forest. Far\noff on the horizon you see sheet lightning.",
    "msg:222": "You hear a heavy, monotonous thumping. Now and then the sound seems to grow\nweaker, only to make the vault tremble with the noise again a moment later.",
    "msg:223": "A long ladder stands against the wall and reaches up to a hole struck\nhigh up in the wall.",
    "msg:224": "                 >>>> BAF <<<<\n\nYou hurt your ankle but luckily it's not too bad.",
    "msg:225": "The hall is deserted.",
    "msg:226": "You see a man in a black cloak coming down the stairs. Having reached\nthe bottom he waits and looks in your direction. Then he snaps\nhis fingers and is instantly gone. The hall is now deserted.",
    "msg:227": "It seems as if you're now in the woods, though the image is very blurry.\nLittle gnomes walk past in front of you and wave at you. The image grows blurrier\nand finally black. Then you see the hall of the castle and a man quickly\nrunning up the stairs.",
    "msg:228": "Lord Dracula plants himself right in front of you. You can't get past.",
    "msg:229": "It blows straight out of your hand again.",
    "msg:230": "I believe you don't quite understand what the idea is.\nYou must always give commands of 2 words, you could for example\ntype now:\n            CLOSE WINDOW ,to close the window\n            GO SOUTH     ,to go to that bedroom\n            CLIMB HOLE   ,to try to reach that hole above you\n            INVENTORY    ,to see what you're carrying\n            READ NOTE    ,to read that note lying on the ground.\n            LOOK         ,to see once more where you are and what you can do.",
    "msg:231": "The window is now closed.",
    "msg:232": "The window is now open.",
    "msg:233": "It's already shut.",
    "msg:234": "The window is already open.",
    "msg:235": "That won't work, the window is shut.",
    "msg:236": "The chest is too heavy to lift. It seems as if\nthere's something inside it.",
    "msg:237": "The chest is so awkward to lift and so heavy that you must first\ndrop everything if you want to be able to carry the chest.",
    "msg:238": "With great effort you pick up the chest.",
    "msg:239": "You lift the chest a few centimetres, but there's nothing beneath it.",
    "msg:240": "The chest is already closed.",
    "msg:241": "The chest won't close any more.",
    "msg:242": "You open the chest with great effort...  When you try to look\ninside, you see the lifeless body of Dracula. After a while\na digital church clock beeps ....",
    "msg:243": ".. the once lifeless body moves and opens its eyes. Dracula\n   then looks at you, makes a hissing sound, springs up\n   and shoves you back with force.",
    "msg:244": "The chest is already open.",
    "msg:245": "A lead-heavy chest with the text\n               ' D  R  A  C  U  L  A'\nchiselled in fine old gothic letters. On the chest lies a heavy, dusty lid. The chest is\ncovered in cobwebs and seems not to have been used or touched in ages.",
    "msg:246": "It is a heavy open chest with on the front the text\n                    ' D R A C U L A '\nin blood-red letters. Inside the chest lies nothing but some dust. In the\nbottom of the chest deep grooves are worn, as if the chest has slid down\nfrom somewhere.",
    "msg:247": "You've already got that in your hands.",
    "msg:248": "Are you crazy? That'll cost you your fingers.",
    "msg:249": "You see Dracula, who clearly walks with fear around a patch of light in the\nshape of a cross. He opens the door of bedroom 2\nand goes inside.",
    "msg:250": "You just catch sight of a shadow in the narrow northern corridor.",
    "msg:251": "When you reach the top, Lord Dracula stands waiting before the heavy door.\nThen he laughs and quickly walks on upward.",
    "msg:252": "Dracula walks up the stairs and glances back for a moment, as if\nhe wants to know whether you're following him.",
    "msg:253": "Dracula disappears up the stairs.",
    "msg:254": "Dracula comes closer and is about to attack you. He\nlooks as if he's very sure of himself.",
    "msg:255": "Dracula darts at you and lashes out.",
    "msg:256": "Dracula now attacks for good and with a simple gesture he strangles you.\nBefore you pass out you see him walk away. He doesn't even seem\nimpressed.",
    "msg:257": "The door is stuck fast in the lock.",
    "msg:258": "These attempts achieve nothing more. Dracula seems bored by\nthe lack of imagination.",
    "msg:259": "Nothing happens.",
    "msg:260": "'Aaaargghhhh'! The vampire recoils in fright.\nHe backs against a wall and holds his hands over his eyes.",
    "msg:261": "You don't have a hammer.",
    "msg:262": "Seems fairly useless to me. Looking at the wedge like this it's only\ngood for finishing off vampires.",
    "msg:263": "Driving stakes into vampires only works when they're in a fairly\ncalmed state. This one is rather in the opposite\nstate and is capable of finishing you off instead of the other way around.",
    "msg:264": "The vampire screams and falls down. For a moment the body lies motionless, then\nis suddenly surrounded by black smoke. A very rapid\nageing process begins and after a few seconds it seems as if\nan age-old corpse lies before you. Then it decays and only\ndust remains.",
    "msg:265": "The room suddenly falls completely silent...It stays quiet for\nquite some time until a loud cry from deep in the castle breaks\nthe silence. It seems as if the door now exhales heavily, but in any\ncase the old sound returns afterward. The door stays shut.",
    "msg:266": "A heavy blow and the door squeaks and grinds. Slowly the door swings open,\nclearing the way into a dark room.",
    "msg:267": "A hollow laugh sounds behind the door. Nothing else happens.",
    "msg:268": "The door is shut and even a hundred horses couldn't pull the door\nopen.",
    "msg:269": "The spider quickly comes at you and crawls over your leg. Since this kind of\nspider has the nasty habit of injecting its venom into its prey,\nthings aren't going too well for you at the moment and.. she now attacks.",
    "msg:270": "The spider comes at you.",
    "msg:271": "The poison streams out of the bottle and the spider, naturally parched\nfrom all those years waiting for a bit of prey, darts at the liquid.\nThe moment she touches the poison the spider dies.",
    "msg:272": "The spider deftly dodges every move.",
    "msg:273": "From here you see the cross room. The walls here are smeared\nwith blood and there are remains of animals lying about.\nIn the corner you see a skeleton. A great fire blocks the passage\nto an adjacent room. The heavy wooden door is open. It\nseems that from inside the armour you feel the heat of the fire less.\nThere also appears to be some movement in the armour now.",
    "msg:274": "From here you see the treasure chamber. The walls seem to give off light\nthrough a strange reflection of the fire. Light falls through a hole\nhigh up in this chamber. Because you're inside the armour you feel the heat\nof the fire a good deal less.",
    "msg:275": "Impossibility, a bug in Dracula or something, because if you're carrying\nthe armour you shouldn't be able to get in it.",
    "msg:276": "I don't see any armour here.",
    "msg:277": "With great effort you can move the armour. You feel an incredible\nheat as you walk through the fire, but the armour offers just enough\nprotection. You are now in another room.",
    "msg:278": "The fire seems fiercer now than ever but you get through it with a somewhat\nscorched behind. So you'll soon be sitting on your blisters, but first you\nstill have to see out the home stretch of this adventure. (The castle,\nyou see, is now beginning to tremble and personally I'm of the opinion that the\nfoundations of the castle can't take too much of that)",
    "msg:279": "The chest begins to slide and you shoot downward at great speed.\nThe chest follows the worn track and after a fifteen-minute death-ride\nyou come sliding into the village. Then the chest stops..",
    "msg:280": "The disintegration temperature of the average adventurer lies far\nbelow the value now reached. The effect is hardly hopeful.",
    "msg:281": "All the villagers and also the CNN (Coffin News Network) are\npresent to congratulate you. A few gentlemen from the tax\noffice are also present, wanting to know what's in the chest you're carrying.\nIt also turns out that vampires have just been classed among the protected\nspecies, so you'll shortly have to answer for yourself in court. A few\nmembers of the action group 'Stop the Vampire Slaughter' are present, treating\nyou aggressively. It turns out that they're all wearing a black coat\n..................",
    "msg:282": "The door is open far enough to get through.\n(You can walk through the door by typing GO DOOR)",
    "msg:283": "Branded into the door it reads \"THIS IS SESAME\".",

    # ---- verbs (full words; engine derives the 4-char token) -----------------
    "verb:GA": "go", "verb:BETRE": "enter", "verb:KRUIP": "crawl", "verb:LOOP": "walk",
    "verb:KLIM": "climb", "verb:VOLG": "follow",
    "verb:KIJK": "look", "verb:K": "l",
    "verb:BEKIJ": "examine", "verb:BESCHRIJF": "describe", "verb:ONDER": "inspect",
    "verb:PAK": "take", "verb:GRIJP": "grab", "verb:NEEM": "get", "verb:RAAP": "fetch",
    "verb:LEG": "drop", "verb:ZET": "put", "verb:DROP": "lay",
    "verb:GOOI": "throw", "verb:WERP": "hurl",
    "verb:SHOW": "show", "verb:TOON": "display", "verb:HOUDT": "hold", "verb:GEEF": "give",
    "verb:SCHIJ": "shine", "verb:BESCHIJN": "illuminate",
    "verb:SLAAP": "sleep",
    "verb:DOOD": "kill", "verb:VERMO": "murder", "verb:LIQUI": "liquidate", "verb:SLA": "hit",
    "verb:STOMP": "punch", "verb:SCHOP": "kick", "verb:TRAP": "stomp",
    "verb:HAK": "chop", "verb:KAP": "hew",
    "verb:VRAAG": "ask", "verb:PAS": "fit", "verb:DRAAG": "wear",
    "verb:FOUT": "fault", "verb:BUG": "bug", "verb:COMMA": "comment", "verb:KOMMA": "remark",
    "verb:BREEK": "break", "verb:SCHEU": "tear", "verb:VERNI": "destroy",
    "verb:GRAAF": "dig", "verb:SCHEP": "scoop",
    "verb:SPRIN": "jump", "verb:DRUK": "press", "verb:DUW": "push", "verb:BLAAS": "blow",
    "verb:GIL": "scream", "verb:ROEP": "shout", "verb:SCHRE": "yell", "verb:BRUL": "roar",
    "verb:GODVE": "goddammit", "verb:SHIT": "shit", "verb:KUT": "bollocks",
    "verb:KLOOT": "bastard", "verb:KANKE": "damn", "verb:GOD": "god",
    "verb:FUCK": "fuck", "verb:GEDVE": "blast",
    "verb:SLUIT": "close", "verb:TIL": "lift", "verb:TREK": "pull", "verb:OPEN": "open",
    "verb:SAVE": "save", "verb:BEWAA": "store", "verb:SPEL": "game",
    "verb:LOAD": "load", "verb:LAAD": "reload",
    "verb:QUIT": "quit", "verb:EIND": "end", "verb:STOP": "stop",
    "verb:HOU": "halt", "verb:OP": "abort",
    "verb:WACHT": "wait", "verb:RUST": "rest",
    "verb:BEVES": "attach", "verb:HANG": "hang", "verb:KNOOP": "tie", "verb:ZEG": "say",
    "verb:HELP": "help", "verb:HULP": "aid",
    "verb:LIJST": "items", "verb:INVEN": "inventory", "verb:I": "i",
    "verb:LEES": "read",
    "verb:SESAM": "sesame", "verb:HOKUS": "hocus", "verb:HOCUS": "pocus",
    "verb:VUL": "fill", "verb:EET": "eat", "verb:DRINK": "drink", "verb:SNIJ": "cut",
    "verb:KOOP": "buy", "verb:LUIST": "listen", "verb:STA": "stand",
    "verb:/": "/",

    # ---- directions (n/s/e/w/u/d/o remap; see help text) --------------------
    "dir:NOOR": "north", "dir:N": "n",
    "dir:ZUID": "south", "dir:Z": "s",
    "dir:OOST": "east", "dir:O": "e",
    "dir:WEST": "west", "dir:W": "w",
    "dir:OMHO": "up", "dir:HOOG": "up", "dir:H": "u",
    "dir:OMLA": "down", "dir:LAAG": "down", "dir:L": "d",
    "dir:ERUI": "out", "dir:UIT": "out", "dir:E": "o",

    # ---- object display names -----------------------------------------------
    "obj:0": "small burning lantern", "obj:1": "piece of thick rope",
    "obj:2": "wooden wedge", "obj:3": "string of garlic", "obj:4": "thick battered book",
    "obj:5": "heavy machete", "obj:6": "long ladder", "obj:7": "piece of wood",
    "obj:8": "carved branch", "obj:9": "wooden cross", "obj:10": "razor-sharp axe",
    "obj:11": "Superfluous object",
    "obj:12": "piece of thick rope, tied to the balcony",
    "obj:13": "treasure chest, full of gold coins", "obj:14": "slice of bread",
    "obj:15": "gold devil's coin", "obj:16": "bottle of milk (no deposit)",
    "obj:17": "empty bottle", "obj:18": "bottle of water", "obj:19": "golden necklace",
    "obj:20": "heavy oak bed", "obj:21": "heavy closed chest",
    "obj:22": "heavy opened chest with a closed hatch at the bottom",
    "obj:23": "heavy opened chest with an open hatch at the bottom",
    "obj:24": "heavy chest with a thick layer of dust on the bottom",
    "obj:25": "heavy chest with a book at the bottom", "obj:26": "heavy empty chest",
    "obj:27": "shards", "obj:28": "blunt axe", "obj:29": "shovel",
    "obj:30": "shallow well", "obj:31": "small wooden box", "obj:32": "wooden hammer",
    "obj:33": "bottle filled with blue, poisonous water",
    "obj:34": "dangerous cross-spider", "obj:35": "small note",
    "obj:36": "large iron suit of armour",
    "obj:37": "heavy coffin with the text 'D R A C U L A' in gothic letters",
    "obj:38": "heavy opened coffin with the text 'DRACULA' on the side",
    "obj:39": "The strangely shaped door is now open", "obj:40": "dead cross-spider",

    # ---- object input nouns (full words; engine derives the token) ----------
    "objnoun:0": "lantern, burning, lamp", "objnoun:1": "rope", "objnoun:2": "wedge",
    "objnoun:3": "garlic, string", "objnoun:4": "book", "objnoun:5": "machete, knife",
    "objnoun:6": "ladder", "objnoun:7": "wood", "objnoun:8": "branch", "objnoun:9": "cross",
    "objnoun:10": "axe", "objnoun:13": "treasure, chest", "objnoun:14": "bread, slice",
    "objnoun:15": "coin, devilcoin", "objnoun:16": "bottle, milk", "objnoun:17": "bottle",
    "objnoun:18": "bottle, water", "objnoun:19": "necklace", "objnoun:28": "axe",
    "objnoun:29": "shovel", "objnoun:31": "box", "objnoun:32": "hammer", "objnoun:33": "bottle",
    "objnoun:35": "note", "objnoun:36": "armour, iron, large", "objnoun:38": "chest, coffin",
    "objnoun:40": "spider",

    # ---- scenery / interaction nouns (canonical Dutch token -> English) -----
    "noun:ALLE": "all", "noun:DEUR": "door", "noun:LUIK": "hatch", "noun:RAAM": "window",
    "noun:HEK": "gate", "noun:GAT": "hole", "noun:STEE": "stone", "noun:BOOM": "tree",
    "noun:GRON": "ground", "noun:ZAND": "sand", "noun:STOF": "dust", "noun:BLOE": "blood",
    "noun:VLEK": "stain", "noun:VOET": "footprints", "noun:SPOR": "tracks",
    "noun:CIRK": "circle", "noun:VIZI": "visor", "noun:TEKS": "text",
    "noun:INSC": "inscription", "noun:VREE": "strange", "noun:TORE": "tower",
    "noun:EETK": "dining", "noun:ROOS": "grating", "noun:SESA": "sesame", "noun:BED": "bed",
    "noun:SLAP": "sleep", "noun:SLAA": "bedroom", "noun:ZITT": "sit", "noun:KAST": "castle",
    "noun:TRAP": "steps", "noun:ZOLD": "attic", "noun:BRON": "well", "noun:WAAR": "innkeeper",
    "noun:MAN": "man", "noun:HAL": "hall", "noun:VUUR": "fire", "noun:UIT": "off",
    "noun:PIN": "stake", "noun:DRAC": "dracula", "noun:DOOD": "coffin", "noun:KIST": "chest",
    "noun:SCHA": "treasure", "noun:LADD": "ladder", "noun:MUNT": "coin", "noun:FLES": "bottle",
    "noun:BOEK": "book", "noun:KNOF": "garlic", "noun:TOUW": "rope", "noun:HARN": "armour",
    "noun:DOOS": "box", "noun:TAK": "branch", "noun:HOUT": "wood", "noun:KRUI": "cross",
    "noun:BROO": "bread", "noun:WATE": "water", "noun:MELK": "milk", "noun:WIG": "wedge",
    "noun:KAPM": "machete", "noun:BIJL": "axe", "noun:SCHE": "shards", "noun:BRIE": "note",
    "noun:SPIN": "spider", "noun:KRUISS": "webspider",
    "noun:HERB": "inn", "noun:HUIS": "house", "noun:POOR": "archway", "noun:GANG": "passage",
    "noun:RUIM": "space", "noun:UITG": "exit", "noun:LINK": "left", "noun:PAD": "path",
    "noun:BINN": "courtyard", "noun:KERK": "graveyard", "noun:STAA": "stand",

    # ---- room static descriptions -------------------------------------------
    "room:0": "You are now in your own house. There is a bedroom to the south\nand a small hall to the east. There is a door leading to the west. The\ndoor is ajar and a bleak wind blows sand and dust inside.\nThrough a window you can see a forest.",
    "room:1": "You are now in the bedroom. The only exit is to the\nnorth, where a cluttered room can be seen. It's fairly dark\nhere, but through a small window just enough light comes in\nto see by.",
    "room:2": "You are now standing in a small hall with a low ceiling. There is a western\nexit, behind which a cluttered and dusty room can be seen. In a\ncorner stands a heavy chest. Right in the middle of the hall the\nwooden floor is scorched in the shape of a circle.",
    "room:3": "You are now in an attic. There is a hole in the floor,\nout of which the tip of a ladder sticks. You could go\ndown by way of this ladder.",
    "room:4": "You are now in a damp cellar. The ceiling\nis so low here that you can't stand upright.\nThere is a narrow hole in the ceiling through which\nyou could climb up. The walls seem to be of\ngranite, but to the north the wall is very\nsandy. You stand up to your ankles in muddy\nwater.",
    "room:5": "You are now crawling in a narrow sand tunnel. The tunnel\nruns to the south, where a faint glimmer of light\ncan be seen. The ground is very soft, so that you could\ndig a passage in any direction. The water\nhere stands about a decimetre deep. Digging\ndownward is therefore not possible.",
    "room:6": "You are now behind the house. There is a small window\nthrough which you can get into the house. A dark forest stretches\nout on all sides.",
    "room:7": "You are now in a dark forest. All around you\nyou see trees.",
    "room:8": "You are now in a dark forest. All around you\nyou see trees.",
    "room:9": "You are now in a dark forest. All around you\nyou see trees.",
    "room:10": "You are now in a dark forest. All around you\nyou see trees.",
    "room:11": "You are now in the main street of the village. Far\nto the north you can see the castle of Lord Dracula.\nBefore you is the inn, while to the left stands a small\nhouse. A large forest lies to the south of the\nvillage.",
    "room:12": "You are now in the inn 'the black hand'. People sit\nat a table talking, while the innkeeper stands behind the\ncounter. Through a door you can get out of the inn.",
    "room:13": "You are now sitting at a table in the inn. Various\npeople sit around you talking. One person stares ahead anxiously.",
    "room:14": "You are now in the dark attic of the inn. By way of\na staircase you can go down. There hangs a strong smell,\nas if a corpse has lain rotting here for some months.\nThe floor is covered in bloodstains. There is, however, no corpse\nto be seen. A strangely shaped stone is set into the\nwall.",
    "room:15": "You are now in an open part of the forest. You hear water\nsplashing to the east, where between the trees you can see a\nwell. The ground has a strange vibration.",
    "room:16": "You are now on top of a small hill\nin the middle of the forest. In the distance above the treetops\nyou can see a tower of a castle. Some tens of\nkilometres further you can see the houses of a small town.",
    "room:17": "You are now in a dark forest. High in a heavy\noak tree a small hut has been built. The branches of\nthe tree hang low enough to climb into it.\nMany footprints can be seen in the ground.",
    "room:18": "You are now in a small hut high up in a tree. One of the\nplanks that make up the floor has broken off,\nso that you can go down through it. From here you have a\nmagnificent view over the vast forest. In the distance you can\nsee the little village with the inn. A narrow path from the village\nwinds into the forest. Far to the left of the village you can see the castle\nof Lord Dracula. By some strange glow the castle looks\nghostly. A narrow path runs up the hill to the entrance\nof the castle. Otherwise the wall around the castle is so\nsteep that the path is in fact the only entrance.",
    "room:19": "You are now walking on a long path in the forest. The path runs\non up to the castle on the hill. The village\nlies below. If you don't follow the path you end up\nin the woods.",
    "room:20": "You are now standing before the entrance of the castle. A path winds\ndown the hill and then vanishes into the dense forest.\nAbove the entrance a text is scratched in large letters\ninto the coarse stones.",
    "room:21": "You are now in an immense hall of the castle. A broad staircase runs\nupward. Under the stairs is a small door to the north.\nIt's as if someone is present, yet you see no one.",
    "room:22": "You are now in a long corridor. With great effort you can make out a very\nnarrow passage to the south. Before you is a door with a\nsign 'BEDROOM 2' on it. The corridor runs east/west.",
    "room:23": "You are in a bedroom of the castle. The walls of this room\nare beautifully worked with green/brown paint in a kind of\noriental pattern. To the south is a door, behind which\na balcony can be seen.",
    "room:24": "You are now in a bedroom of the castle. The room is\ncompletely sealed except for one door. On the back of the door hangs\na sign reading 'BEDROOM 2'. There is a cold hearth\nwith a chimney here. It's very dusty and dry here,\nprobably because of the soot, which lies in thick layers\non everything here.",
    "room:25": "You are now on a wide balcony. Through a door you can\nget to a room to the north. If you look over the\nedge you can see, far below, a ledge that runs along\nthe castle. Beside the ledge is a chasm; the forest\nis far lower still. You have a magnificent view over the\nwoods and the surroundings. The village can't be seen from here.",
    "room:26": "You are now standing on a narrow ledge that runs along the castle.\nThe ledge, however, becomes so narrow on both sides that passage\nis not possible. The hill here slopes very steeply down into the forest.\nDescent here is probably not possible. There are deep tracks\nleading down the hill.",
    "room:27": "You are now in a large dining room. Here stands a very long empty\ntable. Food scraps lie about the floor. A door forms the\nonly exit from this room.",
    "room:28": "You are now standing on the slippery roof of one of the towers of the\ncastle. You have a view over the forest, in which you now, far in the\ndistance, see a kind of well, some way from the village.\nGoing down through the window brings you back into the tower.",
    "room:29": "You are now in a castle tower. There is a small window in the\nwall through which you can see the forest in the distance. A worn\nwooden staircase runs down.",
    "room:30": "You are now standing on a vertical stretch of a high spiral staircase.\nThe staircase runs both further up and down,\nwhile there is a narrow opening to the north. High up, beyond\nyour reach, a hole seems to have been struck in the wall.",
    "room:31": "You are now standing on a long spiral staircase that\ngoes up and down. Before you you see a strangely\nshaped door in the wall with 'THIS IS SESAME' burned into the\nwood of the door. A heavy thumping is audible behind the\ndoor.",
    "room:32": "You are standing in a small vault at the foot of a spiral staircase. A low\nstaircase runs down, past an iron gate. Behind\nthe gate you can see several coffins standing. It is,\nhowever, too dark to see the whole room below.\nBefore you is a small archway, behind which is a courtyard\nused as a graveyard. A spiral staircase leads up.",
    "room:33": "You are now in the spy room. The room is\nhewn out all around, with here and there some loose stones.\nTwo very narrow passages connect to this room. One\npassage runs to the east, the other to the west.\nA hole has been struck in the wall with a ladder\nleaning against the other side. By way of this ladder\nyou can go down.",
    "room:34": "You are now in the cross room. The walls here are smeared\nwith blood and there are remains of animals lying about.\nIn the corner lies the skeleton of a careless adventurer.\nA great fire blocks the passage to an adjacent\nroom. There is only 1 exit, the heavy wooden\ndoor.",
    "room:35": "You are now in the treasure chamber. The walls seem to give\nlight through a strange reflection of the glow of\nthe fire. High up in this chamber is a hole in the\nwall in the shape of a latin cross. Air comes\nin through it.",
    "room:36": "You are now in a courtyard of the castle that serves as a graveyard.\nThere are many graves here, some of which are open. The gravestones of others\nhave been slid aside. Most graves, however, are intact. The only exit\nis a small archway on the west side.",
    "room:37": "You are now in a burial tomb deep beneath the castle. A narrow\nstaircase goes up; halfway up the stairs an iron gate has been placed.\nAn icy draught goes through marrow and bone. There stand a number of wooden\ncoffins in this room, all alike.",
    "room:38": "You are now in a sealed wooden coffin. Bloodstreaks\nand a musty smell betray the fact that this coffin has been\nused before...",
    "room:39": "The shovel has struck something hard. As you dig further\nit turns out you've struck a wall. The stones of the wall are\ncold and damp. The dug-out passage runs back to the south.",
    "room:40": "You are now in a long corridor. Before you to the south\nyou see a door inscribed 'BEDROOM 1'. The corridor once\nran east/west but through a collapse the western\npassage is blocked.",
    "room:41": "You are now in a narrow niche with a small peephole in the wall. Through\nthe hole comes a little light, just enough to see a corridor to the north and a\nsomewhat lower passage to the west.",
    "room:42": "You are standing at the end of a narrow, high corridor. This corridor must run\nexactly behind the various rooms of the castle. Above you is\na hole. Hewn-out steps lead straight up to it.",
    "room:43": "You are now standing right before a hole in the ground. The corridor runs on\nfurther to the east but grows steadily narrower.",
    "room:44": "The corridor is impassable further on. Further along it is only ten\ncentimetres wide. There is, however, an airflow streaming eastward into the\nnarrow slit.",
    "room:51": "You are now standing near a very narrow niche, with a small hole in the wall,\ninto which a finger would fit exactly. Above the hole hangs a sign reading\n'TOWER ROOM'.",
    "room:52": "You are here in a kind of ventilation space. Through a hole closed off\nwith a grating you have a view over the dining room. A tall, spinning\nfan on the other side of the space provides a warm,\nunpleasant airflow here. A hole above you is the only exit\nhere.",
    "room:54": "You are now inside the armour. Through the visor you can see what is\nhappening.",

    # ---- externalised lexicon: UI strings -----------------------------------
    "ui:OK_TAKE": "Ok",
    "ui:TAKEN": " : taken.",
    "ui:DROPPED": " : dropped.",
    "ui:INV_HEADER": "You are carrying:",
    "ui:INV_EMPTY": "You aren't carrying anything.",
    "ui:NO_SEE_A": "I don't see a ",
    "ui:NO_SEE_B": " here.",
    "ui:OBJ_HERE_SINGULAR": "There is a {name} here.",
    "ui:OBJ_HERE_PLURAL": "There are {name} here.",
    "ui:SCREAM_ECHO": "..{noun}....",
    "ui:BUG_PLAYER_PREFIX": " Player: ",
    "ui:REVEAL_SECRET": "The dust swirls about and at a certain moment seems to\nform letters. Faintly you can read the text {word}.\nThen the dust disperses entirely and no trace remains of this\nonce so very impressive dracula.",
    "ui:ASSUME_A": "I assume you mean '",
    "ui:ASSUME_B": "'.",
    "ui:PRESS_KEY": "--- Press a key ---",
    "ui:LOAD_ERROR": "Load error.",
    "ui:OK": "Ok.",
    "ui:TESTER_HELLO": "Hello dear tester.",
    "ui:TESTER_INSTR": "Now type in your comment, when you're done type\na period and then return",
    "ui:TESTER_PROMPT": "comment --> ",
    "ui:GAME_OVER": "[ the game is over ]",
    "ui:MENU_CUT": "Cut",
    "ui:MENU_COPY": "Copy",
    "ui:MENU_PASTE": "Paste",
    "ui:MENU_SELECT_ALL": "Select all",
    "ui:MENU_SAVE_GAME": "Save game",
    "ui:MENU_LOAD_GAME": "Load game",
    "ui:MENU_NEW_GAME": "New game",
    "ui:MENU_QUIT": "Quit",
    "ui:MENU_GAME": "Game",
    "ui:MENU_HELP": "Help",
    "ui:MENU_LANGUAGE": "Language",
    "ui:LANGUAGE_NAME": "English",
    "ui:HELP_CLOSE": "Close",
    "ui:BUG_HEADER": "Dracula Bug list \nThis file is filled if, while playing, you find a bug\nand then type BUG. \n*******************************************************************************",
    "ui:HELP_WARNING_TITLE": "Show commands?",
    "ui:HELP_WARNING": "In the original game you had to discover all commands yourself. Are you sure you want to see them now?",
    "ui:HELP_TITLE": "Commands",
    "ui:HELP_INTRO": "Commands (with a simple example):",
    "ui:HELP_COMMANDS": "Movement\n  go <direction> - e.g. 'go north' (walk somewhere)\n    short: n, s, e, w, u (up), d (down), o (out)\n  stand up - e.g. 'stand up' (get to your feet)\n\nLooking and reading\n  look - e.g. 'look' (look at where you are; short: l)\n  examine <thing> - e.g. 'examine door' (look at something more closely)\n  read <thing> - e.g. 'read note' (read a text)\n\nObjects\n  take <object> - e.g. 'take lamp' (pick something up)\n  drop <object> - e.g. 'drop lamp' (put something down)\n  i - e.g. 'i' (show what you're carrying)\n  show <object> - e.g. 'show cross' (show something)\n  give <object> - e.g. 'give money' (give something away)\n  throw <object> - e.g. 'throw knife' (throw something away)\n  shine <thing> - e.g. 'shine lamp' (shine the lamp)\n\nUsing things\n  open <thing> - e.g. 'open door' (open something)\n  close <thing> - e.g. 'close door' (shut something)\n  push <thing> - e.g. 'push button' (push or press against something)\n  pull <thing> - e.g. 'pull lever' (pull on something)\n  lift <thing> - e.g. 'lift stone' (lift something)\n  dig - e.g. 'dig' (dig in the ground)\n  chop <thing> - e.g. 'chop tree' (chop or hew something)\n  cut <thing> - e.g. 'cut rope' (cut something through)\n  break <thing> - e.g. 'break window' (break something)\n  fill <thing> - e.g. 'fill jug' (fill something)\n  blow <thing> - e.g. 'blow horn' (blow on something)\n  jump - e.g. 'jump' (jump up or forward)\n\nTalking and other\n  say <word> - e.g. 'say sesame' (say a word out loud)\n  scream - e.g. 'scream' (scream or shout)\n  eat <thing> - e.g. 'eat bread' (eat something)\n  drink <thing> - e.g. 'drink water' (drink something)\n  buy <thing> - e.g. 'buy map' (buy something)\n  wait - e.g. 'wait' (wait a moment)\n\nFighting\n  hit <something> - e.g. 'hit wolf' (hit something)\n  kill <someone> - e.g. 'kill dracula' (try to kill someone)\n\nThe game\n  save game - e.g. 'save game' (save your game)\n  load game - e.g. 'load game' (load a saved game)\n  stop - e.g. 'stop' (stop playing)\n\nTip: give several commands in a row, separated by a period '.'\nfor example: go north . take lamp . i",

    # ---- answer letters, secret, title screen -------------------------------
    "answer:yes": "Y",
    "answer:no": "N",
    "secret:word": "incoronium",
    "intro:1": "                 D R A C U L A   A D V E N T U R E",
    "intro:3": "       (c) 1982 Incore Automatisering / R.van Woensel produkties",
    "intro:5": "   Modernised version by Gerwout van der Veen.",
    "intro:6": "   All original copyrights remain with the original",
    "intro:7": "   author and rightsholders.",
    "intro:9": "                    Press a key to begin",
    "intro:header": "Serial number:A000002-MSD on MS-DOS.",
}


def build() -> None:
    import sys
    sys.path.insert(0, str(REPO))
    from engine.data.loader import load_file
    from engine.data.object_nouns import noun_token
    from engine.parser import translated_tables, match_verb, direction_index
    from tools import translate_core as core

    world = load_file()
    rows = core.collect_rows(world, languages=("en",))

    # 1) coverage: every row must be translated (or explicitly verbatim).
    missing, extra = [], set(EN)
    for r in rows:
        rid = r["id"]
        extra.discard(rid)
        if rid in VERBATIM:
            r["en"] = r["dutch"]
        elif rid in EN:
            r["en"] = EN[rid]
        else:
            missing.append(rid)
    if missing:
        raise SystemExit(f"MISSING {len(missing)} translations: {missing[:40]}")
    if extra:
        raise SystemExit(f"EXTRA keys not matching any row: {sorted(extra)[:40]}")

    # 2) fidelity: Dutch full words still derive their parser tokens (verbs/dirs).
    from engine.parser import _VERB_WORDS_NL, _DIR_WORDS_NL, _NOUN_WORDS_NL
    for tok, w in {**_VERB_WORDS_NL, **_DIR_WORDS_NL, **_NOUN_WORDS_NL}.items():
        assert w[: len(tok)].upper() == tok, f"nl word {w!r} != token {tok}"

    # 3) build the English translator and verify the input words actually parse.
    from engine.i18n import Translator
    tr = Translator.from_rows(rows, "en")
    w_en = load_file(translator=tr)
    vt, dt = translated_tables(w_en.lexicon.verbs, w_en.lexicon.dirs)

    # 3a) every verb full word resolves to the right action (no shadowing collisions).
    for rid, en in EN.items():
        if rid.startswith("verb:") and en != "/":
            tok = rid.split(":", 1)[1]
            action = dict(__import__("engine.parser", fromlist=["_VERB_TABLE"])._VERB_TABLE)[tok]
            got = match_verb(en, vt)
            assert got == action, f"verb {en!r} -> {got!r}, expected {action!r} ({tok})"

    # 3b) every direction full word / shortcut resolves.
    for rid, en in EN.items():
        if rid.startswith("dir:"):
            assert direction_index(en, dt) is not None, f"dir {en!r} did not resolve"

    # 3c) scenery-noun aliases: no two canonical tokens collide on a derived token.
    canon: dict[str, str] = {}
    for rid, en in EN.items():
        if rid.startswith("noun:"):
            ctoken = rid.split(":", 1)[1]
            for word in [x.strip() for x in en.split(",") if x.strip()]:
                key = noun_token(word)
                if key in canon and canon[key] != ctoken:
                    raise SystemExit(f"noun collision {key}: {canon[key]} vs {ctoken}")
                canon[key] = ctoken

    OUT.parent.mkdir(parents=True, exist_ok=True)
    core.export_csv(rows, OUT)
    print(f"OK: wrote {len(rows)} rows to {OUT.relative_to(REPO)}")
    print(f"    verbs/dirs/nouns verified; scenery aliases: {len(canon)} tokens")


if __name__ == "__main__":
    build()
