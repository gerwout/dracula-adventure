"""Core game engine: state + command dispatch.

Fidelity status (see docs/exe-map.md):
* FAITHFUL from the disassembly + data: the 2-word parser and full verb table,
  the prefix match rule, movement via the exit table, and the generic EXE
  responses for take / drop / inventory / "not here".
* PROVISIONAL / best-effort: the room object-listing wording, and any verb whose
  effect is a special-event message. The message-number -> event mapping is
  computed inside the compiled BASIC threaded code and is not statically
  recoverable; it needs the live oracle (currently blocked on key injection) or
  hand reconstruction. Such verbs get a generic in-character response for now.
"""
from __future__ import annotations

import json
from pathlib import Path

from .data.loader import load_file
from .data.model import CARRIED
from .io import IO
from .messages import Messages
from .navigation import (
    blocked_message,
    build_named_entries,
    ga_special,
    resolve_named_place,
    resolve_verified,
    resolve_verified_token,
)
from .parser import Command, DIR_ERUIT, parse_line, translated_tables
from .rng import BasrunRNG
from .room_events import FLAG_DEFAULTS, run_room_events
from . import verb_events
from . import end_of_turn
from . import savegame

START_ROOM = 0         # the player's own house
SAVE_PATH = Path("dracula_save.json")
BUG_PATH = Path("DRACULA.BUG")          # the comment/bug logbook (BUG / COMMENTAAR)
# (The BUG logbook header text lives in the lexicon: eng.lex.bug_header.)
# The hidden tester-feedback logbook, reached by typing "/" (EXE 0x5664 uses a TESTER
# file with a TESTER.OLD roll-over backup); distinct from the player BUG/COMMENTAAR.
TESTER_PATH = Path("TESTER")
TESTER_OLD_PATH = Path("TESTER.OLD")

# Verb groups whose exact effect is a not-yet-mapped special-event message.
# Handlers that have been wired to verb_events (docs/verb-events.md) are no longer
# here — they route through the dispatch table below.
_UNMAPPED: set[str] = set()


class Engine:
    def __init__(self, world, io: IO, navigation: dict | None = None,
                 store: savegame.SaveStore | None = None, sandboxed: bool = False):
        self.world = world
        self.io = io
        self.store = store if store is not None else savegame.FileSaveStore(SAVE_PATH)
        self.sandboxed = sandboxed
        self.msg = Messages(world)
        # Externalised UI strings / answer letters / secret word (engine/data/lexicon.py),
        # read through here so a translation (engine/i18n.py) applies everywhere.
        self.lex = world.lexicon
        # Parser tables for this world's language: the Dutch defaults, with any verb/
        # direction token overrides from a translation applied (empty in default play,
        # so parsing is byte-identical). See engine/parser.py + engine/data/lexicon.py.
        self._verb_table, self._dir_table = translated_tables(
            self.lex.verbs, self.lex.dirs)
        # All mutable per-game state is initialised here — and re-initialised on
        # reincarnation (the EXE INT 3Eh fn 0x0d full restart); see _reset_state.
        self._reset_state()
        # Optional reconstructed named-place navigation (opt-in; see navigation.py).
        self.navigation = navigation

    def _reset_state(self) -> None:
        """(Re)set every mutable runtime field to the game's start values. Shared by
        __init__ and the reincarnation restart (EXE 0x3eff -> INT 3Eh fn 0x0d), which
        is a complete restart back to the start room, not a respawn-in-place."""
        self.room = START_ROOM
        self.obj_loc = {oid: o.location
                        for oid, o in self.world.objects.items() if o.is_real}
        self.flags: dict[str, bool] = {}
        # Integer DGROUP state flags read by the describe-time room events
        # (routine 0x2399), initialised to the game's start values.
        self.state: dict[str, int] = dict(FLAG_DEFAULTS)
        # RND source for the random events (parser-failure pool, bird, Dracula
        # spawn). The BASRUN 24-bit LCG seeded exactly as the game starts
        # (seed 5, no RANDOMIZE) — see engine/rng.py.
        self.rng = BasrunRNG()
        # Consecutive-unrecognised-input counter ([0xdf4]); drives the room-0 help
        # block. A recognised command clears it (mirrors the main-loop reset 0x308).
        self.fail_counter = 0
        self.running = True
        # End-of-turn outcomes (engine/end_of_turn.py, EXE 0x269e): Dracula/spider
        # death, and the treasure-to-house win. The main loop ends the game on either.
        self.dead = False
        self.won = False
        # Set by the reincarnation restart to tell the frontend to re-show the opening
        # title screen (press-a-key) before resuming — a faithful full restart.
        self.restart = False

    # ------------------------------------------------------------------ state
    def carried(self) -> list[int]:
        return [o for o, loc in self.obj_loc.items() if loc == CARRIED]

    def objects_here(self) -> list[int]:
        return [o for o, loc in self.obj_loc.items() if loc == self.room]

    def visible(self) -> list[int]:
        return self.objects_here() + self.carried()

    def obj(self, oid: int):
        return self.world.objects[oid]

    def resolve(self, noun: str | None) -> int | None:
        """Match a typed noun to a visible object by 4-char token prefix.

        Uses the same rule as the parser: token T matches word W when
        W[:len(T)] == T (tokens are stored 3-4 chars).
        """
        if not noun:
            return None
        w = noun.upper()
        for oid in self.visible():
            for tok in self.obj(oid).tokens:
                t = tok.upper()
                if t and w[:len(t)] == t:
                    return oid
        return None

    # ----------------------------------------------------------------- output
    def describe_room(self) -> None:
        room = self.world.rooms[self.room]
        self.io.writeln(room.description)
        # Describe-time room-entry events (EXE routine 0x2399) fire between the
        # static room text and the object listing — e.g. room 0's gat/ladder line.
        run_room_events(self.room, self.state, self.world, self.io, self.rng)
        # Object listing (VERIFIED from DRACULA.EXE 0x4f5e vs the live game): EACH
        # object present is printed on its OWN line, "Er is een <name> hier.", with
        # the article chosen per-object by a leading marker in the name (see
        # GameObject.article): '@' -> "Er zijn <name> hier." (plural), '~' -> the
        # name as a bare sentence. There is no comma-joined "Er zijn a, b" form.
        for oid in self.objects_here():
            o = self.obj(oid)
            if not o.name:
                continue
            if o.article == "plural":
                self.io.writeln(self.lex.ui("OBJ_HERE_PLURAL").format(name=o.display_name))
            elif o.article == "bare":
                self.io.writeln(o.display_name)
            else:
                self.io.writeln(self.lex.ui("OBJ_HERE_SINGULAR").format(name=o.display_name))

    def _not_here(self, noun: str | None) -> None:
        self.io.writeln(f"{self.lex.ui('NO_SEE_A')}{(noun or '').lower()}{self.lex.ui('NO_SEE_B')}")

    def _parser_failure(self) -> None:
        """The 'nothing matched' response — faithful port of DRACULA.EXE 0x0dba
        (see docs/parser-failure.md). A random pick from world.messages[6..9], with
        a room-31 special and a room-0 help block that escalates after 4 consecutive
        failures. EXE record R prints world.messages[R-1] (the message off-by-one)."""
        if self.room == 31:
            self.io.writeln(self.world.message_text(267))    # room-31 flavour line
            return
        self.fail_counter += 1
        if self.room == 0 and self.fail_counter > 3:
            self.io.writeln(self.world.message_text(230))    # "give two-word commands" help
            self.fail_counter = 0
            return
        # RND-selected short reply: r1<=0.1 -> record 7; else INT(RND*3)+8 -> {8,9,10}.
        if self.rng.random() <= 0.1:
            record = 7
        else:
            record = int(self.rng.rnd(1.0) * 3.0) + 8
        self.io.writeln(self.world.message_text(record - 1))

    # --------------------------------------------------------------- dispatch
    def dispatch(self, cmd: Command) -> None:
        # Make this world's language active for the hardcoded Dutch noun checks
        # (verb_events.noun_is / navigation): empty in Dutch play, a translation's
        # alias map otherwise (chest -> KIST). Set per command so the right language
        # is active even when several engines/languages coexist in one process.
        verb_events.set_noun_canon(self.lex.noun_canon)
        # 3+ word input: the game echoes the two words it assumed (EXE 0x523) before
        # handling the (now two-word) command.
        if cmd.assumed:
            self.io.writeln(f"{self.lex.ui('ASSUME_A')}{cmd.assumed}{self.lex.ui('ASSUME_B')}")
        # Room-31 secret-word password (EXE dispatcher 0x084a -> handler 0x4f17):
        # in room 31, speaking the secret word runs the door event, even though the
        # word is not a recognised verb. Checked before the normal verb routing.
        if self.room == 31 and verb_events.is_secret(cmd, self.lex.secret):
            self.fail_counter = 0
            verb_events.room31_password(self, cmd)
            return
        if cmd.verb is None:
            self._parser_failure()
            return
        # A recognised command resets the consecutive-failure counter (0x308).
        self.fail_counter = 0
        handler = {
            "ga": self.do_ga,
            "kijk": self.do_kijk,
            "inventaris": self.do_inventaris,
            "pak": self.do_pak,
            "blaas": self.do_blaas,
            "leg": self.do_leg,
            "duw": self.do_duw,
            "spring": self.do_spring,
            "hang": self.do_hang,
            "knoop": self.do_hang,
            "bevestig": self.do_hang,
            "geef": self.do_geef,
            "vraag": self.do_vraag,
            "draag": self.do_draag,
            "pas": self.do_pas,
            "open": self.do_open,
            "sluit": self.do_sluit,
            "til": self.do_til_trek,
            "trek": self.do_til_trek,
            "hak": self.do_hak,
            "snij": self.do_snij,
            "graaf": self.do_graaf,
            "vul": self.do_vul,
            "eet": self.do_eten,
            "drink": self.do_eten,
            "schijn": self.do_schijn,
            "gooi": self.do_gooi,
            "toon": self.do_toon,
            "sla": self.do_sla,
            "dood": self.do_dood,
            "bekijk": self.do_bekijk,
            "lees": self.do_lees,
            "help": self.do_help,
            "bewaar": self.do_bewaar,
            "laad": self.do_laad,
            "bug": self.do_bug,
            "commentaar": self.do_bug,
            "tester": self.do_tester,
            "sta": self.do_sta,
            "stop": self.do_stop,
            "breek": self.do_breek,
            "zeg": self.do_zeg,
            "wacht": self.do_wacht,
            "sesam": self.do_sesam,
            "gil": self.do_gil,
            "vloek": self.do_vloek,
            "slaap": self.do_slaap,
            "luister": self.do_luister,
            "koop": self.do_koop,
        }.get(cmd.verb)
        if handler:
            handler(cmd)
        elif cmd.verb in _UNMAPPED:
            self.do_unmapped(cmd)
        else:
            self.io.writeln(self.msg.named("cant"))

    # ------------------------------------------------------------- core verbs
    def do_ga(self, cmd: Command) -> None:
        # Entry precondition — EXE ga-handler @0xe3e/0xe41: `mov ax,[0xe2e]; cmp
        # ax,[0xdde]; je 0xe4a` -> `[0xe34]=229` (world.messages[228]) + return. When
        # the player stands in Dracula's room ([0xdde]), EVERY movement verb is blocked
        # before direction resolution — this traps the player in the room-24 endgame
        # confrontation (its only exit is OMHOOG->29) and implements the mid-game
        # "Dracula blokkeert alle uitgangen" flee-block when he spawns in your room.
        if self.room == self.state.get("dde", 255):
            self.io.writeln(self.world.message_text(228))
            return
        if cmd.direction is None:
            # "GA <place>" with no direction word. First the movement specials that
            # emit a per-noun failure message or toggle bidirectionally (room-0
            # ceiling climb, balcony rope descent) — these can't be a plain
            # VERIFIED_NAMED row. Then the VERIFIED conditional named transitions
            # (faithful from the disassembly, so always active — independent of
            # explore mode).
            if cmd.noun is not None:
                if ga_special(self, cmd.noun):
                    return
                dest = resolve_verified(self.room, cmd.noun, self.state)
                if dest is not None:
                    self.room = dest
                    self.describe_room()
                    return
                # A named transition exists but its door/gate guard is shut: print the
                # specific closed-door line (EXE A1) rather than the generic cant_go.
                blk = blocked_message(self.room, cmd.noun, self.state)
                if blk is not None:
                    self.io.writeln(self.world.message_text(blk))
                    return
            # Otherwise fall back to the heuristic reconstructed named-place
            # navigation, but only in opt-in explore mode.
            if self.navigation is not None:
                dest = resolve_named_place(self.navigation, self.room, cmd.noun)
                if dest is not None:
                    self.room = dest
                    self.describe_room()
                    return
            self.io.writeln(self.msg.named("cant_go"))
            return
        # Coffin-interior exit (EXE room-38 exit 0x1004): GA UIT / GA E from inside the
        # doodskist (room 38) drops you where the OPENED doodskist now sits ([0xca6]=
        # obj38 loc) — room 11 after the slide, or the room you climbed in from. This
        # MUST run before exit_to because room-38 exits[6]=99 is a sentinel (99 !=
        # NO_EXIT, so exit_to would "succeed" and move you to a non-room).
        if self.room == 38 and cmd.direction == DIR_ERUIT:
            self.room = self.obj_loc.get(verb_events.DOODSKIST_OPEN)
            self.describe_room()
            return
        dest = self.world.rooms[self.room].exit_to(cmd.direction)
        if dest is None:
            self.io.writeln(self.msg.named("cant_go"))
        else:
            self.room = dest
            self.describe_room()

    def do_sta(self, cmd: Command) -> None:
        # "GA STAAN" / "STA OP": the parser routes STA* here, so honour the
        # verified conditional transition (e.g. standing up in room 13 -> 12).
        dest = resolve_verified_token(self.room, "STAA", self.state)
        if dest is not None:
            self.room = dest
            self.describe_room()
            return
        self.io.writeln(self.msg.named("cant"))

    def do_kijk(self, cmd: Command) -> None:
        # EXE dispatch 0x6e8: bare KIJK (no noun) redescribes the room (0x716); KIJK
        # <noun> falls into the shared examine handler (0x71d -> BEKIJK 0x32e6), so it
        # examines exactly like BEKIJK. SS-905/6010: kijk lantaren -> 121, kijk door -> 122.
        if cmd.noun:
            verb_events.bekijk(self, cmd)
        else:
            self.describe_room()

    def do_inventaris(self, cmd: Command) -> None:
        held = [self.obj(o).display_name for o in self.carried() if self.obj(o).name]
        if not held:
            self.io.writeln(self.lex.ui("INV_EMPTY"))
            return
        self.io.writeln(self.lex.ui("INV_HEADER"))
        for name in held:
            self.io.writeln(name)

    def do_pak(self, cmd: Command) -> None:
        verb_events.pak(self, cmd)

    def do_blaas(self, cmd: Command) -> None:
        verb_events.blaas(self, cmd)

    def do_leg(self, cmd: Command) -> None:
        verb_events.leg(self, cmd)

    def do_duw(self, cmd: Command) -> None:
        verb_events.duw(self, cmd)

    def do_spring(self, cmd: Command) -> None:
        verb_events.spring(self, cmd)

    def do_hang(self, cmd: Command) -> None:
        verb_events.hang(self, cmd)

    def do_geef(self, cmd: Command) -> None:
        verb_events.geef(self, cmd)

    def do_vraag(self, cmd: Command) -> None:
        verb_events.vraag(self, cmd)

    def do_draag(self, cmd: Command) -> None:
        verb_events.draag(self, cmd)

    def do_pas(self, cmd: Command) -> None:
        verb_events.pas(self, cmd)

    def do_open(self, cmd: Command) -> None:
        verb_events.open_(self, cmd)

    def do_sluit(self, cmd: Command) -> None:
        verb_events.sluit(self, cmd)

    def do_til_trek(self, cmd: Command) -> None:
        verb_events.til_trek(self, cmd)

    def do_bekijk(self, cmd: Command) -> None:
        verb_events.bekijk(self, cmd)

    def do_lees(self, cmd: Command) -> None:
        verb_events.lees(self, cmd)

    def do_hak(self, cmd: Command) -> None:
        verb_events.hak(self, cmd)

    def do_snij(self, cmd: Command) -> None:
        verb_events.snij(self, cmd)

    def do_graaf(self, cmd: Command) -> None:
        verb_events.graaf(self, cmd)

    def do_vul(self, cmd: Command) -> None:
        verb_events.vul(self, cmd)

    def do_eten(self, cmd: Command) -> None:
        verb_events.eten(self, cmd)

    def do_schijn(self, cmd: Command) -> None:
        verb_events.schijn(self, cmd)

    def do_gooi(self, cmd: Command) -> None:
        verb_events.gooi(self, cmd)

    def do_toon(self, cmd: Command) -> None:
        verb_events.toon(self, cmd)

    def do_sla(self, cmd: Command) -> None:
        verb_events.sla(self, cmd)

    def do_dood(self, cmd: Command) -> None:
        verb_events.dood(self, cmd)

    def do_slaap(self, cmd: Command) -> None:
        verb_events.slaap(self, cmd)

    def do_luister(self, cmd: Command) -> None:
        verb_events.luister(self, cmd)

    def do_koop(self, cmd: Command) -> None:
        verb_events.koop(self, cmd)

    def do_help(self, cmd: Command) -> None:
        # HELP/HULP -> a context quip (EXE 0x3010), NOT the "Spelregels" block (that is
        # LEES BRIEFJE only). Selected by room band + the castle-door flag [0xdee]:
        #   (21..38) & dee==0 -> msg 87; room<21 & dee==0 -> msg 88; else msg 89.
        dee = self.state.get("dee", 1)
        if 21 <= self.room <= 38 and dee == 0:
            self.io.writeln(self.world.message_text(87))
        elif self.room < 21 and dee == 0:
            self.io.writeln(self.world.message_text(88))
        else:
            self.io.writeln(self.world.message_text(89))

    def do_breek(self, cmd: Command) -> None:
        self.io.writeln(self.world.message_text(4))     # EXE 0x9e2

    def do_zeg(self, cmd: Command) -> None:
        self.io.writeln(self.world.message_text(5))     # EXE 0xc83

    def do_wacht(self, cmd: Command) -> None:
        self.io.writeln(self.world.message_text(215))   # EXE 0x4ca0

    def do_sesam(self, cmd: Command) -> None:
        # SESAM/HOKUS/HOCUS -> the "outdated magic word" line. In room 31 the genuine
        # secret word is intercepted earlier (dispatch, is_secret); "sesam" itself is
        # never the password, so it always lands here. EXE 0xd22.
        self.io.writeln(self.world.message_text(210))

    def do_gil(self, cmd: Command) -> None:
        # GIL/ROEP/SCHRE/BRUL — scream. Bare -> msg 153 "AAAA...RGGG" (EXE 0x3d3c); with
        # a word the EXE echoes it framed by dots (0x3d45).
        if cmd.noun:
            self.io.writeln(self.lex.ui("SCREAM_ECHO").format(noun=cmd.noun))
        else:
            self.io.writeln(self.world.message_text(153))

    def do_unmapped(self, cmd: Command) -> None:
        # Recognised verb whose special-event message isn't reconstructed yet.
        self.io.writeln(self.msg.named("cant"))

    def do_vloek(self, cmd: Command) -> None:
        """Profanity ({GODVE,SHIT,KUT,KLOOT,KANKE,GOD,FUCK,GEDVE}) -> a random rebuke.
        Faithful port of EXE 0x3d6c: [0xe34] = INT(RND*5)+155, so it prints one of
        world.messages[154..158] (the message off-by-one gives index [0xe34]-1)."""
        record = int(self.rng.random() * 5.0) + 155
        self.io.writeln(self.world.message_text(record - 1))

    def do_bug(self, cmd: Command) -> None:
        """BUG / COMMENTAAR (EXE 0x3fd6): append a comment/bug report to DRACULA.BUG.
        Asks for the player's name, then reads report lines until a line with just
        '.', and appends '  Speler: <name>' + the lines to the logbook."""
        if self.sandboxed:
            self.io.writeln(self.lex.ui("WEB_DISABLED"))
            return
        self.io.writeln(self.world.message_text(183))    # "Bugje ... tiep eerst je naam in..."
        name = (self.io.read_command() or "").strip()
        self.io.writeln(self.world.message_text(184))     # "Typ nu ... '.' om te stoppen"
        lines: list[str] = []
        while len(lines) < 500:                           # safety cap
            line = self.io.read_command()
            # '.' ends the report; None / "stop" is end-of-input (EOF, or a scripted
            # IO that has run dry) and must not spin forever.
            if line is None or line == "stop" or line.strip() == ".":
                break
            lines.append(line)
        if not BUG_PATH.exists():
            BUG_PATH.write_text(self.lex.bug_header, encoding="utf-8")
        with BUG_PATH.open("a", encoding="utf-8") as f:
            f.write(f"{self.lex.ui('BUG_PLAYER_PREFIX')}{name}\n")
            for line in lines:
                f.write(line + "\n")
            f.write("*" * 79 + "\n")

    def do_tester(self, cmd: Command) -> None:
        """The hidden tester-feedback logbook (EXE 0x5664), reached by typing '/'.
        Prints the tester greeting, then reads comment lines (each after a
        'commentaar --> ' prompt) until a line with just '.', and appends them to the
        TESTER logbook. No name is asked (unlike BUG/COMMENTAAR).

        NB the ORIGINAL crashes here: its file routine renames a non-existent TESTER to
        TESTER.OLD (and opens it for input) with no error handler, so on any normal
        install the missing-file error is fatal. The net *intent* is a rolling logbook
        that accumulates every comment; this port implements that (a plain append) so it
        actually works — a faithful reproduction would mean crashing, which we don't want."""
        if self.sandboxed:
            self.io.writeln(self.lex.ui("WEB_DISABLED"))
            return
        self.io.writeln(self.lex.ui("TESTER_HELLO"))    # "Hallo beste tester."
        self.io.writeln(self.lex.ui("TESTER_INSTR"))    # "Typ nu jouw opmerking in ..."
        lines: list[str] = []
        while len(lines) < 500:
            self.io.write(self.lex.ui("TESTER_PROMPT"))  # "commentaar --> " (no newline)
            line = self.io.read_command()
            if line is None or line == "stop" or line.strip() == ".":
                break
            lines.append(line)
        with TESTER_PATH.open("a", encoding="utf-8") as f:   # accumulate (EXE net effect)
            for line in lines:
                f.write(line + "\n")

    # -------------------------------------------------------------- save/load
    # BEWAAR SPEL / LAAD SPEL serialize the full runtime state (room + object
    # locations + the DGROUP flags) to SAVE_PATH; see engine/savegame.py and
    # docs/savegame.md. Messages are the original's DRACULA.SAV lines.
    def do_bewaar(self, cmd: Command) -> None:
        self.store.save(savegame.serialize(self))
        self.io.writeln(self.world.message_text(185))   # "Ik zet nu alle gegevens in DRACULA.SAV....."

    def do_laad(self, cmd: Command) -> None:
        data = self.store.load()
        if data is None:
            self.io.writeln(self.world.message_text(188))   # the "Vtoc error" load-fail easter egg
            return
        savegame.restore(self, data)
        self.io.writeln(self.world.message_text(186))   # "Ik haal nu alle gegevens uit DRACULA.SAV......"
        self.describe_room()

    def do_stop(self, cmd: Command) -> None:
        # STOP/QUIT/EIND/OP/HOU -> the save-or-not quit prompt (EXE 0x496c). msg 187
        # asks whether to save before stopping; 'J' saves (0x40e7) then ends, anything
        # else ends without saving. Both answers end the game (0x49a9). ScriptedIO
        # returns "stop" when exhausted, so a trailing "stop" ends without saving.
        self.io.writeln(self.world.message_text(187))
        ans = self.io.read_key()               # a single J/N keypress, no Enter needed
        # The 'yes' letter comes from the lexicon (Dutch 'J'; a translation makes it 'Y'
        # etc.). ScriptedIO returns "stop" when exhausted -> ends without saving.
        yes = self.lex.answer("yes").upper()
        if ans and ans != "stop" and yes and ans.strip().upper().startswith(yes):
            self.io.writeln(self.world.message_text(185))   # "Ik zet nu alle gegevens in DRACULA.SAV....."
            self.store.save(savegame.serialize(self))
        self.running = False

    # -------------------------------------------------------------- main loop
    def intro(self) -> None:
        # The startup title screen (EXE 0x52df): title banner, copyright and the
        # press-a-key line — plus the single rewrite-attribution block (the one intended
        # difference). The lines live in engine/data/strings_nl.json (lexicon.intro) so
        # the whole screen is translatable; nothing here is hardcoded.
        for line in self.lex.intro:
            self.io.writeln(line)

    def start(self) -> None:
        # The version/serienummer header at the top of the play screen (EXE 0x52a5/0x52c3;
        # screenshot SS-6010's top line), then the first room description.
        self.io.writeln(self.lex.header)
        self.io.writeln()
        self.describe_room()

    def _game_over(self) -> None:
        """Shared game-over hub — faithful port of EXE 0x3ed3, reached by every death
        path (Block A/B, spider, poison, the fatal jump, the waard knife). After the
        death-specific line each handler already printed, the hub prints
        world.messages[166] (the 'Welkom in het dodenrijk' + 'reincarneer? (toets J of
        N)' prompt) and reads the answer.

        Faithful to EXE 0x3ed3-0x3f1c: only the 'no' letter is tested (const 0x13cc =
        "N"); the 'no' answer — or exhausted scripted input — ends the game, while
        ANYTHING else prints world.messages[167] (the POEFF line) and fully restarts to
        the start room with default state (0x3eff -> INT 3Eh fn 0x0d). The 'no' letter
        comes from the lexicon, so a translation (English 'N', or any letter) applies
        without touching this code."""
        if 166 in self.world.messages:
            self.io.writeln(self.world.message_text(166))
        ans = self.io.read_key()               # a single J/N keypress, no Enter needed
        no = self.lex.answer("no").upper()
        if not ans or ans == "stop" or (no and ans.strip().upper().startswith(no)):
            self.running = False               # 'no' (or no input) -> the game ends
            return
        # Reincarnate: the POEFF line, then a COMPLETE restart. The EXE's INT 3Eh fn
        # 0x0d re-enters init (~0x226) and re-shows the title screen (0x52df), so we
        # reset all state and raise `restart` — the frontend re-shows the opening
        # press-a-key screen and calls start() again, rather than dropping straight
        # into the room. (No describe here; start() does it after the title screen.)
        if 167 in self.world.messages:
            self.io.writeln(self.world.message_text(167))
        self._reset_state()
        self.restart = True

    def submit(self, line: str) -> None:
        for cmd in parse_line(line, self._verb_table, self._dir_table):
            self.dispatch(cmd)
            # End-of-turn events fire after every command (EXE main loop 0x030e),
            # unless the command already ended the game (STOP) or was itself lethal:
            # a verb-death (spring, poison, the waard knife) jmps straight to the
            # 0x3ed3 game-over hub, bypassing the 0x269e end-of-turn routine.
            if self.running and not self.dead and not self.won:
                end_of_turn.run_end_of_turn(self)
            if self.dead:
                self._game_over()          # 0x3ed3: dodenrijk hub, then stop/restart
            elif self.won:
                self.running = False
            # Stop this turn on game-over OR on a reincarnation restart (the frontend
            # then re-shows the opening screen).
            if not self.running or self.restart:
                break

    def play(self) -> None:
        # Outer loop: each pass shows the opening title screen and plays until the game
        # ends; a reincarnation (`restart`) loops back to re-show the title screen.
        while True:
            self.restart = False
            self.intro()
            self.io.pause()          # "Druk een toets om te beginnen"
            self.io.clear()          # clear the title screen before the game
            self.start()
            while self.running and not self.restart:
                self.io.write("\n-> ")
                line = self.io.read_command()
                if line is None:
                    return
                self.submit(line)
            if not self.restart:
                break


def new_game(io: IO, txt_path=None, explore: bool = False,
             corrections: bool = True, lang: str = "nl",
             store: savegame.SaveStore | None = None, sandboxed: bool = False) -> Engine:
    """Create a game. explore=True enables reconstructed named-place navigation
    (BETREED HUIS / GA HERBERG ...) so more of the map is reachable — this is a
    heuristic reconstruction, not oracle-verified (see engine/navigation.py).
    corrections=True (default) shows the modernised text; corrections=False shows the
    true 1982 original text (see engine/data/corrections_nl.json).
    lang selects a bundled language ('nl' = the Dutch original, 'en' = English, ...);
    the whole game — text, input words and scenery nouns — switches together.
    store selects where BEWAAR/LAAD SPEL read and write (default: the save file);
    sandboxed is reserved for a later task."""
    from .i18n import builtin_translator
    world = load_file(txt_path, corrections=corrections, translator=builtin_translator(lang))
    nav = build_named_entries(world) if explore else None
    eng = Engine(world, io, navigation=nav, store=store, sandboxed=sandboxed)
    # Remember the language this game runs in. Not per-game mutable state (a
    # reincarnation restart keeps the same language), so it lives here rather than in
    # _reset_state — frontends/tests read engine.lang to know which language is active.
    eng.lang = lang
    return eng
