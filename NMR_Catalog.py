"""Desktop catalog for NMR books and research papers.
Author: Vineeth Francis Thalakottoor (vineeth.thalakottoor@cea.fr)
Run with: python NMR_Catalog.py
The SQLite database is created beside this script as nmr_catalog.db.
"""

import csv
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, simpledialog, ttk


APP_TITLE = "PyCat NMR"
APP_SUBTITLE = "Python Catalog for NMR"
APP_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIRECTORY, "nmr_catalog.db")
AUTO_CSV_PATH = os.path.join(APP_DIRECTORY, "PyCat_NMR_Catalog.csv")


def open_with_system(path_or_url):
    """Open a URL, file, or folder with the default app on all desktop OSes."""
    if path_or_url.startswith(("http://", "https://")):
        webbrowser.open(path_or_url)
        return
    path = os.path.abspath(os.path.expanduser(path_or_url))
    if sys.platform.startswith("win"):
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


class NMRCatalog(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1180x720")
        self.minsize(900, 600)
        self.selected_id = None
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self._create_database()
        self._build_style()
        self._build_ui()
        self.update_filter_dropdowns()
        self.refresh_table()
        self.sync_csv()
        self.protocol("WM_DELETE_WINDOW", self.close_app)

    def _create_database(self):
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS literature (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_type TEXT NOT NULL,
                title TEXT NOT NULL,
                authors TEXT,
                year TEXT,
                source TEXT,
                volume_issue_pages TEXT,
                doi_isbn TEXT,
                keywords TEXT,
                section TEXT,
                subsection TEXT,
                corresponding_author TEXT,
                author_email TEXT,
                file_link TEXT,
                bibtex_path TEXT,
                image_paths TEXT,
                notes_path TEXT,
                notes TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        existing = {row[1] for row in self.conn.execute("PRAGMA table_info(literature)")}
        migrations = {
            "section": "TEXT", "subsection": "TEXT", "corresponding_author": "TEXT",
            "author_email": "TEXT", "bibtex_path": "TEXT", "image_paths": "TEXT", "notes_path": "TEXT",
        }
        for column, data_type in migrations.items():
            if column not in existing:
                self.conn.execute(f"ALTER TABLE literature ADD COLUMN {column} {data_type}")
        self.conn.execute("CREATE TABLE IF NOT EXISTS settings (name TEXT PRIMARY KEY, value TEXT)")
        self.conn.commit()

    def _build_style(self):
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"))
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10))
        style.configure("TButton", padding=(10, 6))
        style.configure("Treeview", rowheight=27)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    def _build_ui(self):
        header = ttk.Frame(self, padding=(14, 10))
        header.pack(fill="x")
        heading = ttk.Frame(header)
        heading.pack(side="left")
        ttk.Label(heading, text=APP_TITLE, style="Title.TLabel").pack(anchor="w")
        ttk.Label(heading, text=APP_SUBTITLE, style="Subtitle.TLabel").pack(anchor="w")

        search_frame = ttk.Frame(header)
        search_frame.pack(side="right")
        ttk.Label(search_frame, text="Search:").pack(side="left", padx=(0, 5))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=32)
        search_entry.pack(side="left")
        search_entry.bind("<KeyRelease>", lambda _event: self.refresh_table())
        self.search_by_var = tk.StringVar(value="All fields")
        ttk.Combobox(
            search_frame, textvariable=self.search_by_var,
            values=("All fields", "Title", "Keywords", "Author", "Section", "Subsection"),
            state="readonly", width=12,
        ).pack(side="left", padx=(8, 0))
        self.search_by_var.trace_add("write", lambda *_args: self.refresh_table())
        self.filter_var = tk.StringVar(value="All")
        ttk.Combobox(
            search_frame,
            textvariable=self.filter_var,
            values=("All", "Paper", "Book"),
            state="readonly",
            width=8,
        ).pack(side="left", padx=(8, 0))
        self.filter_var.trace_add("write", lambda *_args: self.refresh_table())

        ttk.Label(search_frame, text="Section:").pack(side="left", padx=(10, 4))
        self.section_filter_var = tk.StringVar(value="All sections")
        self.section_filter_combo = ttk.Combobox(
            search_frame, textvariable=self.section_filter_var, state="readonly", width=16,
        )
        self.section_filter_combo.pack(side="left")
        self.section_filter_combo.bind("<<ComboboxSelected>>", self.on_section_filter_changed)

        ttk.Label(search_frame, text="Subsection:").pack(side="left", padx=(8, 4))
        self.subsection_filter_var = tk.StringVar(value="All subsections")
        self.subsection_filter_combo = ttk.Combobox(
            search_frame, textvariable=self.subsection_filter_var, state="readonly", width=16,
        )
        self.subsection_filter_combo.pack(side="left")
        self.subsection_filter_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_table())

        body = ttk.Notebook(self)
        body.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        search_tab = ttk.Frame(body, padding=8)
        upload_tab = ttk.Frame(body, padding=8)
        body.add(search_tab, text="Search Library")
        body.add(upload_tab, text="Upload / Edit")
        self.tabs = body

        form = ttk.LabelFrame(upload_tab, text="Paper or book information", padding=12)
        table_frame = ttk.LabelFrame(search_tab, text="Books and papers", padding=8)
        form.pack(fill="both", expand=True)
        table_frame.pack(fill="both", expand=True)

        self.fields = {}
        definitions = (
            ("item_type", "Type", ("Paper", "Book")),
            ("title", "Title *", None),
            ("authors", "Authors", None),
            ("year", "Year", None),
            ("source", "Journal / Publisher", None),
            ("volume_issue_pages", "Volume, issue, pages", None),
            ("doi_isbn", "DOI / ISBN", None),
            ("keywords", "NMR keywords", None),
            ("section", "Section / Field", None),
            ("subsection", "Subsection", None),
            ("corresponding_author", "Corresponding author", None),
            ("author_email", "Author email", None),
            ("file_link", "PDF path / web link", None),
            ("bibtex_path", "BibTeX attachment", None),
            ("image_paths", "Images", None),
        )
        for row, (key, label, choices) in enumerate(definitions):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", pady=(0, 3))
            var = tk.StringVar(value="Paper" if key == "item_type" else "")
            self.fields[key] = var
            if choices:
                widget = ttk.Combobox(form, textvariable=var, values=choices, state="readonly")
            else:
                widget = ttk.Entry(form, textvariable=var)
            widget.grid(row=row, column=1, sticky="ew", pady=(0, 8))

        ttk.Button(form, text="PDF…", command=self.browse_file).grid(row=12, column=2, padx=(6, 0), pady=(0, 8))
        ttk.Button(form, text="BibTeX…", command=self.browse_bibtex_attachment).grid(row=13, column=2, padx=(6, 0), pady=(0, 8))
        ttk.Button(form, text="Images…", command=self.browse_images).grid(row=14, column=2, padx=(6, 0), pady=(0, 8))
        ttk.Label(form, text="Notes").grid(row=15, column=0, sticky="nw")
        self.notes = tk.Text(form, height=7, width=35, wrap="word")
        self.notes.grid(row=15, column=1, columnspan=2, sticky="nsew")
        form.columnconfigure(1, weight=1)
        form.rowconfigure(15, weight=1)

        buttons = ttk.Frame(form)
        buttons.grid(row=16, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        ttk.Button(buttons, text="Add", command=self.add_item).pack(side="left")
        ttk.Button(buttons, text="Update", command=self.update_item).pack(side="left", padx=5)
        ttk.Button(buttons, text="Clear", command=self.clear_form).pack(side="left")
        ttk.Button(buttons, text="Delete", command=self.delete_item).pack(side="right")

        columns = ("type", "title", "authors", "year", "section", "subsection", "source")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        headings = {"type": "Type", "title": "Title", "authors": "Authors", "year": "Year", "section": "Section", "subsection": "Subsection", "source": "Journal / Publisher"}
        widths = {"type": 65, "title": 260, "authors": 190, "year": 60, "section": 130, "subsection": 130, "source": 170}
        for column in columns:
            self.tree.heading(column, text=headings[column], command=lambda c=column: self.sort_table(c, False))
            self.tree.column(column, width=widths[column], minwidth=55)
        scroll_y = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scroll_x = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")
        self.tree.bind("<<TreeviewSelect>>", self.load_selected)
        self.tree.bind("<Double-1>", lambda _event: self.open_selected_file())
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        footer = ttk.Frame(table_frame)
        footer.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.count_label = ttk.Label(footer, text="0 items")
        self.count_label.pack(side="left")
        ttk.Button(footer, text="Open PDF / Link", command=self.open_selected_file).pack(side="right")
        ttk.Button(footer, text="View BibTeX", command=self.open_bibtex_file).pack(side="right", padx=5)
        ttk.Button(footer, text="Open Notes", command=self.open_notes_file).pack(side="right")
        ttk.Button(footer, text="Open Entry Folder", command=self.open_entry_folder).pack(side="right", padx=5)
        ttk.Button(footer, text="Edit Selected", command=lambda: self.tabs.select(1)).pack(side="right")
        ttk.Button(footer, text="Import BibTeX", command=self.import_bibtex).pack(side="right", padx=5)
        ttk.Button(footer, text="Library Folder", command=self.choose_library_folder).pack(side="right")

    def values_from_form(self):
        values = {name: variable.get().strip() for name, variable in self.fields.items()}
        values["notes"] = self.notes.get("1.0", "end").strip()
        return values

    def add_item(self):
        data = self.values_from_form()
        if not data["title"]:
            messagebox.showwarning(APP_TITLE, "Please enter a title.")
            return
        data["notes_path"] = self.write_notes_file(data["notes"])
        columns = tuple(data.keys())
        placeholders = ", ".join("?" for _ in columns)
        self.conn.execute(
            f"INSERT INTO literature ({', '.join(columns)}) VALUES ({placeholders})",
            tuple(data[column] for column in columns),
        )
        self.conn.commit()
        self.sync_csv()
        self.clear_form()
        self.refresh_table()

    def update_item(self):
        if self.selected_id is None:
            messagebox.showinfo(APP_TITLE, "Select an item to update.")
            return
        data = self.values_from_form()
        if not data["title"]:
            messagebox.showwarning(APP_TITLE, "Please enter a title.")
            return
        data["notes_path"] = self.write_notes_file(data["notes"])
        assignments = ", ".join(f"{column} = ?" for column in data)
        self.conn.execute(
            f"UPDATE literature SET {assignments}, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (*data.values(), self.selected_id),
        )
        self.conn.commit()
        self.sync_csv()
        self.refresh_table()

    def delete_item(self):
        if self.selected_id is None:
            messagebox.showinfo(APP_TITLE, "Select an item to delete.")
            return
        if messagebox.askyesno(APP_TITLE, "Delete the selected catalog entry?"):
            self.conn.execute("DELETE FROM literature WHERE id=?", (self.selected_id,))
            self.conn.commit()
            self.sync_csv()
            self.clear_form()
            self.refresh_table()

    def clear_form(self):
        self.selected_id = None
        for name, variable in self.fields.items():
            variable.set("Paper" if name == "item_type" else "")
        self.notes.delete("1.0", "end")
        for selected in self.tree.selection():
            self.tree.selection_remove(selected)

    def refresh_table(self):
        self.update_filter_dropdowns()
        query = self.search_var.get().strip()
        item_filter = self.filter_var.get()
        sql = "SELECT * FROM literature WHERE 1=1"
        parameters = []
        if query:
            pattern = f"%{query}%"
            field_map = {
                "Title": ("title",), "Keywords": ("keywords",), "Author": ("authors", "corresponding_author"),
                "Section": ("section",), "Subsection": ("subsection",),
                "All fields": ("title", "authors", "corresponding_author", "author_email", "source", "doi_isbn", "keywords", "section", "subsection", "notes"),
            }
            searchable = field_map[self.search_by_var.get()]
            sql += " AND (" + " OR ".join(f"{field} LIKE ?" for field in searchable) + ")"
            parameters.extend([pattern] * len(searchable))
        if item_filter != "All":
            sql += " AND item_type=?"
            parameters.append(item_filter)
        selected_section = self.section_filter_var.get()
        if selected_section != "All sections":
            sql += " AND section=?"
            parameters.append(selected_section)
        selected_subsection = self.subsection_filter_var.get()
        if selected_subsection != "All subsections":
            sql += " AND subsection=?"
            parameters.append(selected_subsection)
        sql += " ORDER BY title COLLATE NOCASE"
        rows = self.conn.execute(sql, parameters).fetchall()
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert("", "end", iid=str(row["id"]), values=(row["item_type"], row["title"], row["authors"], row["year"], row["section"], row["subsection"], row["source"]))
        self.count_label.configure(text=f"{len(rows)} item{'s' if len(rows) != 1 else ''}")

    def update_filter_dropdowns(self):
        sections = [
            row[0] for row in self.conn.execute(
                "SELECT DISTINCT section FROM literature WHERE trim(coalesce(section, '')) != '' ORDER BY section COLLATE NOCASE"
            )
        ]
        section_values = ["All sections", *sections]
        self.section_filter_combo.configure(values=section_values)
        if self.section_filter_var.get() not in section_values:
            self.section_filter_var.set("All sections")
        self.update_subsection_dropdown()

    def update_subsection_dropdown(self):
        selected_section = self.section_filter_var.get()
        if selected_section == "All sections":
            rows = self.conn.execute(
                "SELECT DISTINCT subsection FROM literature WHERE trim(coalesce(subsection, '')) != '' ORDER BY subsection COLLATE NOCASE"
            )
        else:
            rows = self.conn.execute(
                "SELECT DISTINCT subsection FROM literature WHERE section=? AND trim(coalesce(subsection, '')) != '' ORDER BY subsection COLLATE NOCASE",
                (selected_section,),
            )
        subsection_values = ["All subsections", *(row[0] for row in rows)]
        self.subsection_filter_combo.configure(values=subsection_values)
        if self.subsection_filter_var.get() not in subsection_values:
            self.subsection_filter_var.set("All subsections")

    def on_section_filter_changed(self, _event=None):
        self.subsection_filter_var.set("All subsections")
        self.update_subsection_dropdown()
        self.refresh_table()

    def load_selected(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            return
        self.selected_id = int(selection[0])
        row = self.conn.execute("SELECT * FROM literature WHERE id=?", (self.selected_id,)).fetchone()
        if row:
            for name, variable in self.fields.items():
                variable.set(row[name] or "")
            self.notes.delete("1.0", "end")
            self.notes.insert("1.0", row["notes"] or "")

    def browse_file(self):
        path = filedialog.askopenfilename(title="Select an NMR paper or book", filetypes=(("PDF files", "*.pdf"), ("All files", "*.*")))
        if path:
            try:
                stored_path = self.store_document(path, "PDF")
                self.fields["file_link"].set(stored_path)
            except OSError as error:
                messagebox.showerror(APP_TITLE, f"Could not store the document:\n{error}")

    def library_root(self):
        row = self.conn.execute("SELECT value FROM settings WHERE name='library_root'").fetchone()
        return row[0] if row else os.path.join(os.path.dirname(os.path.abspath(__file__)), "NMR_Library")

    def choose_library_folder(self):
        folder = filedialog.askdirectory(title="Choose the main NMR document folder", initialdir=self.library_root())
        if folder:
            self.conn.execute(
                "INSERT INTO settings(name, value) VALUES('library_root', ?) "
                "ON CONFLICT(name) DO UPDATE SET value=excluded.value", (folder,)
            )
            self.conn.commit()
            messagebox.showinfo(APP_TITLE, f"New papers will be stored under:\n{folder}")

    @staticmethod
    def safe_name(value, fallback):
        value = re.sub(r"[^\w .()-]+", "_", value or "", flags=re.UNICODE).strip(" ._")
        return value[:120] or fallback

    def entry_folder(self):
        return self.entry_folder_for(
            self.fields["section"].get(), self.fields["subsection"].get(),
            self.fields["corresponding_author"].get(), self.fields["title"].get(),
        )

    def entry_folder_for(self, section, subsection, author, title):
        parts = (
            self.safe_name(section, "Unclassified"),
            self.safe_name(subsection, "General"),
            self.safe_name(author, "Unknown author"),
            self.safe_name(title, "Untitled"),
        )
        return os.path.join(self.library_root(), *parts)

    def write_notes_file(self, notes, section=None, subsection=None, author=None, title=None):
        if section is None:
            folder = self.entry_folder()
        else:
            folder = self.entry_folder_for(section, subsection, author, title)
        os.makedirs(folder, exist_ok=True)
        destination = os.path.join(folder, "Notes.txt")
        with open(destination, "w", encoding="utf-8") as file:
            file.write(notes or "")
            if notes and not notes.endswith("\n"):
                file.write("\n")
        return destination

    def store_document(self, source, kind="Document"):
        source = os.path.abspath(os.path.expanduser(source))
        destination_dir = self.entry_folder()
        os.makedirs(destination_dir, exist_ok=True)
        extension = os.path.splitext(source)[1] or ".pdf"
        if kind == "PDF":
            base = self.safe_name(self.fields["title"].get(), os.path.splitext(os.path.basename(source))[0])
        else:
            base = self.safe_name(os.path.splitext(os.path.basename(source))[0], kind)
        destination = os.path.join(destination_dir, base + extension)
        counter = 2
        while os.path.exists(destination) and not os.path.samefile(source, destination):
            destination = os.path.join(destination_dir, f"{base}_{counter}{extension}")
            counter += 1
        if not os.path.exists(destination):
            shutil.copy2(source, destination)
        return destination

    def browse_bibtex_attachment(self):
        path = filedialog.askopenfilename(title="Attach BibTeX", filetypes=(("BibTeX files", "*.bib"), ("All files", "*.*")))
        if path:
            try:
                self.fields["bibtex_path"].set(self.store_document(path, "BibTeX"))
            except OSError as error:
                messagebox.showerror(APP_TITLE, f"Could not store the BibTeX file:\n{error}")

    def browse_images(self):
        paths = filedialog.askopenfilenames(
            title="Attach images", filetypes=(("Image files", "*.png *.jpg *.jpeg *.tif *.tiff *.bmp"), ("All files", "*.*"))
        )
        if not paths:
            return
        try:
            stored = [self.store_document(path, "Image") for path in paths]
            self.fields["image_paths"].set("; ".join(stored))
        except OSError as error:
            messagebox.showerror(APP_TITLE, f"Could not store the images:\n{error}")

    def open_selected_file(self):
        value = self.fields["file_link"].get().strip()
        if not value:
            messagebox.showinfo(APP_TITLE, "This entry has no PDF path or web link.")
            return
        try:
            if value.startswith(("http://", "https://")) or os.path.exists(os.path.expanduser(value)):
                open_with_system(value)
            else:
                messagebox.showerror(APP_TITLE, "The saved file path does not exist.")
        except Exception as error:
            messagebox.showerror(APP_TITLE, f"Could not open the file or link:\n{error}")

    def open_entry_folder(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo(APP_TITLE, "Select an entry first.")
            return
        row = self.conn.execute("SELECT file_link, bibtex_path, image_paths, notes_path FROM literature WHERE id=?", (int(selection[0]),)).fetchone()
        candidates = [row["file_link"], row["bibtex_path"], row["notes_path"]]
        candidates.extend((row["image_paths"] or "").split("; "))
        existing = next((path for path in candidates if path and os.path.exists(path)), None)
        if not existing:
            messagebox.showinfo(APP_TITLE, "No stored local document was found for this entry.")
            return
        folder = os.path.dirname(existing)
        try:
            open_with_system(folder)
        except Exception as error:
            messagebox.showerror(APP_TITLE, f"Could not open the entry folder:\n{error}")

    def open_bibtex_file(self):
        self.open_selected_attachment("bibtex_path", "BibTeX")

    def open_notes_file(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo(APP_TITLE, "Select an entry first.")
            return
        row = self.conn.execute("SELECT * FROM literature WHERE id=?", (int(selection[0]),)).fetchone()
        path = row["notes_path"]
        if not path or not os.path.exists(path):
            try:
                path = self.write_notes_file(
                    row["notes"] or "", row["section"], row["subsection"],
                    row["corresponding_author"], row["title"],
                )
                self.conn.execute("UPDATE literature SET notes_path=? WHERE id=?", (path, int(selection[0])))
                self.conn.commit()
                self.sync_csv()
            except OSError as error:
                messagebox.showerror(APP_TITLE, f"Could not create Notes.txt:\n{error}")
                return
        try:
            open_with_system(path)
        except Exception as error:
            messagebox.showerror(APP_TITLE, f"Could not open Notes.txt:\n{error}")

    def open_selected_attachment(self, column, label):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo(APP_TITLE, "Select an entry first.")
            return
        row = self.conn.execute(f"SELECT {column} FROM literature WHERE id=?", (int(selection[0]),)).fetchone()
        path = row[column] or ""
        if not path or not os.path.exists(os.path.expanduser(path)):
            messagebox.showinfo(APP_TITLE, f"This entry has no stored {label} file.")
            return
        try:
            open_with_system(path)
        except Exception as error:
            messagebox.showerror(APP_TITLE, f"Could not open the {label} file:\n{error}")

    def sync_csv(self):
        """Keep a spreadsheet-readable catalog synchronized automatically."""
        columns = ("item_type", "title", "authors", "year", "source", "volume_issue_pages", "doi_isbn", "keywords", "section", "subsection", "corresponding_author", "author_email", "file_link", "bibtex_path", "image_paths", "notes_path", "notes")
        rows = self.conn.execute(f"SELECT {', '.join(columns)} FROM literature ORDER BY title").fetchall()
        try:
            temporary = AUTO_CSV_PATH + ".tmp"
            with open(temporary, "w", newline="", encoding="utf-8-sig") as file:
                writer = csv.writer(file)
                writer.writerow(columns)
                writer.writerows(tuple(row[column] for column in columns) for row in rows)
            os.replace(temporary, AUTO_CSV_PATH)
        except OSError as error:
            messagebox.showwarning(APP_TITLE, f"The automatic CSV file could not be updated:\n{error}")

    @staticmethod
    def parse_bibtex(text):
        """Parse common BibTeX syntax without requiring an external package."""
        entries = []
        position = 0
        while True:
            match = re.search(r"@(\w+)\s*\{", text[position:], re.IGNORECASE)
            if not match:
                break
            entry_type = match.group(1).lower()
            start = position + match.end()
            depth = 1
            quoted = False
            escaped = False
            end = start
            while end < len(text) and depth:
                char = text[end]
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    quoted = not quoted
                elif not quoted and char == "{":
                    depth += 1
                elif not quoted and char == "}":
                    depth -= 1
                end += 1
            body = text[start:end - 1]
            comma = body.find(",")
            fields_text = body[comma + 1:] if comma >= 0 else ""
            fields = {}
            index = 0
            while index < len(fields_text):
                field_match = re.search(r"([A-Za-z][\w-]*)\s*=\s*", fields_text[index:])
                if not field_match:
                    break
                name = field_match.group(1).lower()
                index += field_match.end()
                if index >= len(fields_text):
                    break
                opener = fields_text[index]
                if opener in "{\"":
                    closer = "}" if opener == "{" else '"'
                    index += 1
                    value_start = index
                    nested = 1 if opener == "{" else 0
                    escaped = False
                    while index < len(fields_text):
                        char = fields_text[index]
                        if escaped:
                            escaped = False
                        elif char == "\\":
                            escaped = True
                        elif opener == "{" and char == "{":
                            nested += 1
                        elif char == closer:
                            if opener == "{":
                                nested -= 1
                                if nested == 0:
                                    break
                            else:
                                break
                        index += 1
                    value = fields_text[value_start:index]
                    index += 1
                else:
                    value_match = re.match(r"([^,]+)", fields_text[index:])
                    value = value_match.group(1).strip() if value_match else ""
                    index += len(value_match.group(0)) if value_match else 0
                value = re.sub(r"[{}]", "", value).replace("\\&", "&").strip()
                fields[name] = value
                next_comma = fields_text.find(",", index)
                index = next_comma + 1 if next_comma >= 0 else len(fields_text)
            entries.append((entry_type, fields))
            position = end
        return entries

    def import_bibtex(self):
        path = filedialog.askopenfilename(title="Import BibTeX", filetypes=(("BibTeX files", "*.bib"), ("Text files", "*.txt"), ("All files", "*.*")))
        if not path:
            return
        section = simpledialog.askstring(APP_TITLE, "Section / field for these entries (optional):", parent=self) or ""
        try:
            with open(path, encoding="utf-8-sig") as file:
                entries = self.parse_bibtex(file.read())
            imported = skipped = 0
            columns = ("item_type", "title", "authors", "year", "source", "volume_issue_pages", "doi_isbn", "keywords", "section", "subsection", "corresponding_author", "author_email", "file_link", "bibtex_path", "image_paths", "notes_path", "notes")
            for entry_type, bib in entries:
                title = bib.get("title", "").strip()
                if not title:
                    skipped += 1
                    continue
                doi_isbn = bib.get("doi") or bib.get("isbn", "")
                duplicate = self.conn.execute(
                    "SELECT id FROM literature WHERE lower(title)=lower(?) OR (? != '' AND lower(doi_isbn)=lower(?))",
                    (title, doi_isbn, doi_isbn),
                ).fetchone()
                if duplicate:
                    skipped += 1
                    continue
                source = bib.get("journal") or bib.get("booktitle") or bib.get("publisher", "")
                volume_data = ", ".join(filter(None, (bib.get("volume"), bib.get("number"), bib.get("pages"))))
                file_link = bib.get("file") or bib.get("url", "")
                if file_link and ":" in file_link and not file_link.startswith(("http://", "https://")):
                    candidates = [part for part in file_link.split(":") if part.lower().endswith(".pdf")]
                    file_link = candidates[0] if candidates else file_link
                author_text = bib.get("author", "")
                corresponding = author_text.split(" and ")[0] if author_text else ""
                self.fields["section"].set(section)
                self.fields["subsection"].set("")
                self.fields["corresponding_author"].set(corresponding)
                self.fields["title"].set(title)
                if file_link and os.path.isfile(os.path.expanduser(file_link)):
                    file_link = self.store_document(file_link, "PDF")
                stored_bib = self.store_bibtex_entry(path, title, entry_type, bib)
                notes = bib.get("note") or bib.get("abstract", "")
                notes_path = self.write_notes_file(notes, section, "", corresponding, title)
                values = (
                    "Book" if entry_type in ("book", "inbook") else "Paper",
                    title,
                    author_text.replace(" and ", "; "),
                    bib.get("year", ""), source, volume_data, doi_isbn,
                    bib.get("keywords", ""), section, "", corresponding, bib.get("email", ""),
                    file_link, stored_bib, "", notes_path, notes,
                )
                self.conn.execute(f"INSERT INTO literature ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})", values)
                imported += 1
            self.conn.commit()
            self.sync_csv()
            self.refresh_table()
            messagebox.showinfo(APP_TITLE, f"Imported {imported} BibTeX entries.\nSkipped {skipped} incomplete or duplicate entries.")
        except (OSError, sqlite3.Error) as error:
            self.conn.rollback()
            messagebox.showerror(APP_TITLE, f"BibTeX import failed:\n{error}")

    def store_bibtex_entry(self, source_bib, title, entry_type, fields):
        """Store a small BibTeX file beside the paper instead of only linking the bulk import."""
        os.makedirs(self.entry_folder(), exist_ok=True)
        destination = os.path.join(self.entry_folder(), self.safe_name(title, "reference") + ".bib")
        citation_key = self.safe_name(fields.get("doi") or title, "reference").replace(" ", "_")
        with open(destination, "w", encoding="utf-8") as file:
            file.write(f"@{entry_type}{{{citation_key},\n")
            for name, value in fields.items():
                file.write(f"  {name} = {{{value}}},\n")
            file.write("}\n")
        return destination

    def sort_table(self, column, reverse):
        rows = [(self.tree.set(item, column), item) for item in self.tree.get_children("")]
        rows.sort(key=lambda pair: pair[0].casefold(), reverse=reverse)
        for index, (_value, item) in enumerate(rows):
            self.tree.move(item, "", index)
        self.tree.heading(column, command=lambda: self.sort_table(column, not reverse))

    def close_app(self):
        self.conn.close()
        self.destroy()


if __name__ == "__main__":
    NMRCatalog().mainloop()
