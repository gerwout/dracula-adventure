# Translating Dracula Avontuur

The game's original text is **Dutch** (language code `nl`), decoded from
`DRACULA.TXT`. This tool lets you translate every game string into another
language and run the game in that language — without touching the Dutch original.

## What can be translated

`tools/translate_gui.py` gathers three kinds of string:

| type        | id form       | what it is                                            |
|-------------|---------------|-------------------------------------------------------|
| `message`   | `msg:<n>`     | a response / event message (`world.message_text(n)`)  |
| `verb`      | `verb:<TOK>` / `dir:<TOK>` | an input word the player types (verb or direction) |
| `room-text` | `room:<n>`    | a room's static description text                       |

Each row also shows:

* **room** — the room(s) where a message can appear (`14`, `7-11`, `2, 14, 29`,
  or `any`). This is a best-effort **static analysis** of the engine source
  (`tools/translate_core.analyze_message_rooms`): it finds each `pr(...)` /
  `message_text(...)` call and the nearest enclosing `room == N` / `room in (...)`
  / `LO <= room <= HI` guard. Room-specific lines (e.g. `msg 214` → room 14, the
  INCORE easter egg you read with `BEKIJK STEEN` in the herberg attic) get their
  room; global replies (parser failures, generic verb answers) show `any`.
* **room_name** — a short descriptive label for that room (`Zolder (herberg)`),
  from `tools/room_names.py`.
* **dutch** — the original source text (read-only). Newlines are shown as `⏎`
  in the table but exported/imported as real newlines.

## Workflow

1. **Export a template.**

   ```
   python tools/translate_gui.py
   ```

   Click **Export** and save `dracula_en.csv` (CSV is UTF-8-with-BOM so Excel
   opens it cleanly; if `openpyxl` is installed you may save `.xlsx` instead).
   The file has one column per language; new languages start empty. Use **+ Lang**
   to add e.g. `fr`, `de`.

2. **Translate.** Fill in the language column — either directly in the GUI
   (double-click a language cell; a popup editor opens so multi-line strings work)
   or in Excel/LibreOffice. Only translate the `dutch` text into the language
   column; leave `id`, `type`, `room`, `room_name`, `dutch` untouched. Leaving a
   cell empty keeps the Dutch original for that string.

3. **Import back** (optional). Click **Import** to reload an edited file, or
   **Save** to re-export to the last file.

4. **Run the game in that language.**

   ```python
   from engine.data.loader import load_file
   from engine.i18n import Translator

   world = load_file(translator=Translator.from_csv("dracula_en.csv", "en"))
   ```

   `load_file()` with no translator (or a default `Translator()`) is unchanged —
   the game stays byte-identical Dutch. A non-default translator swaps message
   texts and room descriptions in place, so the whole engine emits the translated
   strings.

## Notes / scope

* Round-trip is lossless: Export → Import yields identical rows.
* Verb/direction **input tokens** are included so a translator can see them, but
  the seam does not yet re-seed the parser to accept translated commands — the
  parser table (`engine/parser.py`) stays Dutch. Message/room text translation is
  the supported path; localized input words are a documented future step.
* The room attribution and room names are heuristics (documented in the source);
  they are aids for the translator, not gameplay data.
