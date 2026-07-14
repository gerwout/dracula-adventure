# Dracula Adventure

A faithful, *observable-identical* Python reimplementation of **Dracula Avontuur**, the
1982 Dutch text adventure — playable in your terminal or in a desktop GUI with a faithful
DOS look.

[![CI](https://img.shields.io/github/actions/workflow/status/gerwout/dracula-adventure/ci.yml?branch=main)](https://github.com/gerwout/dracula-adventure/actions)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Latest release](https://img.shields.io/github/v/release/gerwout/dracula-adventure)](../../releases/latest)

<!-- screenshot placeholder -->

## About

**Dracula Avontuur** is a Dutch text adventure written by **R. van Woensel**
(© 1982 Incore Automatisering, Rotterdam). It originally shipped for MS-DOS as a
compiled Microsoft QuickBASIC program — `DRACULA.EXE`, running on the `BASRUN.EXE`
runtime, with its rooms, objects and text stored in a `DRACULA.TXT` data file. The
original game is now **freeware**. You can read more about it in the catalogue entry at
[tekstadventure.nl](https://www.tekstadventure.nl/database/dracula.html).

This project is a from-scratch Python reimplementation that reproduces the original
game's behaviour, room layout, puzzles and text as closely as possible — down to its
quirks — while running natively on modern systems with no DOS emulator required. The
game itself runs entirely from its own modern data file, `engine/data/world.json` (a
re-encoding of the original content), so none of the original files are needed at
runtime. The original four files are also mirrored in this repository (see
[The original game](#the-original-game-freeware) below) for archival purposes and out of
respect for the original author.

Faithful to the 1982 original, the in-game parser's **commands stay in Dutch** — you play
with commands like `ga noord`, `pak lamp`, and `kijk`. An **English translation** of all
on-screen text is available with `--lang en`; Dutch (`nl`) remains the default and is the
source language the game was written in.

## Download & install

Grab the latest build for your platform from the
**[Releases page](../../releases/latest)**.

### Windows

Download `dracula-adventure-<version>-setup.exe` and run it. It's an Inno Setup
installer that installs both the CLI (`dracula.exe`) and the GUI (`dracula-gui.exe`),
adds Start Menu shortcuts, and registers an uninstaller.

The installer is **unsigned**, so Windows SmartScreen may warn you when you first run
it. Click **More info → Run anyway** to proceed.

### Linux

Two options are provided:

- **AppImage**: download it, `chmod +x dracula-adventure-*.AppImage`, then run it directly.
- **.deb**: `sudo apt install ./dracula-adventure_<version>_amd64.deb`

### macOS

Download the `.dmg`, open it, and drag **Dracula Adventure** into your `Applications`
folder.

The app is **unsigned**. On first launch, either right-click the app and choose **Open**,
or clear the quarantine flag from a terminal:

```sh
xattr -dr com.apple.quarantine "/Applications/Dracula Adventure.app"
```

## Play from source

Requires **Python 3.14**. The engine and CLI use only the standard library; the GUI
additionally needs `tkinter` (bundled with most Python installers).

```sh
git clone https://github.com/gerwout/dracula-adventure.git
cd dracula-adventure

python run_cli.py          # play in the terminal
python run_gui.py          # play in the desktop window
```

Useful flags (both frontends):

- `--lang en` — play with the English translation instead of the Dutch original text.
- `--faithful` — use the verbatim 1982 text, including its original spelling typos
  (by default a "Gemoderniseerde" build is used, which corrects a handful of them).

## Play in your browser / self-host

The game also runs as a web app: a small Python server drives the engine over a WebSocket
and serves a single self-contained page as the terminal (it mirrors the desktop GUI, saves
to your browser's `localStorage`, and works on mobile). Every visitor gets their own
isolated session.

**Run it locally** (needs Python 3.14):

```sh
pip install -r requirements-web.txt
python -m frontends.web.server
```

Then open **http://127.0.0.1:8765/** in your browser — that's it (the server serves both
the page and the WebSocket). Override the address with `DRACULA_WEB_HOST` /
`DRACULA_WEB_PORT`; e.g. run `DRACULA_WEB_HOST=0.0.0.0 python -m frontends.web.server` to
reach it from your phone on the same network at `http://<your-computer-ip>:8765/`.

**Production:** put it behind Nginx for TLS (see [`deploy/nginx.conf`](deploy/nginx.conf))
and run it as a service with [`deploy/dracula-web.service`](deploy/dracula-web.service).

Online, the filesystem-writing commands (BUG / COMMENTAAR / the `/` tester) are disabled.

## Translate the game (contributions welcome!)

The game ships in **Dutch** (the original) and **English**, but adding another language is
easy and needs **no code changes** — translations live as plain CSV files under
`engine/data/i18n/`, which the game **auto-discovers** at startup. A small helper tool
collects every translatable string (messages, room descriptions, object names, the title
screen — even the words you type) into one editable table.

1. **Fork and clone** the repo (Python 3.14).

2. **Launch the translation tool** (a small tkinter window):

   ```sh
   python tools/translate_gui.py
   ```

3. **Add your language:** click **+ Lang**, enter your language code (e.g. `fr`, `de`, `es`),
   then **Export** and save the file as `dracula_<code>.csv` (e.g. `dracula_fr.csv`).

4. **Translate.** Fill in your language's column — in the tool (double-click a cell) or in
   Excel / LibreOffice (it's a UTF-8 CSV). Only edit *your* column; leave `id`, `type`,
   `dutch` untouched. **Any cell you leave empty keeps the Dutch original**, so you can
   translate as much or as little as you like. Do translate the `ui:LANGUAGE_NAME` row into
   your language's own name — that's what shows up in the in-game language picker.

5. **Drop it in:** save the finished file as `engine/data/i18n/dracula_<code>.csv`. That's it
   — no code to touch. Use the bundled `engine/data/i18n/dracula_en.csv` as a reference.

6. **Try it:**

   ```sh
   python run_cli.py --lang fr      # or your code
   python run_gui.py                # your language now appears in the startup picker
   ```

7. **Verify and open a PR.** Run the tests — the suite plays a full winning walkthrough in
   *every* registered language, so it catches a broken translation:

   ```sh
   python -m pytest
   ```

   Then open a pull request adding your `engine/data/i18n/dracula_<code>.csv`. 🎉

Full details (what each string type means, the room/context hints the tool shows) are in
[`tools/TRANSLATING.md`](tools/TRANSLATING.md).

## The original game (freeware)

The [`original/`](original/) folder, and the `dracula-original-1982.zip` attached to
every [release](../../releases/latest), contain the original 1982 MS-DOS release
verbatim:

- `LEESMIJ` — the original Dutch readme
- `DRACULA.TXT` — the game's room/object/text database
- `DRACULA.EXE` — the compiled QuickBASIC game
- `BASRUN.EXE` — Microsoft's QuickBASIC runtime, included because the original game
  shipped with it and needs it to run

The original game is now freeware. All rights to it remain with its original author,
**R. van Woensel**, and **Incore Automatisering** (Rotterdam).

## How it was reverse-engineered

Reconstructing the original game required reverse-engineering a compiled Microsoft
QuickBASIC program from 1982 — a toolchain that produces a `BASRUN`-hosted bytecode
format, not native x86 machine code. Static analysis with **Ghidra** and **radare2**
disassembles the small amount of native glue code, but the game logic itself runs as
interpreted intermediate language dispatched through `INT 3Fh`, which defeats ordinary
decompilers. Recovering it meant decoding that IL — its opcode set, its calling
conventions, and how it addresses variables and strings — well enough to reconstruct the
control flow and logic of each in-game routine by hand.

The other half of the puzzle was data: `DRACULA.TXT` stores every room, object, verb
response and message as fixed 80-byte records in a custom binary layout. Decoding this
format made it possible to extract the entire game world — rooms, exits, objects,
vocabulary and text — programmatically rather than by transcription.

Throughout, the emerging Python implementation was checked against **the original
program running under DOSBox**, by driving both versions through the same input and
diffing their output turn by turn. This differential-testing loop is what let the
rewrite converge on byte- and behaviour-identical fidelity, rather than just a
plausible-looking approximation.

## Development

Run the test suite (~576 tests):

```sh
python -m pytest
```

`tools/build_world.py` regenerates `engine/data/world.json` from a local copy of the
original `DRACULA.TXT` — you only need this if you're changing how the world data is
decoded, not to play the game.

Project layout, in brief:

```
engine/         pure game engine (state, parser, navigation, messages) — no I/O or UI code
frontends/      the tkinter desktop GUI
run_cli.py      terminal entry point
run_gui.py      GUI entry point
tools/          world-data builder + translation tooling
tests/          pytest suite
original/       the mirrored 1982 MS-DOS release (see above)
```

## License

The rewrite's **code** is licensed under **GPL-3.0** — see [`LICENSE`](LICENSE).

The original 1982 game (`original/`, and its logic and text as reconstructed in
`engine/data/world.json`) is freeware; all rights to it belong to its original author,
R. van Woensel / Incore Automatisering.
