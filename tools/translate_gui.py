#!/usr/bin/env python3
"""Excel-like translation editor for Dracula Avontuur.

Run it::

    python tools/translate_gui.py

The tool's own interface is in English; the GAME text stays Dutch. Each language has a
short code (nl, en, de …) shown by its endonym (Nederlands, English, Deutsch …), and the
columns open PRE-FILLED from each language's bundled translation CSV
(engine/data/i18n/dracula_<code>.csv). It shows every translatable game string (messages,
verb / direction input words, object names and input nouns, scenery nouns, and per-room
static text) in a scrollable table with columns:

    ID | Type | Room | Room name | Nederlands (read-only) | <one column per language>

Double-click a language cell to edit its translation (a small popup editor opens, so
multi-line strings work). Selecting a row shows its FULL (multi-line) source text and
every translation in the detail pane below the table; drag the sash between the table
and the detail pane to resize it (it also has its own scrollbar). The Search box filters
to the rows
whose text in the chosen language contains a substring (e.g. search "Dracula" in
Nederlands). Buttons:

    Import      — load a previously exported CSV/.xlsx back into the table.
    Export      — write the whole table (incl. edits) to a CSV (utf-8-sig; .xlsx too
                  if openpyxl is installed).
    + Language  — add another target-language column (asks for a short code, e.g. 'de').

Newlines in the (read-only) source text are shown with a "⏎" marker in the single-line
table cells; the real newline value is preserved on export and shown in full in the
detail pane.

The data-gathering + import/export logic lives in :mod:`tools.translate_core`
(pure functions, unit-tested headlessly). This file only adds the tkinter UI, and
imports tkinter lazily so it can still be imported without a display.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make `engine` and `tools` importable when run as a standalone script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import translate_core as core          # noqa: E402
# Re-export the pure functions so `import tools.translate_gui` exposes them too.
from tools.translate_core import (                 # noqa: E402,F401
    ANY_LANGUAGE, SOURCE_LANGUAGE, analyze_message_rooms, collect_rows, columns_of,
    export_csv, export_xlsx, filter_rows, import_csv, import_xlsx, language_key,
    languages_of, rooms_to_str, xlsx_available,
)
from tools.room_names import room_name             # noqa: E402,F401

NEWLINE_MARK = " ⏎ "


def _display(value: str) -> str:
    """Render a raw cell value for the table (newlines -> visible marker)."""
    return value.replace("\n", NEWLINE_MARK)


def build_rows(languages=None) -> list[dict]:
    """Gather all translatable rows (see translate_core), with each language column
    PRE-FILLED from its bundled translation CSV so the tool opens showing the shipped
    translations rather than blank columns. Columns are keyed by language CODE ("en"),
    matching the CSVs the game loads; the GUI shows each language's endonym as its header.
    """
    from engine.data.loader import load_file
    from engine.i18n import AVAILABLE_LANGUAGES, SOURCE_LANG, _I18N_DIR
    if languages is None:
        languages = [c for c in AVAILABLE_LANGUAGES if c != SOURCE_LANG] or ["en"]
    world = load_file()
    rows = core.collect_rows(world, languages=languages, room_name_fn=room_name)
    by_id = {r["id"]: r for r in rows}
    for code in languages:
        path = _I18N_DIR / f"dracula_{code}.csv"
        if not path.exists():
            continue
        for tr in core.import_csv(path):
            rid, value = tr.get("id"), tr.get(code, "")
            if value and rid in by_id:
                by_id[rid][code] = value
    return rows


# --------------------------------------------------------------------------- #
#  GUI (tkinter imported lazily inside the class/main so headless import works)
# --------------------------------------------------------------------------- #
class TranslatorApp:
    def __init__(self, master, rows: list[dict]):
        import tkinter as tk
        from tkinter import ttk

        self.tk = tk
        self.ttk = ttk
        self.master = master
        self.rows = rows
        self.languages = core.languages_of(rows) or ["en"]
        self.last_path: str | None = None
        self._editor = None

        master.title("Dracula Avontuur — Translation Tool")
        master.geometry("1100x700")

        toolbar = ttk.Frame(master)
        toolbar.pack(side="top", fill="x", padx=6, pady=4)
        ttk.Button(toolbar, text="Import", command=self.on_import).pack(side="left")
        ttk.Button(toolbar, text="Export", command=self.on_export).pack(side="left", padx=4)
        ttk.Button(toolbar, text="+ Language", command=self.on_add_language).pack(side="left")
        self.status = ttk.Label(toolbar, text="Double-click a language cell to translate; "
                                              "select a row to see its full text.")
        self.status.pack(side="right")

        # Search bar: filter to the rows whose text in a chosen language contains a
        # substring (e.g. search "Dracula" in Nederlands).
        self.filter_text = ""
        search = ttk.Frame(master)
        search.pack(side="top", fill="x", padx=6, pady=(0, 4))
        ttk.Label(search, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        entry = ttk.Entry(search, textvariable=self.search_var, width=32)
        entry.pack(side="left", padx=4)
        # Live substring filter as you type (and on Enter).
        entry.bind("<KeyRelease>", lambda e: self.apply_filter())
        entry.bind("<Return>", lambda e: self.apply_filter())
        ttk.Label(search, text="in language:").pack(side="left", padx=(8, 2))
        # Default to searching every column so a substring is found regardless of which
        # language column holds it (e.g. "drac" -> the Dutch "Dracula" lines).
        self.search_lang = tk.StringVar(value=ANY_LANGUAGE)
        self.search_combo = ttk.Combobox(search, textvariable=self.search_lang,
                                         state="readonly", width=16,
                                         values=self._search_languages())
        self.search_combo.pack(side="left")
        self.search_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_filter())
        ttk.Button(search, text="Filter", command=self.apply_filter).pack(side="left", padx=4)
        ttk.Button(search, text="Show all", command=self.clear_filter).pack(side="left")

        # A vertical split with a DRAGGABLE SASH: the row table on top, the full text of
        # the selected row below. Drag the sash to resize the detail area (and it has its
        # own scrollbar for text taller than the pane).
        self.paned = ttk.PanedWindow(master, orient="vertical")
        self.paned.pack(side="top", fill="both", expand=True, padx=6, pady=4)

        container = ttk.Frame(self.paned)
        self.tree = ttk.Treeview(container, show="headings", selectmode="browse")
        vsb = ttk.Scrollbar(container, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        self.paned.add(container, weight=3)

        detail = ttk.LabelFrame(self.paned, text="Full text of the selected row")
        dsb = ttk.Scrollbar(detail, orient="vertical")
        dsb.pack(side="right", fill="y")
        self.detail = tk.Text(detail, height=8, wrap="word", state="disabled",
                              yscrollcommand=dsb.set)
        self.detail.pack(side="left", fill="both", expand=True, padx=4, pady=4)
        dsb.config(command=self.detail.yview)
        self.paned.add(detail, weight=1)

        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self._rebuild_columns()
        self._populate()

    # Human-readable headers for the fixed columns. Language columns are keyed by CODE
    # ("en") and shown by their endonym ("English") -- see _lang_label.
    HEADER_LABELS = {"id": "ID", "type": "Type", "room": "Room",
                     "room_name": "Room name", "object": "Object",
                     "dutch": SOURCE_LANGUAGE}

    def _lang_label(self, code: str) -> str:
        """The display name (endonym) for a language column key, e.g. 'en' -> 'English'."""
        from engine.i18n import AVAILABLE_LANGUAGES
        return AVAILABLE_LANGUAGES.get(code, code)

    # -- table plumbing ---------------------------------------------------- #
    def _columns(self) -> list[str]:
        return core.FIXED_COLUMNS + self.languages

    def _rebuild_columns(self):
        cols = self._columns()
        self.tree["columns"] = cols
        widths = {"id": 90, "type": 80, "room": 70, "room_name": 150,
                  "object": 150, "dutch": 360}
        for c in cols:
            label = self.HEADER_LABELS.get(c) or (self._lang_label(c) if c in self.languages else c)
            self.tree.heading(c, text=label)
            self.tree.column(c, width=widths.get(c, 160), anchor="w", stretch=False)

    def _populate(self):
        self.tree.delete(*self.tree.get_children())
        cols = self._columns()
        self._item_row: dict[str, dict] = {}
        rows = filter_rows(self.rows, getattr(self, "filter_text", ""),
                           self._search_key(self.search_lang.get())) \
            if getattr(self, "filter_text", "") else self.rows
        for row in rows:
            values = [_display(str(row.get(c, ""))) for c in cols]
            item = self.tree.insert("", "end", values=values)
            self._item_row[item] = row

    # -- search / filter --------------------------------------------------- #
    def _search_languages(self):
        return [ANY_LANGUAGE, SOURCE_LANGUAGE] + [self._lang_label(k) for k in self.languages]

    def _search_key(self, label: str) -> str:
        """Map a search-dropdown label back to the key filter_rows expects: the special
        ANY/source labels pass through; a language endonym maps to its column code."""
        if label in (ANY_LANGUAGE, SOURCE_LANGUAGE):
            return label
        for k in self.languages:
            if self._lang_label(k) == label:
                return k
        return label

    def apply_filter(self):
        self.filter_text = self.search_var.get().strip()
        self._populate()
        n = len(self.tree.get_children())
        if self.filter_text:
            self.status.config(text=f"{n} row(s) contain '{self.filter_text}' "
                                    f"in {self.search_lang.get()}.")
        else:
            self.status.config(text="Showing all rows.")

    def clear_filter(self):
        self.filter_text = ""
        self.search_var.set("")
        self._populate()
        self.status.config(text="Showing all rows.")

    def _refresh_item(self, item: str):
        row = self._item_row[item]
        cols = self._columns()
        self.tree.item(item, values=[_display(str(row.get(c, ""))) for c in cols])

    # -- editing ----------------------------------------------------------- #
    def on_double_click(self, event):
        tk = self.tk
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        item = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)   # like "#6"
        if not item or not col_id:
            return
        col_index = int(col_id[1:]) - 1
        cols = self._columns()
        if col_index < 0 or col_index >= len(cols):
            return
        col = cols[col_index]
        if col not in self.languages:
            self.status.config(text=f"Column '{col}' is not editable (language columns only).")
            return
        self._open_editor(item, col)

    def _open_editor(self, item: str, col: str):
        tk = self.tk
        ttk = self.ttk
        row = self._item_row[item]
        top = tk.Toplevel(self.master)
        top.title(f"{row.get('id', '')} — {self._lang_label(col)}")
        top.geometry("560x320")
        top.transient(self.master)

        ttk.Label(top, text="Nederlands (source):").pack(anchor="w", padx=8, pady=(8, 0))
        src = tk.Text(top, height=6, wrap="word")
        src.insert("1.0", str(row.get("dutch", "")))
        src.configure(state="disabled")
        src.pack(fill="both", expand=True, padx=8, pady=4)

        ttk.Label(top, text=f"Translation ({self._lang_label(col)}):").pack(anchor="w", padx=8)
        edit = tk.Text(top, height=6, wrap="word")
        edit.insert("1.0", str(row.get(col, "")))
        edit.pack(fill="both", expand=True, padx=8, pady=4)
        edit.focus_set()

        btns = ttk.Frame(top)
        btns.pack(fill="x", padx=8, pady=6)

        def commit():
            # Text always appends a trailing newline; strip exactly one.
            value = edit.get("1.0", "end")
            if value.endswith("\n"):
                value = value[:-1]
            row[col] = value
            self._refresh_item(item)
            top.destroy()

        ttk.Button(btns, text="OK", command=commit).pack(side="right")
        ttk.Button(btns, text="Cancel", command=top.destroy).pack(side="right", padx=4)
        top.bind("<Escape>", lambda e: top.destroy())

    # -- selection detail pane --------------------------------------------- #
    def on_select(self, _event=None):
        """Show the full (multi-line) source text + every translation of the row."""
        sel = self.tree.selection()
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        if sel:
            row = self._item_row.get(sel[0])
            if row is not None:
                parts = [f"[{row.get('id', '')}]  {row.get('type', '')}  "
                         f"(room: {row.get('room', '')} — {row.get('room_name', '')})",
                         "", "Nederlands:", str(row.get("dutch", ""))]
                for lang in self.languages:
                    parts += ["", f"{self._lang_label(lang)}:", str(row.get(lang, "")) or "—"]
                self.detail.insert("1.0", "\n".join(parts))
        self.detail.configure(state="disabled")

    # -- languages --------------------------------------------------------- #
    def on_add_language(self):
        from tkinter import simpledialog
        code = simpledialog.askstring(
            "Add language",
            "Language code (e.g. 'de', 'fr', 'es').\n\n"
            "Translate the new column (including LANGUAGE_NAME, the language's own name) "
            "and Export to engine/data/i18n/dracula_<code>.csv. The game discovers it "
            "automatically on the next launch -- no code change needed.",
            parent=self.master)
        if not code:
            return
        code = code.strip().lower()
        if code in self.languages or code in core.FIXED_COLUMNS:
            self.status.config(text=f"Language '{code}' already exists.")
            return
        self.languages.append(code)
        for row in self.rows:
            row.setdefault(code, "")
        self._rebuild_columns()
        self._populate()
        self.search_combo.configure(values=self._search_languages())
        self.status.config(text=f"Language '{self._lang_label(code)}' added.")

    # -- file I/O ---------------------------------------------------------- #
    def on_export(self):
        from tkinter import filedialog
        types = [("CSV (Excel)", "*.csv")]
        if core.xlsx_available():
            types.append(("Excel workbook", "*.xlsx"))
        path = filedialog.asksaveasfilename(
            title="Export translations", defaultextension=".csv", filetypes=types)
        if not path:
            return
        self._write(path)

    def _write(self, path: str):
        if path.lower().endswith(".xlsx") and core.xlsx_available():
            core.export_xlsx(self.rows, path)
        else:
            core.export_csv(self.rows, path)
        self.last_path = path
        self.status.config(text=f"Saved: {path}")

    def on_import(self):
        from tkinter import filedialog, messagebox
        types = [("CSV / Excel", "*.csv *.xlsx"), ("CSV", "*.csv")]
        if core.xlsx_available():
            types.insert(0, ("Excel workbook", "*.xlsx"))
        path = filedialog.askopenfilename(title="Import translations", filetypes=types)
        if not path:
            return
        try:
            if path.lower().endswith(".xlsx") and core.xlsx_available():
                rows = core.import_xlsx(path)
            else:
                rows = core.import_csv(path)
        except Exception as exc:                       # pragma: no cover - UI feedback
            messagebox.showerror("Import error", str(exc))
            return
        if not rows:
            messagebox.showwarning("Empty file", "No rows found.")
            return
        self.rows = rows
        self.languages = core.languages_of(rows) or ["en"]
        self.last_path = path
        self._rebuild_columns()
        self._populate()
        self.search_combo.configure(values=self._search_languages())
        self.status.config(text=f"Imported: {path} ({len(rows)} rows)")


def main(argv=None):
    import tkinter as tk
    from tkinter import messagebox

    rows = build_rows()
    root = tk.Tk()
    try:
        TranslatorApp(root, rows)
    except Exception as exc:                            # pragma: no cover
        messagebox.showerror("Error", str(exc))
        raise
    root.mainloop()


if __name__ == "__main__":
    main()
