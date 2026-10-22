r"""PyCat NMR — Python Catalog for NMR papers, books, manuals, theses, notes, images, and equations.

Author: Vineeth Francis Thalakottoor (vineeth.thalakottoor@cea.fr)

Run with: python PyCat_NMR.py
Equation previews require: python -m pip install matplotlib
Quick preview uses Matplotlib MathText. Full LaTeX uses pdflatex + pdftoppm.
Ubuntu/Debian: sudo apt install texlive-latex-base texlive-latex-recommended texlive-latex-extra poppler-utils
Full LaTeX image conversion requires Pillow: python -m pip install pillow
Enter one equation per line, optionally wrapped in $...$, $$...$$, \[...\], or \(...\).
The SQLite database and NMR_Library are created beside this script.
Catalog attachment paths are stored relative to this folder so the complete
PyCat directory can move between Linux, Windows, and macOS on a USB drive.
"""

import base64
import io
import filecmp
import csv
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tkinter as tk
import tempfile
import threading
import unicodedata
from concurrent.futures import ThreadPoolExecutor
import webbrowser
from tkinter import filedialog, messagebox, simpledialog, ttk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
    CatalogWindow = TkinterDnD.Tk
except ImportError:
    DND_FILES = None
    DND_AVAILABLE = False
    CatalogWindow = tk.Tk


_MATH_RENDER_LOCK = threading.RLock()

CATEGORY_FOLDERS = {
    "Paper": "Papers", "Book": "Books", "Manual": "Manuals", "Thesis": "Thesis",
    "Note": "Notes", "Image": "Images", "Equation": "Equations", "Lecture": "Lectures", "Conference": "Conferences", "Report": "Reports", "Researchers": "Researchers", "Websites": "Websites",
}

ITEM_TYPES = ("Paper", "Book", "Manual", "Thesis", "Lecture", "Conference", "Report", "Researchers", "Websites")
PDF_TYPES = tuple(kind for kind in ITEM_TYPES if kind not in ("Researchers", "Websites")) + ("Note", "Image", "Equation")


APP_VERSION = "1.0.18"
APP_TITLE = f"PyCat NMR v{APP_VERSION}"
APP_SUBTITLE = "Python Catalog for NMR"
__author__ = "Vineeth Francis Thalakottoor"
__email__ = "vineeth.thalakottoor@cea.fr"
APP_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIRECTORY, "nmr_catalog.db")
AUTO_CSV_PATH = os.path.join(APP_DIRECTORY, "PyCat_NMR_Catalog.csv")

SETUP_README = r"""PyCat NMR — Setup and use

Keep PyCat_NMR.py, nmr_catalog.db, PyCat_NMR_Catalog.csv, and NMR_Library together.
Install Python 3 before creating an environment. Internet access is required to
download packages; the catalog works offline after setup.

WINDOWS — COMMAND PROMPT (CMD)

Create the environment once:

    py -m venv "%USERPROFILE%\venvs\pycat"

Activate it in each new CMD window:

    call "%USERPROFILE%\venvs\pycat\Scripts\activate.bat"

Install packages after activation:

    python -m pip install --upgrade pip
    python -m pip install --upgrade matplotlib pillow tkinterdnd2

Go to your PyCat folder (replace this example with your actual path) and run:

    cd /d "C:\path\to\PyCat"
    python PyCat_NMR.py

Leave the environment when finished:

    deactivate

These commands are for CMD. Windows Python should include Tcl/Tk support.

LINUX — TERMINAL (UBUNTU / DEBIAN)

Install the system prerequisites once:

    sudo apt update
    sudo apt install python3 python3-venv python3-tk

Create the environment once:

    python3 -m venv ~/venvs/pycat

Activate it in each new terminal:

    source ~/venvs/pycat/bin/activate

Install packages after activation:

    python -m pip install --upgrade pip
    python -m pip install --upgrade matplotlib pillow tkinterdnd2

Go to your PyCat folder (replace this example with your actual path) and run:

    cd "/path/to/PyCat"
    python PyCat_NMR.py

Leave the environment when finished:

    deactivate

Other Linux distributions use their own package manager for system prerequisites.

IMAGES — COPY FROM CLIPBOARD

1. Enter the entry title and choose a type that supports image attachments.
2. Copy an image or screenshot to the clipboard.
3. Beside Images, click Copy from clipboard.
4. Click Add or Update to save the catalog entry.

Pasted images are saved as PNG files in the entry's Images folder. Repeated
copies add images with distinct names and retain existing attachments.
On Windows you can also copy image files in File Explorer.

Linux clipboard access needs xclip for X11 or wl-paste for Wayland:

    sudo apt install xclip wl-clipboard

OPTIONAL — FULL LATEX AND PDF PREVIEW

On Ubuntu/Debian:

    sudo apt install texlive-latex-base texlive-latex-recommended texlive-latex-extra poppler-utils

On Windows install a LaTeX distribution (such as MiKTeX or TeX Live) and Poppler.
Ensure pdflatex and pdftoppm are available on PATH, then restart PyCat.
Catalog storage, plain text, and image attachments do not need LaTeX.

PORTABLE USE

Keep the Python environment on each computer and the whole PyCat folder on
your USB drive. Use that computer's environment to run the USB copy.
Close PyCat before backing up or ejecting the drive.

DELETE UNUSED FOLDERS

In Search Library, click Delete unused folders. Review the listed folders,
then click Delete listed folders permanently to remove them and their contents.
Cancel leaves them untouched. The full saved catalog is checked, including
entries hidden by search filters. Active entry folders, referenced attachments,
and the current upload form are protected. Loose files directly inside
NMR_Library are left in place; cleanup removes unused folders only.

After renaming an entry, save it with Update. Organize Files can move still-used
attachments into their current entry folders before you run cleanup again.
Unused empty categories are not recreated at startup.
"""


def normalize_search_text(value):
    """Case-fold Unicode text and treat punctuation/symbols as word separators."""
    text = unicodedata.normalize("NFC", value or "").casefold()
    return " ".join(re.findall(r"[^\W_]+", text, flags=re.UNICODE))


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


class NMRCatalog(CatalogWindow):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1440x900")
        self.minsize(900, 600)
        self.selected_id = None
        self._latex_executor = ThreadPoolExecutor(max_workers=1)
        self._latex_future = None
        self._pdf_future = None
        self._pdf_poll_job = None
        self._latex_poll_job = None
        self._preview_generation = 0
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row
        self._create_database()
        self.make_existing_paths_portable()
        self.ensure_category_folders()
        self._build_style()
        self._build_ui()
        self.update_filter_dropdowns()
        self.refresh_table()
        self.sync_csv()
        self.protocol("WM_DELETE_WINDOW", self.close_app)

    def _create_database(self):
        self.conn.create_function("pycat_search", 1, normalize_search_text, deterministic=True)
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
                lecture_pdf_paths TEXT,
                supplementary_paths TEXT,
                bibtex_path TEXT,
                image_paths TEXT,
                notes_path TEXT,
                notes TEXT,
                equation_latex TEXT,
                equation_renderer TEXT,
                equation_pdf_path TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        existing = {row[1] for row in self.conn.execute("PRAGMA table_info(literature)")}
        migrations = {
            "section": "TEXT", "subsection": "TEXT", "corresponding_author": "TEXT",
            "author_email": "TEXT", "supplementary_paths": "TEXT", "bibtex_path": "TEXT",
            "image_paths": "TEXT", "notes_path": "TEXT", "equation_latex": "TEXT",
            "equation_renderer": "TEXT", "equation_pdf_path": "TEXT",
            "lecture_pdf_paths": "TEXT", "website": "TEXT", "place": "TEXT",
            "report_date": "TEXT", "notes_pdf_path": "TEXT",
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
        style.configure("Toolbar.TButton", padding=(5, 6))
        style.configure("Treeview", rowheight=27)
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    def _build_ui(self):
        header = ttk.Frame(self, padding=(14, 10))
        header.pack(fill="x")
        heading = ttk.Frame(header)
        heading.pack(side="left")
        ttk.Label(heading, text=APP_TITLE, style="Title.TLabel").pack(anchor="w")
        ttk.Label(heading, text=APP_SUBTITLE, style="Subtitle.TLabel").pack(anchor="w")

        search_frame = ttk.Frame(self, padding=(14, 0, 14, 10))
        search_frame.pack(fill="x")
        search_frame.columnconfigure(1, weight=1)
        ttk.Label(search_frame, text="Search:").grid(row=0, column=0, padx=(0, 5))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=22)
        search_entry.grid(row=0, column=1, sticky="ew")
        search_entry.bind("<KeyRelease>", lambda _event: self.refresh_table())
        self.search_by_var = tk.StringVar(value="All fields")
        ttk.Combobox(
            search_frame, textvariable=self.search_by_var,
            values=("All fields", "Title", "Keywords", "Author", "Section", "Subsection"),
            state="readonly", width=10,
        ).grid(row=0, column=2, padx=(6, 0))
        self.search_by_var.trace_add("write", lambda *_args: self.refresh_table())
        self.filter_var = tk.StringVar(value="All")
        ttk.Combobox(
            search_frame,
            textvariable=self.filter_var,
            values=("All", *("Lecture notes" if kind == "Lecture" else kind for kind in ITEM_TYPES)),
            state="readonly",
            width=10,
        ).grid(row=0, column=3, padx=(6, 0))
        self.filter_var.trace_add("write", lambda *_args: self.refresh_table())

        ttk.Label(search_frame, text="Section:").grid(row=0, column=4, padx=(8, 4))
        self.section_filter_var = tk.StringVar(value="All sections")
        self.section_filter_combo = ttk.Combobox(
            search_frame, textvariable=self.section_filter_var, state="readonly", width=14,
        )
        self.section_filter_combo.grid(row=0, column=5)
        self.section_filter_combo.bind("<<ComboboxSelected>>", self.on_section_filter_changed)

        ttk.Label(search_frame, text="Subsection:").grid(row=0, column=6, padx=(8, 4))
        self.subsection_filter_var = tk.StringVar(value="All subsections")
        self.subsection_filter_combo = ttk.Combobox(
            search_frame, textvariable=self.subsection_filter_var, state="readonly", width=14,
        )
        self.subsection_filter_combo.grid(row=0, column=7)
        self.subsection_filter_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_table())
        ttk.Button(search_frame, text="Organize Files", command=self.organize_existing_files,
                   style="Toolbar.TButton").grid(row=0, column=8, padx=(8, 0))
        ttk.Button(search_frame, text="Delete unused folders…", command=self.preview_unused_folders,
                   style="Toolbar.TButton").grid(row=0, column=9, padx=(5, 0))

        body = ttk.Notebook(self)
        body.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        search_tab = ttk.Frame(body, padding=8)
        upload_tab = ttk.Frame(body, padding=8)
        body.add(search_tab, text="Search Library")
        body.add(upload_tab, text="Upload / Edit")
        self.tabs = body
        self._build_readme_tab(body)

        # Scroll metadata independently so Add/Update remain accessible on small screens.
        editor = ttk.Panedwindow(upload_tab, orient="horizontal")
        editor.pack(fill="both", expand=True)
        self.editor = editor
        metadata = ttk.Frame(editor)
        editor.add(metadata, weight=3)
        form_canvas = tk.Canvas(metadata, highlightthickness=0, width=520)
        form_scroll = ttk.Scrollbar(metadata, orient="vertical", command=form_canvas.yview)
        form_canvas.configure(yscrollcommand=form_scroll.set)
        form_scroll.pack(side="right", fill="y")
        form_canvas.pack(side="left", fill="both", expand=True)
        form = ttk.LabelFrame(form_canvas, text="Entry information", padding=12)
        form_window = form_canvas.create_window((0, 0), window=form, anchor="nw")
        form.bind("<Configure>", lambda _e: form_canvas.configure(scrollregion=form_canvas.bbox("all")))
        form_canvas.bind("<Configure>", lambda e: form_canvas.itemconfigure(form_window, width=e.width))
        self.equation_panel = ttk.LabelFrame(editor, text="Notes and rendered PDF — up to 100 A4 pages", padding=12)
        editor.add(self.equation_panel, weight=2)
        table_frame = ttk.LabelFrame(search_tab, text="Papers, books, manuals, theses, lecture notes, conferences, reports, researchers, and websites", padding=8)
        table_frame.pack(fill="both", expand=True)

        self.fields = {}
        self.field_widgets = {}
        self.field_labels = {}
        self.attachment_buttons = {}
        self.attachment_actions = {}
        definitions = (
            ("item_type", "Type", ITEM_TYPES),
            ("title", "Title *", None),
            ("authors", "Authors * (literature)", None),
            ("year", "Year", None),
            ("source", "Journal / Publisher / University", None),
            ("volume_issue_pages", "Volume, issue, pages", None),
            ("doi_isbn", "DOI / ISBN", None),
            ("keywords", "NMR keywords", None),
            ("section", "Section / Field *", None),
            ("subsection", "Subsection *", None),
            ("corresponding_author", "Corresponding author", None),
            ("author_email", "Author email", None),
            ("file_link", "PDF attachment", None),
            ("lecture_pdf_paths", "Lecture PDFs", None),
            ("supplementary_paths", "Supplementary files", None),
            ("bibtex_path", "BibTeX / RIS attachment", None),
            ("image_paths", "Images", None),
            ("website", "Website", None),
            ("place", "Conference place", None),
            ("report_date", "Date (YYYY-MM-DD)", None),
        )
        self.form = form
        for row, (key, label, choices) in enumerate(definitions):
            row = row if key == "item_type" else row + 1
            field_label = ttk.Label(form, text=label)
            field_label.grid(row=row, column=0, sticky="w", pady=(0, 3))
            self.field_labels[key] = field_label
            var = tk.StringVar(value="Paper" if key == "item_type" else "")
            self.fields[key] = var
            if key == "item_type":
                widget = ttk.Frame(form)
                for index, choice in enumerate(choices):
                    ttk.Radiobutton(widget, text="Lecture notes" if choice == "Lecture" else choice, variable=var, value=choice).grid(
                        row=index // 4, column=index % 4, sticky="w", padx=(0, 12), pady=2)
            elif key in ("section", "subsection"):
                widget = ttk.Combobox(form, textvariable=var, state="normal",
                                     postcommand=self.update_entry_suggestions)
            else:
                widget = ttk.Entry(form, textvariable=var, state="readonly" if key in ("file_link", "lecture_pdf_paths") else "normal")
            self.field_widgets[key] = widget
            widget.grid(row=row, column=1, columnspan=2 if key == "item_type" else 1, sticky="ew", pady=(0, 8))

        self.fields["section"].trace_add("write", self.update_entry_suggestions)

        self.rearrange_authors_button = ttk.Button(
            form, text="Rearrange authors", command=self.rearrange_authors
        )
        self.rearrange_authors_button.grid(row=3, column=2, padx=(6, 0), pady=(0, 8), sticky="w")

        # Stored separately from the main paper PDF. It is managed through the
        # equation editor and the dedicated Open LaTeX PDF buttons.
        self.fields["equation_pdf_path"] = tk.StringVar()
        self.fields["notes_pdf_path"] = tk.StringVar()

        for row, key, label, command in (
            (13, "file_link", "Select PDF…", self.browse_file),
            (14, "lecture_pdf_paths", "Select PDFs…", self.browse_lecture_pdfs),
            (15, "supplementary_paths", "Supplement…", self.browse_supplementary),
            (16, "bibtex_path", "BibTeX / RIS…", self.browse_bibtex_attachment),
            (17, "image_paths", "Images…", self.browse_images),
        ):
            actions = ttk.Frame(form)
            actions.grid(row=row, column=2, padx=(6, 0), pady=(0, 8), sticky="w")
            self.attachment_actions[key] = actions
            button = ttk.Button(actions, text=label, command=command)
            button.pack(side="left")
            self.attachment_buttons[key] = button
            if key == "file_link":
                drop_text = "Drop PDF here" if DND_AVAILABLE else "PDF drag-and-drop: install tkinterdnd2"
                self.pdf_drop_target = ttk.Label(actions, text=drop_text, relief="groove", padding=(8, 6))
                self.pdf_drop_target.pack(side="left", padx=(5, 0))
                if DND_AVAILABLE:
                    for target in (self.pdf_drop_target, self.field_widgets["file_link"]):
                        target.drop_target_register(DND_FILES)
                        target.dnd_bind("<<Drop>>", self.drop_pdf)
            if key == "lecture_pdf_paths":
                self.lecture_drop_target = ttk.Label(actions, text="Drop lecture PDFs here" if DND_AVAILABLE else "Drag-and-drop: install tkinterdnd2", relief="groove", padding=(8, 6))
                self.lecture_drop_target.pack(side="left", padx=(5, 0))
                if DND_AVAILABLE:
                    for target in (self.lecture_drop_target, self.field_widgets[key]):
                        target.drop_target_register(DND_FILES)
                        target.dnd_bind("<<Drop>>", self.drop_lecture_pdfs)
            if key == "supplementary_paths":
                drop_text = "Drop supplementary files here" if DND_AVAILABLE else "Drag-and-drop: install tkinterdnd2"
                self.supplementary_drop_target = ttk.Label(
                    actions, text=drop_text, relief="groove", padding=(8, 6)
                )
                self.supplementary_drop_target.pack(side="left", padx=(5, 0))
                if DND_AVAILABLE:
                    for target in (self.supplementary_drop_target, self.field_widgets["supplementary_paths"]):
                        target.drop_target_register(DND_FILES)
                        target.dnd_bind("<<Drop>>", self.drop_supplementary)
            if key == "bibtex_path":
                paste_button = ttk.Button(actions, text="Paste…", command=self.paste_bibtex_attachment)
                paste_button.pack(side="left", padx=(4, 0))
                self.attachment_buttons["bibtex_paste"] = paste_button
                drop_text = "Drop .bib/.bibtex/.ris here" if DND_AVAILABLE else "Drag-and-drop: install tkinterdnd2"
                self.bibtex_drop_target = ttk.Label(actions, text=drop_text, relief="groove", padding=(8, 6))
                self.bibtex_drop_target.pack(side="left", padx=(5, 0))
                if DND_AVAILABLE:
                    for target in (self.bibtex_drop_target, self.field_widgets["bibtex_path"]):
                        target.drop_target_register(DND_FILES)
                        target.dnd_bind("<<Drop>>", self.drop_bibtex)
            if key == "image_paths":
                ttk.Button(actions, text="Copy from clipboard", command=self.copy_image_from_clipboard).pack(side="left", padx=(5, 0))
                drop_text = "Drop images here" if DND_AVAILABLE else "Drag-and-drop: install tkinterdnd2"
                self.images_drop_target = ttk.Label(actions, text=drop_text, relief="groove", padding=(8, 6))
                self.images_drop_target.pack(side="left", padx=(5, 0))
                if DND_AVAILABLE:
                    for target in (self.images_drop_target, self.field_widgets["image_paths"]):
                        target.drop_target_register(DND_FILES)
                        target.dnd_bind("<<Drop>>", self.drop_images)
        form.columnconfigure(1, weight=1)

        buttons = ttk.Frame(upload_tab)
        buttons.pack(fill="x", pady=(12, 0))
        ttk.Button(buttons, text="Add", command=self.add_item).pack(side="left")
        ttk.Button(buttons, text="Update", command=self.update_item).pack(side="left", padx=5)
        ttk.Button(buttons, text="Clear", command=self.clear_form).pack(side="left")
        ttk.Button(buttons, text="Delete", command=self.delete_item).pack(side="right")

        ttk.Button(buttons, text="Open website", command=self.open_conference_website).pack(side="left", padx=8)
        self._build_equation_editor()
        self.fields["item_type"].trace_add("write", self.update_type_controls)
        self.update_type_controls()

        columns = ("type", "title", "authors", "year", "section", "subsection", "source")
        self.tree = ttk.Treeview(table_frame, columns=columns,
            displaycolumns=("type", "section", "subsection", "title", "authors", "year", "source"),
            show="headings", selectmode="browse")
        headings = {"type": "Type", "title": "Title", "authors": "Authors", "year": "Year", "section": "Section", "subsection": "Subsection", "source": "Journal / Publisher / University"}
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
        self.count_label.pack(anchor="w")
        actions = ttk.Frame(footer)
        actions.pack(fill="x", pady=(5, 0))
        for column, (label, command) in enumerate((
            ("Open / View", self.open_selected_file),
            ("Open Supplementary", self.open_supplementary),
            ("Open Notes", self.open_notes_file),
            ("Open Notes PDF", lambda: self.open_selected_attachment("notes_pdf_path", "Notes PDF")),
            ("View BibTeX / RIS", self.open_bibtex_file),
            ("Open LaTeX PDF", self.open_selected_equation_pdf),
            ("Open Images", self.open_images),
            ("Edit Selected", lambda: self.tabs.select(1)),
            ("Open Entry Folder", self.open_entry_folder),
        )):
            ttk.Button(actions, text=label, command=command, style="Toolbar.TButton").grid(
                row=0, column=column, sticky="ew", padx=(0 if column == 0 else 4, 0))
            actions.columnconfigure(column, weight=1)


    def _build_readme_tab(self, notebook):
        tab = ttk.Frame(notebook, padding=12)
        notebook.add(tab, text="ReadMe")
        text = tk.Text(tab, wrap="word", font=("Courier", 10), padx=12, pady=12)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        text.pack(fill="both", expand=True)
        text.insert("1.0", SETUP_README)
        text.configure(state="disabled")

    def _build_equation_editor(self):
        outer = self.equation_panel
        self.workspace_tabs = ttk.Notebook(outer)
        self.workspace_tabs.pack(fill="both", expand=True)
        source_area = ttk.Frame(self.workspace_tabs, padding=4)
        self.pdf_area = ttk.Frame(self.workspace_tabs, padding=4)
        self.workspace_tabs.add(source_area, text="LaTeX")
        self.workspace_tabs.add(self.pdf_area, text="LaTeX output")
        self.document_tabs = ttk.Notebook(source_area)
        self.document_tabs.pack(fill="both", expand=True)
        notes_tab = ttk.Frame(self.document_tabs)
        panel = ttk.Frame(self.document_tabs)
        self.plain_source_tab = notes_tab
        self.latex_source_tab = panel
        self.document_tabs.add(notes_tab, text="Plain text")
        self.document_tabs.add(panel, text="LaTeX code")
        self.document_tabs.select(panel)
        self.notes = tk.Text(notes_tab, height=14, width=32, wrap="word", undo=True)
        scroll = ttk.Scrollbar(notes_tab, command=self.notes.yview)
        self.notes.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.notes.pack(fill="both", expand=True)
        note_actions = ttk.Frame(notes_tab)
        self.note_actions = note_actions
        note_actions.pack(fill="x")
        for label, command in (("Preview", lambda: self.preview_equation(True)),
                               ("Save PDF…", self.save_equation_pdf),
                               ("Open PDF", self.open_current_equation_pdf),
                               ("New page", self.insert_document_page)):
            ttk.Button(note_actions, text=label, command=command).pack(side="left")
        self.document_tabs.bind("<<NotebookTabChanged>>", lambda e: self.preview_equation())
        self._preview_pdf = None
        self._preview_page = 1
        self._preview_pages = 1
        self.renderer_var = tk.StringVar(value="Text + equations")
        self.equation_text = tk.Text(panel, height=9, width=32, wrap="word", undo=True)
        equation_scroll = ttk.Scrollbar(panel, command=self.equation_text.yview)
        equation_scroll.pack(side="right", fill="y")
        self.equation_text.configure(yscrollcommand=equation_scroll.set)
        self.equation_text.pack(fill="both", expand=True)
        self.equation_text.bind("<<Modified>>", self._equation_modified)
        self._preview_job = None
        self._equation_photo = None
        actions = ttk.Frame(panel)
        actions.pack(fill="x", pady=8)
        self.preview_button = ttk.Button(actions, text="Preview", command=lambda: self.preview_equation(compile_full=True))
        self.preview_button.pack(side="left")
        self.save_pdf_button = ttk.Button(actions, text="Save PDF…", command=self.save_equation_pdf)
        self.save_pdf_button.pack(side="left", padx=4)
        self.open_latex_pdf_button = ttk.Button(actions, text="Open PDF", command=self.open_current_equation_pdf)
        self.open_latex_pdf_button.pack(side="left")
        extra = ttk.Frame(panel)
        extra.pack(fill="x")
        ttk.Button(extra, text="Clear code", command=self.clear_latex_code).pack(side="left")
        ttk.Button(extra, text="Insert default report", command=self.insert_default_latex_code).pack(side="left", padx=4)
        ttk.Button(extra, text="Insert default beamer", command=self.insert_default_beamer).pack(side="left", padx=4)
        ttk.Button(extra, text="New page", command=self.insert_document_page).pack(side="left")
        navigation = ttk.Frame(self.pdf_area)
        navigation.pack(fill="x")
        ttk.Button(navigation, text="Previous page", command=lambda: self.change_preview_page(-1)).pack(side="left")
        self.page_label = ttk.Label(navigation, text="Page 1")
        self.page_label.pack(side="left", padx=8)
        ttk.Button(navigation, text="Next page", command=lambda: self.change_preview_page(1)).pack(side="left")
        self.equation_status = ttk.Label(outer, text="", wraplength=330)
        self.equation_status.pack(fill="x", pady=(0, 8))
        ttk.Button(navigation, text="Back to LaTeX", command=lambda: self.workspace_tabs.select(0)).pack(side="right")
        preview = ttk.Frame(self.pdf_area)
        preview.pack(fill="both", expand=True)
        self.equation_canvas = tk.Canvas(preview, background="white", highlightthickness=1,
                                        highlightbackground="#cccccc", width=300, height=220)
        yscroll = ttk.Scrollbar(preview, orient="vertical", command=self.equation_canvas.yview)
        xscroll = ttk.Scrollbar(preview, orient="horizontal", command=self.equation_canvas.xview)
        self.equation_canvas.configure(xscrollcommand=xscroll.set, yscrollcommand=yscroll.set)
        self.equation_canvas.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        preview.rowconfigure(0, weight=1)
        preview.columnconfigure(0, weight=1)
        self.preview_equation()

    @staticmethod
    def report_template(title="", authors="", report_date=""):
        source = r"""\documentclass[a4paper,12pt]{article}

% Report packages
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[margin=25mm]{geometry}
\usepackage{amsmath,amssymb,bm}
\usepackage{graphicx}
\usepackage{booktabs,array,longtable}
\usepackage{float}
\usepackage{xcolor}
\usepackage[hidelinks]{hyperref}

\title{Report title}
\author{Author name}
\date{\today}

\begin{document}
\maketitle



% Uncomment to add a table of contents:
% \tableofcontents
% \newpage

\section{Introduction}
Describe the background and objectives of this report.


\end{document}
"""
        if title:
            source = source.replace(r"\title{Report title}", r"\title{" + NMRCatalog.escape_latex(title) + "}")
        if authors:
            source = source.replace(r"\author{Author name}", r"\author{" + NMRCatalog.escape_latex(authors) + "}")
        if report_date:
            source = source.replace(r"\date{\today}", r"\date{" + NMRCatalog.escape_latex(report_date) + "}")
        return source

    def clear_latex_code(self):
        self.equation_text.edit_separator()
        self.equation_text.delete("1.0", "end")
        self.equation_text.edit_separator()
        self.equation_text.focus_set()
        self.preview_equation()

    def insert_default_latex_code(self, source=None):
        self.equation_text.edit_separator()
        self.equation_text.insert("insert", self.report_template() if source is None else source)
        self.equation_text.edit_separator()
        self.renderer_var.set("Full LaTeX")
        self.document_tabs.select(self.latex_source_tab)
        self.workspace_tabs.select(0)
        self.equation_text.focus_set()
        self.preview_equation()

    @staticmethod
    def beamer_template():
        return r"""\documentclass[aspectratio=169]{beamer}
\title{Presentation title}
\author{Author name}
\date{\today}

\begin{document}
\begin{frame}
\titlepage
\end{frame}

\begin{frame}{Introduction}
\begin{itemize}
\item First point.
\item Second point.
\end{itemize}
\end{frame}
\end{document}
"""

    def insert_default_beamer(self):
        self.insert_default_latex_code(self.beamer_template())

    def notes_active(self):
        return self.document_tabs.index(self.document_tabs.select()) == 0

    @staticmethod
    def escape_latex(text):
        replacements = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%",
                        "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{",
                        "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
        return "".join(replacements.get(c, c) for c in text)

    def document_source(self):
        if not self.notes_active():
            return self.equation_text.get("1.0", "end-1c").strip(), self.renderer_var.get()
        text = self.notes.get("1.0", "end-1c").strip()
        parts = re.split(r"(\[\[image:.*?\]\]|\f)", text)
        body = []
        for part in parts:
            if part == "\f":
                body.append(r"\newpage")
            elif part.startswith("[[image:") and part.endswith("]]"):
                body.append(r"\par\includegraphics[width=0.85\linewidth,height=0.7\textheight,keepaspectratio]{" + part[8:-2] + "}\\par")
            else:
                body.append(self.escape_latex(part).replace("\n", "\\par\n"))
        return "\n".join(body), "Text + equations"

    def insert_document_page(self):
        widget = self.notes if self.notes_active() else self.equation_text
        widget.insert("insert", "\f\n" if self.notes_active() else "\n\\newpage\n")

    @staticmethod
    def stage_document_images(document, directory, image_directory=None, image_paths=()):
        from PIL import Image
        def stage(match):
            line_start = document.rfind("\n", 0, match.start()) + 1
            if re.search(r"(?<!\\)%", document[line_start:match.start()]):
                return match.group(0)  # A commented image example is not an attachment.
            reference = match.group(2)
            candidates = []
            if image_directory:
                candidates.extend((os.path.join(image_directory, reference),
                                   os.path.join(os.path.dirname(image_directory), reference)))
            candidates.append(NMRCatalog.resolve_stored_path(reference))
            # Saved attachments remain usable when metadata is edited before Update.
            for stored in image_paths:
                if os.path.basename(stored) == os.path.basename(reference):
                    candidates.append(NMRCatalog.resolve_stored_path(stored))
            if not os.path.splitext(reference)[1]:
                candidates = [candidate + extension for candidate in candidates
                              for extension in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif", ".webp")]
            path = next((candidate for candidate in candidates if os.path.isfile(candidate)), None)
            if path is None:
                raise ValueError("Image not found: " + reference +
                                 "\nUpload it using Images… and use its saved filename in \\includegraphics{...}.")
            name = "image-" + str(stage.count) + ".png"
            stage.count += 1
            with Image.open(path) as image:
                image.convert("RGB").save(os.path.join(directory, name))
            return match.group(1) + "{" + name + "}"
        stage.count = 0
        return re.sub(r"(\\includegraphics(?:\[[^\]]*\])?)\{([^{}]+)\}", stage, document)

    @staticmethod
    def pdf_page_png(pdf, page):
        with tempfile.TemporaryDirectory(prefix="pycat_page_") as directory:
            path = os.path.join(directory, "document.pdf")
            with open(path, "wb") as file:
                file.write(pdf)
            prefix = os.path.join(directory, "preview")
            result = subprocess.run([shutil.which("pdftoppm") or "pdftoppm", "-png", "-singlefile",
                "-scale-to", "1100", "-f", str(page), "-l", str(page), path, prefix],
                capture_output=True, timeout=30)
            if result.returncode:
                raise ValueError("Could not render PDF page.")
            with open(prefix + ".png", "rb") as file:
                return file.read()

    def change_preview_page(self, delta):
        if not self._preview_pdf:
            return
        page = max(1, min(self._preview_pages, self._preview_page + delta))
        if page == self._preview_page:
            return
        try:
            png = self.pdf_page_png(self._preview_pdf, page)
            self._equation_photo = tk.PhotoImage(master=self, data=base64.b64encode(png).decode("ascii"))
            self.equation_canvas.delete("all")
            self.equation_canvas.create_image(8, 8, anchor="nw", image=self._equation_photo)
            self.equation_canvas.configure(scrollregion=self.equation_canvas.bbox("all"))
            self._preview_page = page
            self.page_label.configure(text=f"Page {page} / {self._preview_pages}")
        except Exception as error:
            messagebox.showerror(APP_TITLE, str(error))

    def open_conference_website(self):
        url = self.fields["website"].get().strip()
        if self.fields["item_type"].get() not in ("Conference", "Researchers") or not url:
            messagebox.showinfo(APP_TITLE, "Select a conference or researcher and enter a website.")
            return
        if not url.startswith(("https://", "http://")):
            url = "https://" + url
        open_with_system(url)

    def _equation_modified(self, _event=None):
        if not self.equation_text.edit_modified():
            return
        self.equation_text.edit_modified(False)
        if self._preview_job is not None:
            self.after_cancel(self._preview_job)
        if not self.notes_active():
            self._preview_job = self.after(500, self.preview_equation)

    @staticmethod
    def equation_png(latex, output_format="png"):
        """Render common LaTeX math locally, without a TeX executable or shell."""
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib import rc_context

        text = latex.strip()
        if not text:
            raise ValueError("Enter text or an equation first.")
        for pattern in (r"\\\[([\s\S]*?)\\\]", r"\\\(([\s\S]*?)\\\)", r"\$\$([\s\S]*?)\$\$"):
            text = re.sub(pattern, lambda match: "$" + match.group(1).strip().replace("\n", " ") + "$", text)
        lines = text.splitlines()
        with _MATH_RENDER_LOCK, rc_context({"text.usetex": False, "mathtext.fontset": "dejavusans"}):
            fig = Figure(figsize=(6, max(1, len(lines) * 0.8)), dpi=130, facecolor="white")
            canvas = FigureCanvasAgg(fig)
            labels = []
            for index, line in enumerate(lines):
                # Unwrapped formula lines remain compatible with earlier catalog entries.
                bare_math = "$" not in line and bool(re.search(r"[=^_]|\\[A-Za-z]+", line))
                display = "$" + line + "$" if bare_math else line
                labels.append(fig.text(0.02, 1 - (index + 0.5) / len(lines),
                                       display, fontsize=20, va="center"))
            canvas.draw()  # Validate before committing an image to the preview.
            renderer = canvas.get_renderer()
            for label in labels:
                box = label.get_window_extent(renderer)
                if box.width > 12000 or box.height > 12000:
                    raise ValueError("Equation is too large to preview; split it into shorter lines.")
            output = io.BytesIO()
            fig.savefig(output, format=output_format, bbox_inches="tight", pad_inches=0.15, dpi=130)
            return output.getvalue()

    def preview_equation(self, compile_full=False):
        if self._preview_job is not None:
            self.after_cancel(self._preview_job)
            self._preview_job = None
        self._preview_generation += 1
        latex, active_renderer = self.document_source()
        self._preview_pdf = None
        self.page_label.configure(text="Page 1")
        self.equation_canvas.delete("all")
        self._equation_photo = None
        self.equation_canvas.configure(scrollregion=(0, 0, 1, 1))
        if self.fields["item_type"].get() in ("Researchers", "Websites"):
            self.equation_status.configure(text="Enter website links, descriptions, or other plain text." if self.fields["item_type"].get() == "Websites" else "Enter biography, research interests, or other plain-text notes.")
            return
        if not latex:
            self.equation_status.configure(text="Type an equation to see its preview.", foreground="#555555")
            return
        if active_renderer in ("Full LaTeX", "Text + equations"):
            if not compile_full:
                self.equation_status.configure(text="Click Preview to compile with Full LaTeX.", foreground="#555555")
                return
            if self._latex_future is not None:
                self.equation_status.configure(text="A compilation is finishing. Click Preview again shortly.", foreground="#555555")
                return
            self.equation_status.configure(text="Compiling LaTeX…", foreground="#555555")
            self._latex_future = self._latex_executor.submit(self.full_latex_png, latex, "png", active_renderer == "Text + equations",
                os.path.join(self.entry_folder(), "Images"), tuple(p for p in self.fields["image_paths"].get().split("; ") if p))
            generation = self._preview_generation
            self._latex_poll_job = self.after(100, lambda: self._poll_latex(generation))
            return
        try:
            png = self.equation_png(latex)
            self._equation_photo = tk.PhotoImage(master=self, data=base64.b64encode(png).decode("ascii"))
            self.equation_canvas.create_image(8, 8, anchor="nw", image=self._equation_photo)
            self.equation_canvas.configure(scrollregion=self.equation_canvas.bbox("all"))
            if compile_full:
                self.workspace_tabs.select(self.pdf_area)
            self.equation_status.configure(text="Preview updated. Use Add or Update to save the entry.", foreground="#27632a")
        except ImportError:
            self.equation_status.configure(text="Install equation preview support, then restart:\npython -m pip install matplotlib\nYour LaTeX text can still be saved.", foreground="#a04020")
        except Exception as error:
            self.equation_status.configure(text="Cannot preview this equation. Check the LaTeX syntax.\n" + str(error)[:240], foreground="#a04020")

    def open_images(self):
        paths = [p for p in self.fields["image_paths"].get().split("; ") if p]
        primary = self.fields["file_link"].get().strip()
        if (self.fields["item_type"].get() == "Image" and primary
                and os.path.isfile(self.resolve_stored_path(primary))):
            paths = list(dict.fromkeys([primary, *paths]))
        if not paths:
            messagebox.showinfo(APP_TITLE, "This entry has no attached images. Use Images… to add one.")
            return
        try:
            for path in paths:
                resolved = self.resolve_stored_path(path)
                if not os.path.isfile(resolved):
                    raise FileNotFoundError(path)
                open_with_system(resolved)
        except Exception as error:
            messagebox.showerror(APP_TITLE, f"Could not open the image:\n{error}")


    def update_type_controls(self, *_args):
        self._preview_generation += 1
        kind = self.fields["item_type"].get()
        common = {"item_type", "title", "section", "subsection"}
        literature = {"authors", "year", "source", "volume_issue_pages", "doi_isbn", "keywords",
                      "corresponding_author", "author_email", "file_link", "supplementary_paths",
                      "bibtex_path", "image_paths"}
        visible = common | ({"authors", "lecture_pdf_paths"} if kind == "Lecture" else
                            {"website", "place", "file_link"} if kind == "Conference" else
                            {"authors", "report_date", "image_paths", "file_link"} if kind == "Report" else
                            {"image_paths"} if kind == "Image" else
                            literature if kind in ("Paper", "Book", "Manual", "Thesis") else set())
        if kind == "Researchers":
            visible = {"item_type", "title", "website", "section", "subsection"}
        elif kind == "Websites":
            visible = common
        for key, widget in self.field_widgets.items():
            if key in visible:
                self.field_labels[key].grid()
                widget.grid()
            else:
                self.field_labels[key].grid_remove()
                widget.grid_remove()
        for key, actions in self.attachment_actions.items():
            (actions.grid if key in visible else actions.grid_remove)()
        (self.rearrange_authors_button.grid if "authors" in visible else
         self.rearrange_authors_button.grid_remove)()
        if kind == "Equation":
            self.document_tabs.select(1)
        self.field_labels["title"].configure(text="Name *" if kind == "Researchers" else "Name of conference *" if kind == "Conference" else "Title *")
        self.notes.configure(state="normal")
        if kind in ("Researchers", "Websites"):
            self.document_tabs.select(self.plain_source_tab)
            self.workspace_tabs.select(0)
            self.document_tabs.hide(self.latex_source_tab)
            self.workspace_tabs.hide(self.pdf_area)
            self.workspace_tabs.tab(0, text="Plain text")
            self.note_actions.pack_forget()
            self.equation_panel.configure(text="Websites — plain text" if kind == "Websites" else "Researcher — plain text")
            self.equation_status.configure(text="Enter website links, descriptions, or other plain text." if kind == "Websites" else "Enter biography, research interests, or other plain-text notes.")
        else:
            self.document_tabs.add(self.latex_source_tab, text="LaTeX code")
            self.workspace_tabs.add(self.pdf_area, text="LaTeX output")
            self.workspace_tabs.tab(0, text="LaTeX")
            self.note_actions.pack(fill="x")
            self.equation_panel.configure(text="Notes and rendered PDF — up to 100 A4 pages")
        equation_enabled = True
        equation_pane = str(self.equation_panel)
        if equation_enabled and equation_pane not in self.editor.panes():
            self.editor.add(self.equation_panel, weight=2)
        elif not equation_enabled and equation_pane in self.editor.panes():
            self.editor.forget(self.equation_panel)
        self.equation_text.configure(state="normal" if equation_enabled else "disabled")
        self.preview_button.configure(state="normal" if equation_enabled else "disabled")
        self.save_pdf_button.configure(state="normal" if equation_enabled and self._pdf_future is None else "disabled")
        self.open_latex_pdf_button.configure(state="normal" if equation_enabled else "disabled")

    def ensure_compact_title(self, image_path=None):
        # Every entry requires a meaningful user-supplied title.
        return self.fields["title"].get().strip()

    def _renderer_changed(self, _event=None):
        self.preview_equation()

    @staticmethod
    def full_latex_png(source, output_format="png", text_mode=False, image_directory=None, image_paths=()):
        """Compile local LaTeX and return cropped PNG pages for the Tk preview."""
        from PIL import Image, ImageChops, ImageOps
        compiler = shutil.which("pdflatex")
        converter = shutil.which("pdftoppm")
        if not compiler or (output_format == "png" and not converter):
            raise RuntimeError("Install Full LaTeX support:\nsudo apt install texlive-latex-base "
                               "texlive-latex-recommended texlive-latex-extra poppler-utils")
        source = source.strip()
        if not source:
            raise ValueError("Enter an equation first.")
        if r"\documentclass" in source:
            # Respect the declared page size and Beamer slide aspect ratio.
            document = source
        else:
            # Display environments provide their own math mode; matrix/cases need a wrapper.
            display = re.match(r"\\begin\{(?:align\*?|alignat\*?|gather\*?|multline\*?|equation\*?|flalign\*?|displaymath)\}", source)
            wrapped = source.startswith(("$", r"\[", r"\("))
            body = source if text_mode or display or wrapped else "\\[\n" + source + "\n\\]"
            document = (r"\documentclass[a4paper,12pt]{article}" + "\n" +
                        r"\usepackage[margin=12mm]{geometry}" + "\n" +
                        r"\usepackage{amsmath,amssymb,bm,graphicx}" + "\n" +
                        r"\pagestyle{empty}" + "\n" + r"\begin{document}" + "\n" +
                        body + "\n" + r"\end{document}")
        with tempfile.TemporaryDirectory(prefix="pycat_latex_") as directory:
            document = NMRCatalog.stage_document_images(document, directory, image_directory, image_paths)
            tex_path = os.path.join(directory, "equation.tex")
            with open(tex_path, "w", encoding="utf-8") as file:
                file.write(document)
            env = os.environ.copy()
            env.update({"openin_any": "p", "openout_any": "p"})
            result = subprocess.run(
                [compiler, "-no-shell-escape", "-interaction=nonstopmode", "-halt-on-error", "equation.tex"],
                cwd=directory, env=env, capture_output=True, text=True, errors="replace", timeout=120,
            )
            if result.returncode:
                log = result.stdout + result.stderr
                lines = log.splitlines()
                index = next((i for i, line in enumerate(lines) if line.startswith("!")), max(0, len(lines) - 8))
                raise ValueError("LaTeX compilation failed:\n" + "\n".join(lines[index:index + 8]))
            match = re.search(r"Output written on .*?\((\d+) pages?", result.stdout)
            pages = int(match.group(1)) if match else 1
            if pages > 100:
                raise ValueError("Document exceeds the 100 A4 page limit; shorten it before export.")
            with open(os.path.join(directory, "equation.pdf"), "rb") as file:
                pdf = file.read()
            if output_format == "pdf":
                return pdf
            return {"pdf": pdf, "pages": pages, "png": NMRCatalog.pdf_page_png(pdf, 1)}

    def _poll_latex(self, generation):
        self._latex_poll_job = None
        if not self._latex_future.done():
            self._latex_poll_job = self.after(100, lambda: self._poll_latex(generation))
            return
        future = self._latex_future
        self._latex_future = None
        if generation != self._preview_generation:
            return
        try:
            document = future.result()
            self._preview_pdf = document["pdf"]
            self._preview_page, self._preview_pages = 1, document["pages"]
            self.page_label.configure(text=f"Page 1 / {self._preview_pages}")
            png = document["png"]
            self._equation_photo = tk.PhotoImage(master=self, data=base64.b64encode(png).decode("ascii"))
            self.equation_canvas.create_image(8, 8, anchor="nw", image=self._equation_photo)
            self.equation_canvas.configure(scrollregion=self.equation_canvas.bbox("all"))
            self.workspace_tabs.select(self.pdf_area)
            self.equation_status.configure(text="PDF preview (up to 100 pages). Use Add or Update to save.", foreground="#27632a")
        except ImportError:
            self.equation_status.configure(text="Install image support: python -m pip install pillow", foreground="#a04020")
        except subprocess.TimeoutExpired:
            self.equation_status.configure(text="LaTeX preview timed out. Check or shorten the source.", foreground="#a04020")
        except Exception as error:
            self.equation_status.configure(text=str(error)[:700], foreground="#a04020")


    def save_equation_pdf(self):
        source, active_renderer = self.document_source()
        if not source:
            messagebox.showinfo(APP_TITLE, "Enter some text or an equation first.")
            return
        if self._pdf_future is not None:
            messagebox.showinfo(APP_TITLE, "A PDF export is already running.")
            return
        title = self.ensure_compact_title()
        if not title:
            messagebox.showinfo(APP_TITLE, "Enter the entry title before saving its equations PDF.")
            return
        folder = self.entry_folder()
        try:
            os.makedirs(folder, exist_ok=True)
        except OSError as error:
            messagebox.showerror(APP_TITLE, f"Could not create entry folder:\n{error}")
            return
        path = filedialog.asksaveasfilename(
            title="Save text and equations as PDF", defaultextension=".pdf", initialdir=folder,
            initialfile=self.safe_name(title, "Equation") + ("-Notes.pdf" if self.notes_active() else "-Equations.pdf"),
            filetypes=(("PDF document", "*.pdf"),),
        )
        if not path:
            return
        # Capture the current editor content; never export an outdated preview image.
        renderer = active_renderer
        self._export_column = "notes_pdf_path" if self.notes_active() else "equation_pdf_path"
        self._export_entry = self.selected_id
        self._export_title = self.fields["title"].get()
        self._pdf_future = self._latex_executor.submit(self.render_pdf_to_file, source, renderer, path,
            os.path.join(self.entry_folder(), "Images"), tuple(p for p in self.fields["image_paths"].get().split("; ") if p))
        self.save_pdf_button.configure(state="disabled")
        self.equation_status.configure(text="Creating PDF…", foreground="#555555")
        self._pdf_poll_job = self.after(100, self._poll_pdf_export)

    @staticmethod
    def render_pdf_to_file(source, renderer, path, image_directory=None, image_paths=()):
        if renderer == "Quick preview":
            pdf = NMRCatalog.equation_png(source, output_format="pdf")
        else:
            pdf = NMRCatalog.full_latex_png(source, output_format="pdf", text_mode=renderer == "Text + equations",
                image_directory=image_directory, image_paths=image_paths)
        # Replace only after rendering succeeds; keep an existing PDF on compiler errors.
        descriptor, temporary = tempfile.mkstemp(prefix=".pycat_pdf_", suffix=".pdf",
                                                dir=os.path.dirname(os.path.abspath(path)))
        try:
            with os.fdopen(descriptor, "wb") as file:
                file.write(pdf)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return path

    def _poll_pdf_export(self):
        self._pdf_poll_job = None
        if not self._pdf_future.done():
            self._pdf_poll_job = self.after(100, self._poll_pdf_export)
            return
        future = self._pdf_future
        self._pdf_future = None
        self.save_pdf_button.configure(state="normal" if self.fields["item_type"].get() in PDF_TYPES else "disabled")
        try:
            path = future.result()
            stored = self.portable_stored_path(path)
            if self.selected_id == self._export_entry and self.fields["title"].get() == self._export_title:
                self.fields[self._export_column].set(stored)
            self.equation_status.configure(text="PDF saved. Use Add or Update to save the editable catalog entry.", foreground="#27632a")
            messagebox.showinfo(APP_TITLE, "LaTeX PDF saved and attached separately:\n" + path)
        except Exception as error:
            self.equation_status.configure(text="PDF export failed.", foreground="#a04020")
            messagebox.showerror(APP_TITLE, "Could not save the PDF:\n" + str(error))

    def expected_equation_pdf(self, section, subsection, corresponding_author, authors, title, item_type):
        """Return the standard equation-PDF path used by older and current entries."""
        folder = self.entry_folder_for(
            section, subsection, self.folder_author(corresponding_author, authors), title, item_type,
        )
        return os.path.join(folder, self.safe_name(title, "Equation") + "-Equations.pdf")

    def open_current_equation_pdf(self):
        """Open the separate equation PDF attached to the form being edited."""
        if self.fields["item_type"].get() not in PDF_TYPES:
            messagebox.showinfo(APP_TITLE, "LaTeX PDFs are available for papers, books, manuals, theses, notes, and equations.")
            return
        stored = self.fields["notes_pdf_path" if self.notes_active() else "equation_pdf_path"].get().strip()
        if self.notes_active() and not stored:
            messagebox.showinfo(APP_TITLE, "Save the Notes PDF first.")
            return
        path = self.resolve_stored_path(stored)
        if self.notes_active() and not os.path.isfile(path):
            messagebox.showinfo(APP_TITLE, "Saved Notes PDF was not found. Save it again.")
            return
        if not stored or not os.path.isfile(path):
            path = self.expected_equation_pdf(
                self.fields["section"].get(), self.fields["subsection"].get(),
                self.fields["corresponding_author"].get(), self.fields["authors"].get(),
                self.fields["title"].get(), self.fields["item_type"].get(),
            )
        if not os.path.isfile(path):
            messagebox.showinfo(APP_TITLE, "No saved LaTeX PDF was found. Use Save PDF… first.")
            return
        self.fields["notes_pdf_path" if self.notes_active() else "equation_pdf_path"].set(self.portable_stored_path(path))
        try:
            open_with_system(path)
        except Exception as error:
            messagebox.showerror(APP_TITLE, f"Could not open the LaTeX PDF:\n{error}")

    def open_selected_equation_pdf(self):
        """Open the equation PDF for the selected catalog record, independently of its main PDF."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo(APP_TITLE, "Select an entry first.")
            return
        entry_id = int(selection[0])
        row = self.conn.execute("SELECT * FROM literature WHERE id=?", (entry_id,)).fetchone()
        if row["item_type"] not in PDF_TYPES:
            messagebox.showinfo(APP_TITLE, "The selected entry does not support a LaTeX PDF.")
            return
        stored = (row["equation_pdf_path"] or "").strip()
        path = self.resolve_stored_path(stored)
        if not stored or not os.path.isfile(path):
            path = self.expected_equation_pdf(
                row["section"], row["subsection"], row["corresponding_author"],
                row["authors"], row["title"], row["item_type"],
            )
        if not os.path.isfile(path):
            messagebox.showinfo(APP_TITLE, "This entry has no saved LaTeX PDF.")
            return
        portable = self.portable_stored_path(path)
        if portable != stored:
            self.conn.execute("UPDATE literature SET equation_pdf_path=? WHERE id=?", (portable, entry_id))
            self.conn.commit()
            self.sync_csv()
        try:
            open_with_system(path)
        except Exception as error:
            messagebox.showerror(APP_TITLE, f"Could not open the LaTeX PDF:\n{error}")

    def values_from_form(self):
        values = {name: variable.get().strip() for name, variable in self.fields.items()}
        kind = values["item_type"]
        if kind == "Lecture":
            for key in ("year", "source", "volume_issue_pages", "doi_isbn", "keywords",
                        "corresponding_author", "author_email", "file_link", "supplementary_paths",
                        "bibtex_path"):
                values[key] = ""
        elif kind in ("Note", "Image", "Equation"):
            for key in ("authors", "year", "source", "volume_issue_pages", "doi_isbn", "keywords",
                        "corresponding_author", "author_email", "supplementary_paths", "bibtex_path"):
                values[key] = ""
            if kind != "Image":
                values["file_link"] = ""
        else:
            values["lecture_pdf_paths"] = ""
        values["equation_latex"] = self.equation_text.get("1.0", "end-1c").strip()
        values["equation_renderer"] = self.renderer_var.get()
        values["notes"] = self.notes.get("1.0", "end").strip()
        if kind in ("Researchers", "Websites"):
            keep = {"item_type", "title", "notes", "section", "subsection"}
            if kind == "Researchers":
                keep.add("website")
            for key in values:
                if key not in keep:
                    values[key] = ""
        return values

    def validate_entry_data(self, data):
        """Enforce the metadata needed for consistent search and folder organization."""
        required = (
            ("title", "Please enter a title."),
            ("section", "Please enter a section / field."),
            ("subsection", "Please enter a subsection."),
        )
        if data["item_type"] in ("Conference", "Report"):
            required = required[:1]
        for key, message in required:
            if not data.get(key):
                messagebox.showwarning(APP_TITLE, message)
                return False
        if data["item_type"] in ("Paper", "Book", "Manual", "Thesis", "Lecture", "Report") and not data.get("authors"):
            messagebox.showwarning(APP_TITLE, "Please enter at least one author.")
            return False
        if data["item_type"] == "Report" and data.get("report_date"):
            from datetime import date
            try:
                date.fromisoformat(data["report_date"])
            except ValueError:
                messagebox.showwarning(APP_TITLE, "Use a valid date: YYYY-MM-DD.")
                return False
        if data["item_type"] == "Equation" and not data["equation_latex"]:
            messagebox.showwarning(APP_TITLE, "Please enter a LaTeX equation.")
            return False
        if data["item_type"] == "Note" and not (data["notes"] or data["equation_latex"]):
            messagebox.showwarning(APP_TITLE, "Please enter a note or an equation.")
            return False
        if data["item_type"] == "Image" and not (data["file_link"] or data["image_paths"]):
            messagebox.showwarning(APP_TITLE, "Please select an image using Images…")
            return False
        return True

    def add_item(self):
        data = self.values_from_form()
        if not self.validate_entry_data(data):
            return
        try:
            data = self.organize_entry_data(data)
        except OSError as error:
            messagebox.showerror(APP_TITLE, f"Could not store entry files:\n{error}")
            return
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
        if not self.validate_entry_data(data):
            return
        try:
            data = self.organize_entry_data(data)
        except OSError as error:
            messagebox.showerror(APP_TITLE, f"Could not store entry files:\n{error}")
            return
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
        self.notes.configure(state="normal")
        self.equation_text.configure(state="normal")
        self.notes.delete("1.0", "end")
        self.equation_text.delete("1.0", "end")
        self.renderer_var.set("Text + equations")
        self.update_type_controls()
        self.preview_equation()
        for selected in self.tree.selection():
            self.tree.selection_remove(selected)

    def refresh_table(self):
        self.update_filter_dropdowns()
        query = self.search_var.get().strip()
        item_filter = self.filter_var.get()
        if item_filter == "Lecture notes":
            item_filter = "Lecture"
        sql = "SELECT * FROM literature WHERE 1=1"
        parameters = []
        words = list(dict.fromkeys(normalize_search_text(query).split()))
        if words:
            field_map = {
                "Title": ("title",), "Keywords": ("keywords",), "Author": ("authors", "corresponding_author"),
                "Section": ("section",), "Subsection": ("subsection",),
                "All fields": ("title", "authors", "corresponding_author", "author_email", "source", "doi_isbn", "keywords", "section", "subsection", "notes", "equation_latex", "website", "place", "report_date"),
            }
            searchable = field_map[self.search_by_var.get()]
            # Every query word must occur in a searchable field, in any order.
            # instr keeps symbols such as % and _ from acting as SQL wildcards.
            for word in words:
                sql += " AND (" + " OR ".join(f"instr(pycat_search({field}), ?) > 0" for field in searchable) + ")"
                parameters.extend([word] * len(searchable))
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
            self.tree.insert("", "end", iid=str(row["id"]), values=("Lecture notes" if row["item_type"] == "Lecture" else row["item_type"], row["title"], row["authors"], row["year"], row["section"], row["subsection"], row["source"]))
        self.count_label.configure(text=f"{len(rows)} item{'s' if len(rows) != 1 else ''}")

    def update_entry_suggestions(self, *_args):
        """Suggest saved categories while allowing new text and preserving edits."""
        sections = [row[0] for row in self.conn.execute(
            "SELECT DISTINCT section FROM literature "
            "WHERE trim(coalesce(section, '')) != '' ORDER BY section COLLATE NOCASE")]
        selected = self.fields["section"].get().strip()
        if selected:
            rows = self.conn.execute(
                "SELECT DISTINCT subsection FROM literature WHERE section=? "
                "AND trim(coalesce(subsection, '')) != '' ORDER BY subsection COLLATE NOCASE",
                (selected,))
        else:
            rows = self.conn.execute(
                "SELECT DISTINCT subsection FROM literature "
                "WHERE trim(coalesce(subsection, '')) != '' ORDER BY subsection COLLATE NOCASE")
        self.field_widgets["section"].configure(values=sections)
        self.field_widgets["subsection"].configure(values=[row[0] for row in rows])

    def update_filter_dropdowns(self):
        self.update_entry_suggestions()
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
            self.notes.configure(state="normal")
            self.equation_text.configure(state="normal")
            self.notes.delete("1.0", "end")
            self.notes.insert("1.0", row["notes"] or "")
            self.equation_text.delete("1.0", "end")
            self.equation_text.insert("1.0", row["equation_latex"] or "")
            self.renderer_var.set(row["equation_renderer"] or "Quick preview")
            self.update_type_controls()
            self.preview_equation()

    def browse_file(self):
        path = filedialog.askopenfilename(
            title="Select a PDF document",
            filetypes=(("PDF documents", "*.pdf"), ("All files", "*.*")),
        )
        if path:
            self.attach_pdf(path)

    def browse_lecture_pdfs(self):
        paths = filedialog.askopenfilenames(
            title="Select lecture PDFs", filetypes=(("PDF documents", "*.pdf"),))
        if paths:
            self.attach_lecture_pdfs(paths)

    def attach_lecture_pdfs(self, paths):
        if self.fields["item_type"].get() != "Lecture":
            return 0
        if not self.fields["title"].get().strip():
            messagebox.showinfo(APP_TITLE, "Enter the lecture title before attaching PDFs.")
            return 0
        valid = [os.path.abspath(os.path.expanduser(p)) for p in paths
                 if os.path.isfile(os.path.expanduser(p)) and p.lower().endswith(".pdf")]
        if not valid:
            messagebox.showwarning(APP_TITLE, "Select one or more PDF files.")
            return 0
        try:
            # Keep the source filenames so multiple lectures remain identifiable.
            stored = [self.portable_stored_path(self.copy_to_entry(p, self.entry_folder())) for p in valid]
            existing = [p for p in self.fields["lecture_pdf_paths"].get().split("; ") if p]
            self.fields["lecture_pdf_paths"].set("; ".join(dict.fromkeys([*existing, *stored])))
            if len(valid) != len(paths):
                messagebox.showinfo(APP_TITLE, f"Added {len(valid)} PDF(s); skipped non-PDF items.")
            return len(valid)
        except OSError as error:
            messagebox.showerror(APP_TITLE, f"Could not attach lecture PDFs:\n{error}")
            return 0

    def drop_lecture_pdfs(self, event):
        try:
            paths = list(self.tk.splitlist(event.data))
        except (tk.TclError, TypeError):
            paths = []
        self.attach_lecture_pdfs(paths)
        return "break"

    def attach_pdf(self, path):
        """Validate, copy and attach one local PDF to the current entry."""
        path = os.path.abspath(os.path.expanduser(path))
        if not os.path.isfile(path):
            messagebox.showwarning(APP_TITLE, "The dropped item is not a file.")
            return False
        if os.path.splitext(path)[1].lower() != ".pdf":
            messagebox.showwarning(APP_TITLE, "Only PDF files can be attached here.")
            return False
        if self.fields["item_type"].get() in ("Equation", "Image", "Note"):
            messagebox.showinfo(APP_TITLE, "PDF attachments are available for papers, books, manuals, and theses.")
            return False
        if not self.fields["title"].get().strip():
            messagebox.showinfo(APP_TITLE, "Enter the title before attaching its PDF.")
            return False
        try:
            stored_path = self.store_document(path, "PDF")
            self.fields["file_link"].set(stored_path)
            return True
        except OSError as error:
            messagebox.showerror(APP_TITLE, f"Could not store the PDF:\n{error}")
            return False

    def drop_pdf(self, event):
        """Accept the first PDF from a desktop file-manager drop."""
        try:
            paths = list(self.tk.splitlist(event.data))
        except (tk.TclError, TypeError):
            paths = []
        if not paths:
            messagebox.showwarning(APP_TITLE, "No file was found in the drop.")
            return "break"
        if len(paths) > 1:
            messagebox.showinfo(APP_TITLE, "Only one primary PDF can be attached. Using the first dropped file.")
        self.attach_pdf(paths[0])
        return "break"

    def library_root(self):
        """The portable library always travels beside this Python file."""
        return os.path.join(APP_DIRECTORY, "NMR_Library")

    @staticmethod
    def resolve_stored_path(path):
        """Resolve a portable database path against the PyCat folder."""
        path = (path or "").strip()
        if not path or path.startswith(("http://", "https://")):
            return path
        expanded = os.path.expanduser(path)
        foreign_windows_path = os.name != "nt" and bool(re.match(r"^[A-Za-z]:[\\/]", expanded))
        foreign_posix_path = os.name == "nt" and expanded.startswith("/")
        if foreign_windows_path or foreign_posix_path:
            return expanded
        if os.path.isabs(expanded):
            return os.path.normpath(expanded)
        return os.path.normpath(os.path.join(APP_DIRECTORY, *expanded.replace("\\", "/").split("/")))

    @staticmethod
    def portable_stored_path(path):
        """Store paths inside the PyCat folder with forward slashes on every OS."""
        path = (path or "").strip()
        if not path or path.startswith(("http://", "https://")):
            return path
        expanded = os.path.expanduser(path)
        foreign_windows_path = os.name != "nt" and bool(re.match(r"^[A-Za-z]:[\\/]", expanded))
        foreign_posix_path = os.name == "nt" and expanded.startswith("/")
        if foreign_windows_path or foreign_posix_path:
            return path
        absolute = NMRCatalog.resolve_stored_path(expanded)
        try:
            relative = os.path.relpath(absolute, APP_DIRECTORY)
        except ValueError:  # Different Windows drives cannot be made relative.
            return absolute
        if relative == os.pardir or relative.startswith(os.pardir + os.sep):
            return absolute
        return relative.replace(os.sep, "/")

    def make_existing_paths_portable(self):
        """Convert already-local absolute paths without moving or deleting files."""
        columns = ("file_link", "lecture_pdf_paths", "bibtex_path", "supplementary_paths", "image_paths", "notes_path", "equation_pdf_path", "notes_pdf_path")
        rows = self.conn.execute("SELECT id, " + ", ".join(columns) + " FROM literature").fetchall()
        with self.conn:
            for row in rows:
                updates = {}
                for key in columns:
                    multiple = key in ("lecture_pdf_paths", "supplementary_paths", "image_paths")
                    values = (row[key] or "").split("; ") if multiple else [row[key] or ""]
                    converted = [self.portable_stored_path(value) for value in values]
                    new_value = "; ".join(converted) if multiple else converted[0]
                    if new_value != (row[key] or ""):
                        updates[key] = new_value
                if updates:
                    assignments = ", ".join(f"{key}=?" for key in updates)
                    self.conn.execute(f"UPDATE literature SET {assignments} WHERE id=?",
                                      (*updates.values(), row["id"]))

    @staticmethod
    def safe_name(value, fallback):
        value = unicodedata.normalize("NFC", value or "")
        value = re.sub(r"[^\w .()-]+", "_", value, flags=re.UNICODE).strip(" ._")
        value = value[:120] or fallback
        reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
                    *(f"LPT{i}" for i in range(1, 10))}
        if value.split(".", 1)[0].upper() in reserved:
            value = "_" + value
        return value

    def ensure_category_folders(self):
        # Entry folders are created when needed; do not recreate empty categories.
        os.makedirs(self.library_root(), exist_ok=True)

    def unused_library_folders(self):
        """Return maximal unused subtrees, preserving saved entries and draft uploads."""
        root = os.path.abspath(self.library_root())
        if os.path.islink(root) or (hasattr(os.path, "isjunction") and os.path.isjunction(root)):
            raise OSError("Cleanup is unavailable when NMR_Library is a symbolic link.")
        if not os.path.isdir(root):
            return []
        root_key = os.path.normcase(root)

        def path_key(path):
            return os.path.normcase(os.path.abspath(path))

        def inside(path, parent):
            try:
                return os.path.commonpath((path, parent)) == parent
            except ValueError:
                return False

        keep = set()
        rows = [dict(row) for row in self.conn.execute("SELECT * FROM literature")]
        # Files are copied immediately on upload, before Add/Update is pressed.
        draft = {key: var.get() for key, var in self.fields.items()}
        if draft.get("title", "").strip():
            rows.append(draft)
        columns = ("file_link", "lecture_pdf_paths", "bibtex_path", "supplementary_paths",
                   "image_paths", "notes_path", "equation_pdf_path", "notes_pdf_path")
        for row in rows:
            canonical = self.entry_folder_for(row.get("section"), row.get("subsection"),
                self.folder_author(row.get("corresponding_author"), row.get("authors")),
                row.get("title"), row.get("item_type"))
            keep.add(path_key(canonical))
            for key in columns:
                paths = (row.get(key) or "").split("; ") if key in (
                    "lecture_pdf_paths", "supplementary_paths", "image_paths") else [row.get(key) or ""]
                for stored in paths:
                    if not stored or stored.startswith(("http://", "https://")):
                        continue
                    resolved = self.resolve_stored_path(stored)
                    for reference in (resolved, os.path.realpath(resolved)):
                        parent = path_key(os.path.dirname(reference))
                        if inside(parent, root_key):
                            keep.add(parent)
        candidates = []

        def scan(folder):
            with os.scandir(folder) as entries:
                for entry in entries:
                    # Never follow symbolic links or Windows directory junctions.
                    if entry.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(entry.path)):
                        continue
                    if not entry.is_dir(follow_symlinks=False):
                        continue
                    key = path_key(entry.path)
                    if any(inside(key, saved) for saved in keep):
                        continue
                    if any(inside(saved, key) for saved in keep):
                        scan(entry.path)
                    else:
                        candidates.append(entry.path)

        scan(root)
        return sorted(candidates, key=str.casefold)

    def preview_unused_folders(self):
        try:
            candidates = self.unused_library_folders()
        except (OSError, sqlite3.Error) as error:
            messagebox.showerror(APP_TITLE, f"Could not check library folders:\n{error}")
            return
        if not candidates:
            messagebox.showinfo(APP_TITLE, "No unused library folders were found.")
            return
        dialog = tk.Toplevel(self)
        dialog.title("Delete unused folders — review")
        dialog.geometry("820x480")
        dialog.transient(self)
        panel = ttk.Frame(dialog, padding=12)
        panel.pack(fill="both", expand=True)
        ttk.Label(panel, text=(f"Found {len(candidates)} unused folder(s) in NMR_Library.\n"
            "The complete catalog and current upload form were checked.\n"
            "Saved entry folders and referenced attachment folders will be kept.\n"
            "The listed folders and ALL their contents will be permanently deleted."),
            wraplength=760).pack(fill="x", pady=(0, 10))
        listing = ttk.Frame(panel)
        listing.pack(fill="both", expand=True)
        text = tk.Text(listing, wrap="word", width=70, height=15)
        scroll = ttk.Scrollbar(listing, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        text.pack(fill="both", expand=True)
        text.insert("1.0", "\n".join(os.path.relpath(path, self.library_root()) for path in candidates))
        text.configure(state="disabled")
        actions = ttk.Frame(panel)
        actions.pack(fill="x", pady=(10, 0))

        def delete_listed():
            # Recheck protection immediately before removing only reviewed folders.
            try:
                current = set(self.unused_library_folders())
            except (OSError, sqlite3.Error) as error:
                messagebox.showerror(APP_TITLE, f"Could not recheck folders:\n{error}", parent=dialog)
                return
            deleted, failed, skipped = 0, [], 0
            for folder in candidates:
                if folder not in current or os.path.islink(folder):
                    skipped += 1
                    continue
                try:
                    shutil.rmtree(folder)
                    deleted += 1
                except OSError as error:
                    failed.append(f"{os.path.relpath(folder, self.library_root())}: {error}")
            dialog.destroy()
            report = f"Deleted {deleted} unused folder(s). Catalog entries were kept."
            if skipped:
                report += f"\nSkipped {skipped} folder(s) that changed after review."
            if failed:
                messagebox.showwarning(APP_TITLE, report + "\nCould not delete:\n" + "\n".join(failed))
            else:
                messagebox.showinfo(APP_TITLE, report)

        ttk.Button(actions, text="Cancel", command=dialog.destroy).pack(side="right")
        ttk.Button(actions, text="Delete listed folders permanently", command=delete_listed).pack(side="right", padx=6)
        dialog.grab_set()

    @staticmethod
    def folder_author(corresponding_author, authors):
        """Prefer the corresponding author; preserve commas inside individual names."""
        corresponding = (corresponding_author or "").strip()
        if corresponding:
            return corresponding
        names = re.split(r";|\n|\s+and\s+", authors or "", flags=re.IGNORECASE)
        return next((name.strip() for name in names if name.strip()), "")

    def entry_folder(self):
        return self.entry_folder_for(
            self.fields["section"].get(), self.fields["subsection"].get(),
            self.folder_author(self.fields["corresponding_author"].get(), self.fields["authors"].get()),
            self.fields["title"].get(), self.fields["item_type"].get(),
        )

    def entry_folder_for(self, section, subsection, author, title, item_type="Paper"):
        author = self.safe_name(author, "Unknown author")[:40]
        title = self.safe_name(title, "Untitled")[:70]
        return os.path.join(
            self.library_root(), CATEGORY_FOLDERS.get(item_type, "Papers"),
            self.safe_name(section, "Unclassified")[:45],
            self.safe_name(subsection, "General")[:45],
            f"{author}-{title}",
        )

    def write_notes_file(self, notes, section=None, subsection=None, author=None, title=None, item_type="Paper"):
        if section is None:
            folder = self.entry_folder()
        else:
            folder = self.entry_folder_for(section, subsection, author, title, item_type)
        os.makedirs(folder, exist_ok=True)
        destination = os.path.join(folder, "Notes.txt")
        with open(destination, "w", encoding="utf-8") as file:
            file.write(notes or "")
            if notes and not notes.endswith("\n"):
                file.write("\n")
        return self.portable_stored_path(destination)

    @staticmethod
    def copy_to_entry(source, folder):
        """Copy without removing originals; reuse identical files on repeated organization."""
        source = NMRCatalog.resolve_stored_path(source)
        os.makedirs(folder, exist_ok=True)
        name = os.path.basename(source)
        base, extension = os.path.splitext(name)
        destination = os.path.join(folder, name)
        counter = 2
        while os.path.exists(destination):
            if os.path.samefile(source, destination) or filecmp.cmp(source, destination, shallow=False):
                return destination
            destination = os.path.join(folder, f"{base}_{counter}{extension}")
            counter += 1
        shutil.copy2(source, destination)
        return destination

    def organize_entry_data(self, data):
        data = dict(data)
        author = self.folder_author(data.get("corresponding_author"), data.get("authors"))
        folder = self.entry_folder_for(data.get("section"), data.get("subsection"),
                                      author, data.get("title"), data.get("item_type"))
        os.makedirs(folder, exist_ok=True)
        for key in ("file_link", "lecture_pdf_paths", "bibtex_path", "supplementary_paths", "image_paths", "equation_pdf_path", "notes_pdf_path"):
            multiple = key in ("lecture_pdf_paths", "supplementary_paths", "image_paths")
            paths = (data.get(key) or "").split("; ") if multiple else [data.get(key) or ""]
            stored = []
            for path in paths:
                resolved = self.resolve_stored_path(path)
                if path and os.path.isfile(resolved):
                    old_path = path
                    target_folder = os.path.join(folder, "Images") if key == "image_paths" else folder
                    os.makedirs(target_folder, exist_ok=True)
                    path = self.portable_stored_path(self.copy_to_entry(resolved, target_folder))
                    if key == "image_paths" and old_path != path:
                        for content_key in ("notes", "equation_latex"):
                            data[content_key] = (data.get(content_key) or "").replace(old_path, path)
                stored.append(path)
            data[key] = "; ".join(stored) if multiple else stored[0]
        # Keep any notes edited externally, as well as catalog notes.
        old_notes = data.get("notes_path")
        resolved_notes = self.resolve_stored_path(old_notes)
        if old_notes and os.path.isfile(resolved_notes):
            data["notes_path"] = self.portable_stored_path(
                self.copy_to_entry(resolved_notes, folder)
            )
        else:
            data["notes_path"] = self.write_notes_file(data.get("notes", ""),
                data.get("section") or "", data.get("subsection"), author,
                data.get("title"), data.get("item_type"))
        return data

    def organize_existing_files(self):
        """Reorganize stored attachments and persist their new paths together."""
        try:
            self.ensure_category_folders()
            rows = self.conn.execute("SELECT * FROM literature").fetchall()
            changed = 0
            missing = 0
            columns = ("file_link", "lecture_pdf_paths", "bibtex_path", "supplementary_paths", "image_paths", "notes_path", "equation_pdf_path", "notes_pdf_path")
            with self.conn:
                for row in rows:
                    for key in columns:
                        paths = (row[key] or "").split("; ") if key in ("lecture_pdf_paths", "supplementary_paths", "image_paths") else [row[key] or ""]
                        missing += sum(bool(path) and not path.startswith(("https://", "http://"))
                                       and not os.path.isfile(self.resolve_stored_path(path)) for path in paths)
                    data = self.organize_entry_data(dict(row))
                    self.conn.execute("UPDATE literature SET " + ", ".join(f"{key}=?" for key in columns) + " WHERE id=?",
                                      (*[data[key] for key in columns], row["id"]))
                    changed += 1
            self.sync_csv()
            self.clear_form()
            self.refresh_table()
            messagebox.showinfo(APP_TITLE, f"Organized {changed} entries into category / section / subsection / corresponding author-title.\n"
                                f"Original files were kept. Missing file references: {missing}.")
        except (OSError, sqlite3.Error) as error:
            messagebox.showerror(APP_TITLE, f"Could not finish organizing files. Original files were kept.\n{error}")

    def store_document(self, source, kind="Document"):
        source = os.path.abspath(os.path.expanduser(source))
        destination_dir = self.entry_folder()
        if kind == "Image":
            destination_dir = os.path.join(destination_dir, "Images")
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
        return self.portable_stored_path(destination)


    def paste_bibtex_attachment(self):
        dialog = tk.Toplevel(self)
        dialog.title("Paste BibTeX / RIS")
        dialog.geometry("760x520")
        dialog.minsize(520, 360)
        dialog.transient(self)
        panel = ttk.Frame(dialog, padding=12)
        panel.pack(fill="both", expand=True)
        ttk.Label(panel, text="Paste BibTeX or RIS below. Fill Form extracts metadata; Save citation attaches the original text.",
                  wraplength=650).pack(anchor="w", pady=(0, 8))

        def paste():
            try:
                editor.insert("insert", self.clipboard_get())
            except tk.TclError:
                messagebox.showinfo(APP_TITLE, "The clipboard contains no text.", parent=dialog)

        def save():
            raw = editor.get("1.0", "end-1c")
            if not raw.strip():
                messagebox.showwarning(APP_TITLE, "Paste some BibTeX or RIS first.", parent=dialog)
                return
            if not self.fields["title"].get().strip():
                messagebox.showwarning(APP_TITLE, "Enter the entry title first, then paste its citation.", parent=dialog)
                return
            try:
                path = self.store_pasted_bibtex(raw)
                self.fields["bibtex_path"].set(path)
            except OSError as error:
                messagebox.showerror(APP_TITLE, f"Could not save the citation:\n{error}", parent=dialog)
                return
            dialog.destroy()
            messagebox.showinfo(APP_TITLE, "Citation file attached. Click Add or Update to save the catalog entry.")

        # Keep actions above the expanding editor so they remain visible on
        # small screens and with large desktop font/scaling settings.
        buttons = ttk.Frame(panel)
        buttons.pack(fill="x", pady=(0, 10))
        ttk.Button(buttons, text="Paste from clipboard", command=paste).pack(side="left")
        ttk.Button(buttons, text="Fill Form", command=lambda: self.fill_form_from_bibtex_text(
            editor.get("1.0", "end-1c"), parent=dialog
        )).pack(side="left", padx=5)
        ttk.Button(buttons, text="Save citation", command=save).pack(side="right")
        ttk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="right", padx=5)

        body = ttk.Frame(panel)
        body.pack(fill="both", expand=True)
        editor = tk.Text(body, wrap="none", undo=True, font=("Courier", 11), width=70, height=18)
        vertical = ttk.Scrollbar(body, orient="vertical", command=editor.yview)
        horizontal = ttk.Scrollbar(body, orient="horizontal", command=editor.xview)
        editor.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        editor.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)

        dialog.grab_set()
        editor.focus_set()

    def store_pasted_bibtex(self, text):
        # Preserve pasted braces, accents, commands and line breaks verbatim.
        with tempfile.TemporaryDirectory(prefix="pycat_bib_") as directory:
            source = os.path.join(directory, "reference.ris" if self.is_ris(text) else "reference.bib")
            with open(source, "w", encoding="utf-8", newline="") as file:
                file.write(text)
            return self.store_document(source, "BibTeX")

    def rearrange_authors(self):
        """Convert BibTeX 'Family, Given' names to 'Given Family' in the form."""
        authors = self.fields["authors"].get()
        if not authors.strip():
            messagebox.showinfo(APP_TITLE, "Enter or import authors first.")
            return
        names = re.split(r"\s*;\s*|\s+and\s+|\n+", authors, flags=re.IGNORECASE)
        rearranged = []
        for name in names:
            name = name.strip()
            if not name:
                continue
            parts = [part.strip() for part in name.split(",")]
            if len(parts) == 2 and all(parts):
                name = f"{parts[1]} {parts[0]}"
            elif len(parts) == 3 and all(parts):
                # BibTeX also allows 'Family, Suffix, Given' (e.g. Smith, Jr, John).
                name = f"{parts[2]} {parts[0]} {parts[1]}"
            rearranged.append(name)
        self.fields["authors"].set("; ".join(rearranged))

    def browse_bibtex_attachment(self):
        path = filedialog.askopenfilename(title="Attach BibTeX / RIS", filetypes=(("Citation files", "*.bib *.bibtex *.ris"), ("All files", "*.*")))
        if path:
            self.attach_bibtex_file(path)

    def attach_bibtex_file(self, path):
        """Validate, attach and optionally parse one local BibTeX or RIS file."""
        path = os.path.abspath(os.path.expanduser(path))
        if not os.path.isfile(path):
            messagebox.showwarning(APP_TITLE, "The citation item is not a file.")
            return False
        if os.path.splitext(path)[1].lower() not in (".bib", ".bibtex", ".ris"):
            messagebox.showwarning(APP_TITLE, "Supported citation files: .bib, .bibtex and .ris.")
            return False
        try:
            self.fields["bibtex_path"].set(self.store_document(path, "BibTeX"))
            with open(path, encoding="utf-8-sig", errors="replace") as file:
                bibtex_text = file.read()
            if messagebox.askyesno(
                APP_TITLE, "Citation file attached. Fill the form from its metadata now?",
                default=messagebox.YES,
            ):
                self.fill_form_from_bibtex_text(bibtex_text)
            return True
        except OSError as error:
            messagebox.showerror(APP_TITLE, f"Could not store the citation file:\n{error}")
            return False

    def drop_bibtex(self, event):
        """Accept the first .bib, .bibtex or .ris file from a desktop file-manager drop."""
        try:
            paths = list(self.tk.splitlist(event.data))
        except (tk.TclError, TypeError):
            paths = []
        if not paths:
            messagebox.showwarning(APP_TITLE, "No citation file was found in the drop.")
            return "break"
        if len(paths) > 1:
            messagebox.showinfo(APP_TITLE, "Only one citation attachment is supported. Using the first dropped file.")
        self.attach_bibtex_file(paths[0])
        return "break"

    def browse_supplementary(self):
        paths = filedialog.askopenfilenames(
            title="Attach supplementary files",
            filetypes=(("Documents", "*.pdf *.doc *.docx *.xls *.xlsx *.csv *.txt *.zip"), ("All files", "*.*")),
        )
        if paths:
            self.attach_supplementary_files(paths)

    def attach_supplementary_files(self, paths):
        """Copy one or more local files and retain existing supplementary attachments."""
        valid = []
        skipped = []
        for path in paths:
            path = os.path.abspath(os.path.expanduser(path))
            if os.path.isfile(path):
                valid.append(path)
            else:
                skipped.append(path)
        if not valid:
            messagebox.showwarning(APP_TITLE, "No valid supplementary files were selected or dropped.")
            return 0
        try:
            stored = [self.store_document(path, "Supplementary") for path in valid]
            existing = [p for p in self.fields["supplementary_paths"].get().split("; ") if p]
            self.fields["supplementary_paths"].set("; ".join(dict.fromkeys([*existing, *stored])))
            if skipped:
                messagebox.showinfo(
                    APP_TITLE,
                    f"Added {len(stored)} supplementary file(s). Skipped {len(skipped)} item(s) that were not files.",
                )
            return len(stored)
        except OSError as error:
            messagebox.showerror(APP_TITLE, f"Could not store the supplementary files:\n{error}")
            return 0

    def drop_supplementary(self, event):
        """Accept multiple supplementary files from a desktop file-manager drop."""
        try:
            paths = list(self.tk.splitlist(event.data))
        except (tk.TclError, TypeError):
            paths = []
        if not paths:
            messagebox.showwarning(APP_TITLE, "No files were found in the drop.")
            return "break"
        self.attach_supplementary_files(paths)
        return "break"

    def browse_images(self):
        paths = filedialog.askopenfilenames(
            title="Attach images", filetypes=(("Image files", "*.png *.jpg *.jpeg *.tif *.tiff *.bmp *.gif *.webp"), ("All files", "*.*"))
        )
        if paths:
            self.attach_image_files(paths)

    def copy_image_from_clipboard(self):
        """Attach a copied image as a PNG through the existing image storage path."""
        if not self.fields["title"].get().strip():
            messagebox.showinfo(APP_TITLE, "Enter the entry title before copying an image.")
            return 0
        try:
            from PIL import Image, ImageGrab
        except ImportError:
            messagebox.showerror(APP_TITLE, "Install clipboard image support in your PyCat environment:\npython -m pip install --upgrade pillow")
            return 0
        try:
            content = ImageGrab.grabclipboard()
            if isinstance(content, list):
                # Windows Explorer may place copied image filenames on the clipboard.
                return self.attach_image_files(content)
            if not isinstance(content, Image.Image):
                messagebox.showinfo(APP_TITLE, "The clipboard contains no image. Copy an image or screenshot, then try again.")
                return 0
            with tempfile.TemporaryDirectory(prefix="pycat_clipboard_") as directory:
                path = os.path.join(directory, "clipboard-image.png")
                if content.mode not in ("RGB", "RGBA", "L", "LA", "P", "1", "I", "I;16"):
                    content = content.convert("RGBA")
                content.save(path, format="PNG")
                count = self.attach_image_files([path])
            if count:
                messagebox.showinfo(APP_TITLE, "Clipboard image attached as PNG. Click Add or Update to save the entry.")
            return count
        except (NotImplementedError, AttributeError):
            messagebox.showerror(APP_TITLE, "Clipboard image access is unavailable.\nUpdate Pillow: python -m pip install --upgrade pillow\nOn Ubuntu/Debian install: sudo apt install xclip wl-clipboard\nThen copy the image again and retry.")
        except Exception as error:
            messagebox.showerror(APP_TITLE, f"Could not copy an image from the clipboard:\n{error}")
        return 0

    def attach_image_files(self, paths):
        """Validate and attach one or more images without discarding existing ones."""
        if not self.fields["title"].get().strip():
            messagebox.showinfo(APP_TITLE, "Enter the title before attaching images.")
            return 0
        extensions = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".gif", ".webp"}
        valid = []
        skipped = []
        for path in paths:
            path = os.path.abspath(os.path.expanduser(path))
            if os.path.isfile(path) and os.path.splitext(path)[1].lower() in extensions:
                valid.append(path)
            else:
                skipped.append(path)
        if not valid:
            messagebox.showwarning(APP_TITLE, "No supported image files were selected or dropped.")
            return 0
        try:
            self.ensure_compact_title(valid[0])
            stored = [self.store_document(path, "Image") for path in valid]
            existing = [p for p in self.fields["image_paths"].get().split("; ") if p]
            self.fields["image_paths"].set("; ".join(dict.fromkeys([*existing, *stored])))
            if skipped:
                messagebox.showinfo(
                    APP_TITLE,
                    f"Added {len(stored)} image(s). Skipped {len(skipped)} unsupported item(s).",
                )
            return len(stored)
        except OSError as error:
            messagebox.showerror(APP_TITLE, f"Could not store the images:\n{error}")
            return 0

    def drop_images(self, event):
        """Accept multiple supported images from a desktop file-manager drop."""
        try:
            paths = list(self.tk.splitlist(event.data))
        except (tk.TclError, TypeError):
            paths = []
        if not paths:
            messagebox.showwarning(APP_TITLE, "No image files were found in the drop.")
            return "break"
        self.attach_image_files(paths)
        return "break"

    def open_selected_file(self):
        if self.fields["item_type"].get() == "Websites":
            self.tabs.select(1)
            self.document_tabs.select(self.plain_source_tab)
            self.workspace_tabs.select(0)
            self.notes.focus_set()
            return
        if self.fields["item_type"].get() == "Lecture":
            paths = [self.resolve_stored_path(p) for p in self.fields["lecture_pdf_paths"].get().split("; ") if p]
            paths = [p for p in paths if os.path.isfile(p)]
            if not paths:
                messagebox.showinfo(APP_TITLE, "This lecture has no attached PDFs.")
                return
            if len(paths) == 1:
                open_with_system(paths[0])
                return
            dialog = tk.Toplevel(self)
            dialog.title("Open lecture PDF")
            dialog.geometry("520x320")
            files = tk.Listbox(dialog, exportselection=False)
            files.pack(fill="both", expand=True, padx=12, pady=12)
            for path in paths:
                files.insert("end", os.path.basename(path))
            files.selection_set(0)
            def open_chosen(_event=None):
                selected = files.curselection()
                if selected:
                    open_with_system(paths[selected[0]])
                    dialog.destroy()
            ttk.Button(dialog, text="Open selected PDF", command=open_chosen).pack(pady=(0, 12))
            files.bind("<Double-1>", open_chosen)
            return
        if self.fields["item_type"].get() in ("Equation", "Note"):
            self.tabs.select(1)
            self.preview_equation(compile_full=True)
            self.equation_text.focus_set()
            return
        if self.fields["item_type"].get() == "Image" and not self.fields["file_link"].get().strip():
            self.open_images()
            return
        value = self.fields["file_link"].get().strip()
        if not value:
            messagebox.showinfo(APP_TITLE, "This entry has no attached PDF.")
            return
        try:
            resolved = self.resolve_stored_path(value)
            # Continue opening URLs stored by older PyCat versions, but v14 no
            # longer permits adding new web links to the PDF attachment field.
            if value.startswith(("http://", "https://")) or os.path.exists(resolved):
                open_with_system(resolved)
            else:
                messagebox.showerror(APP_TITLE, "The saved PDF location does not exist.")
        except Exception as error:
            messagebox.showerror(APP_TITLE, f"Could not open the PDF:\n{error}")

    def open_entry_folder(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo(APP_TITLE, "Select an entry first.")
            return
        row = self.conn.execute("SELECT * FROM literature WHERE id=?", (int(selection[0]),)).fetchone()
        folder = self.entry_folder_for(row["section"], row["subsection"],
            self.folder_author(row["corresponding_author"], row["authors"]), row["title"], row["item_type"])
        if os.path.isdir(folder):
            try:
                open_with_system(folder)
            except Exception as error:
                messagebox.showerror(APP_TITLE, f"Could not open the entry folder:\n{error}")
            return
        candidates = [row["file_link"], row["bibtex_path"], row["notes_path"], row["equation_pdf_path"]]
        candidates.extend((row["supplementary_paths"] or "").split("; "))
        candidates.extend((row["lecture_pdf_paths"] or "").split("; "))
        candidates.extend((row["image_paths"] or "").split("; "))
        existing = next((self.resolve_stored_path(path) for path in candidates
                         if path and os.path.exists(self.resolve_stored_path(path))), None)
        if not existing:
            messagebox.showinfo(APP_TITLE, "No stored local document was found for this entry.")
            return
        folder = os.path.dirname(existing)
        try:
            open_with_system(folder)
        except Exception as error:
            messagebox.showerror(APP_TITLE, f"Could not open the entry folder:\n{error}")

    def open_bibtex_file(self):
        self.open_selected_attachment("bibtex_path", "BibTeX / RIS")

    def open_supplementary(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo(APP_TITLE, "Select an entry first.")
            return
        row = self.conn.execute("SELECT supplementary_paths FROM literature WHERE id=?", (int(selection[0]),)).fetchone()
        paths = [path for path in (row["supplementary_paths"] or "").split("; ") if path]
        existing = [self.resolve_stored_path(path) for path in paths
                    if os.path.exists(self.resolve_stored_path(path))]
        if not existing:
            messagebox.showinfo(APP_TITLE, "This entry has no stored supplementary files.")
            return
        try:
            for path in existing:
                open_with_system(path)
        except Exception as error:
            messagebox.showerror(APP_TITLE, f"Could not open the supplementary files:\n{error}")

    def open_notes_file(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo(APP_TITLE, "Select an entry first.")
            return
        row = self.conn.execute("SELECT * FROM literature WHERE id=?", (int(selection[0]),)).fetchone()
        stored_path = row["notes_path"]
        path = self.resolve_stored_path(stored_path)
        if not stored_path or not os.path.exists(path):
            try:
                path = self.write_notes_file(
                    row["notes"] or "", row["section"], row["subsection"],
                    self.folder_author(row["corresponding_author"], row["authors"]), row["title"], row["item_type"],
                )
                self.conn.execute("UPDATE literature SET notes_path=? WHERE id=?", (path, int(selection[0])))
                self.conn.commit()
                self.sync_csv()
            except OSError as error:
                messagebox.showerror(APP_TITLE, f"Could not create Notes.txt:\n{error}")
                return
        try:
            open_with_system(self.resolve_stored_path(path))
        except Exception as error:
            messagebox.showerror(APP_TITLE, f"Could not open Notes.txt:\n{error}")

    def open_selected_attachment(self, column, label):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo(APP_TITLE, "Select an entry first.")
            return
        row = self.conn.execute(f"SELECT {column} FROM literature WHERE id=?", (int(selection[0]),)).fetchone()
        stored_path = row[column] or ""
        path = self.resolve_stored_path(stored_path)
        if not stored_path or not os.path.exists(path):
            messagebox.showinfo(APP_TITLE, f"This entry has no stored {label} file.")
            return
        try:
            open_with_system(path)
        except Exception as error:
            messagebox.showerror(APP_TITLE, f"Could not open the {label} file:\n{error}")

    def sync_csv(self):
        """Keep a spreadsheet-readable catalog synchronized automatically."""
        columns = ("item_type", "title", "authors", "year", "source", "volume_issue_pages", "doi_isbn", "keywords", "section", "subsection", "corresponding_author", "author_email", "file_link", "lecture_pdf_paths", "supplementary_paths", "bibtex_path", "image_paths", "notes_path", "notes", "equation_latex", "equation_renderer", "equation_pdf_path", "notes_pdf_path", "website", "place", "report_date")
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
    def is_ris(text):
        return bool(re.search(r"^\s*TY\s{2}-\s*\S+", text.lstrip("\ufeff"), re.MULTILINE))

    @staticmethod
    def parse_citation(text):
        return NMRCatalog.parse_ris(text) if NMRCatalog.is_ris(text) else NMRCatalog.parse_bibtex(text)

    @staticmethod
    def parse_ris(text):
        """Read RIS records into the same metadata fields used by BibTeX imports."""
        entries, record = [], None
        last_tag = None

        def finish():
            if not record:
                return
            def first(*tags):
                return next((v for tag in tags for v in record.get(tag, []) if v), "")
            kind = first("TY").upper()
            entry_type = {"BOOK": "book", "EBOOK": "book", "CHAP": "inbook",
                          "THES": "thesis", "RPRT": "techreport", "CONF": "proceedings",
                          "CPAPER": "inproceedings", "MANUAL": "manual"}.get(kind, "article")
            year = re.search(r"\b\d{4}\b", first("PY", "Y1", "DA"))
            start, end = first("SP"), first("EP")
            pages = start + ("--" + end if start and end and start != end else "")
            pages = pages or end or first("C7")
            fields = {
                "title": first("TI", "T1", "CT"),
                "author": " and ".join(record.get("AU") or record.get("A1") or []),
                "year": year.group(0) if year else "",
                "journal": first("JF", "JO", "JA", "J2", "T2") if entry_type == "article" else "",
                "booktitle": first("T2", "BT") if entry_type in ("inbook", "inproceedings") else "",
                "publisher": first("PB"), "volume": first("VL"), "number": first("IS"),
                "pages": pages, "doi": first("DO"), "isbn": first("SN"),
                "keywords": "; ".join(record.get("KW", [])),
                "abstract": first("AB", "N2"), "note": "\n".join(record.get("N1", [])),
                "url": first("UR"), "file": first("L1"),
            }
            entries.append((entry_type, {k: v for k, v in fields.items() if v}))

        for line in text.lstrip("\ufeff").splitlines():
            match = re.match(r"^\s*([A-Z0-9]{2})\s{2}-\s?(.*)$", line)
            if match:
                tag, value = match.groups()
                if tag == "TY":
                    finish()
                    record = {}
                elif tag == "ER":
                    finish()
                    record, last_tag = None, None
                    continue
                if record is not None:
                    record.setdefault(tag, []).append(value.strip())
                    last_tag = tag
            elif record is not None and last_tag and line.strip():
                record[last_tag][-1] += " " + line.strip()
        finish()
        return entries

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

    @staticmethod
    def bibtex_form_values(entry_type, bib):
        """Map one parsed BibTeX entry to PyCat form fields."""
        entry_type = (entry_type or "").lower()
        if entry_type == "manual":
            item_type = "Manual"
        elif entry_type in ("book", "inbook", "booklet", "proceedings"):
            item_type = "Book"
        elif entry_type in ("phdthesis", "mastersthesis", "thesis"):
            item_type = "Thesis"
        else:
            item_type = "Paper"

        author_text = (bib.get("author") or "").strip()
        authors = re.sub(r"\s+and\s+", "; ", author_text, flags=re.IGNORECASE)
        corresponding = (
            bib.get("correspondingauthor")
            or bib.get("corresponding_author")
            or bib.get("corresponding-author")
            or ""
        )
        source = (
            bib.get("journal") or bib.get("booktitle") or bib.get("publisher")
            or bib.get("school") or bib.get("institution") or ""
        )
        volume_data = ", ".join(filter(None, (
            bib.get("volume"), bib.get("number") or bib.get("issue"), bib.get("pages")
        )))
        values = {
            "item_type": item_type,
            "title": bib.get("title", ""),
            "authors": authors,
            "year": bib.get("year", ""),
            "source": source,
            "volume_issue_pages": volume_data,
            "doi_isbn": bib.get("doi") or bib.get("isbn", ""),
            "keywords": bib.get("keywords") or bib.get("keyword", ""),
            "corresponding_author": corresponding,
            "author_email": bib.get("email", ""),
        }
        notes = bib.get("abstract") or bib.get("note", "")
        url = bib.get("url", "")
        return values, notes, url

    def apply_bibtex_to_form(self, entry_type, bib):
        values, notes, url = self.bibtex_form_values(entry_type, bib)
        populated = []
        for name, value in values.items():
            if value:
                self.fields[name].set(value)
                populated.append(name)
        note_parts = [notes.strip()] if notes.strip() else []
        if url:
            note_parts.append("Source URL: " + url)
        if note_parts:
            self.notes.configure(state="normal")
            self.notes.delete("1.0", "end")
            self.notes.insert("1.0", "\n\n".join(note_parts))
            populated.append("notes")
        self.update_type_controls()
        self.tabs.select(1)
        return populated

    def fill_form_from_bibtex_text(self, text, parent=None):
        entries = self.parse_citation(text)
        if not entries:
            messagebox.showwarning(APP_TITLE, "No valid BibTeX or RIS entry was found.", parent=parent)
            return False
        if len(entries) == 1:
            self.apply_bibtex_to_form(*entries[0])
            messagebox.showinfo(
                APP_TITLE,
                "The form was filled from the citation. Review the fields, then click Add or Update.",
                parent=parent,
            )
            return True

        chooser = tk.Toplevel(parent or self)
        chooser.title("Choose a citation entry")
        chooser.geometry("760x380")
        chooser.minsize(480, 280)
        chooser.transient(parent or self)
        panel = ttk.Frame(chooser, padding=12)
        panel.pack(fill="both", expand=True)
        ttk.Label(panel, text=f"This file contains {len(entries)} entries. Choose one to fill the form.").pack(anchor="w", pady=(0, 8))
        list_frame = ttk.Frame(panel)
        list_frame.pack(fill="both", expand=True)
        choices = tk.Listbox(list_frame, exportselection=False)
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=choices.yview)
        choices.configure(yscrollcommand=scroll.set)
        choices.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        for entry_type, bib in entries:
            title = bib.get("title") or "Untitled"
            author = bib.get("author") or "Unknown author"
            choices.insert("end", f"{entry_type}: {title} — {author}")
        choices.selection_set(0)

        def apply_selected(_event=None):
            selection = choices.curselection()
            if not selection:
                messagebox.showinfo(APP_TITLE, "Select a citation entry first.", parent=chooser)
                return
            self.apply_bibtex_to_form(*entries[selection[0]])
            chooser.destroy()
            messagebox.showinfo(
                APP_TITLE,
                "The form was filled from the selected citation entry. Review it, then click Add or Update.",
                parent=parent,
            )

        actions = ttk.Frame(panel)
        actions.pack(fill="x", pady=(10, 0))
        ttk.Button(actions, text="Fill Form", command=apply_selected).pack(side="right")
        ttk.Button(actions, text="Cancel", command=chooser.destroy).pack(side="right", padx=5)
        choices.bind("<Double-1>", apply_selected)
        chooser.grab_set()
        choices.focus_set()
        return True

    def import_bibtex(self):
        path = filedialog.askopenfilename(title="Import BibTeX / RIS", filetypes=(("Citation files", "*.bib *.bibtex *.ris"), ("Text files", "*.txt"), ("All files", "*.*")))
        if not path:
            return
        section = simpledialog.askstring(APP_TITLE, "Section / field for these entries (required):", parent=self)
        if section is None:
            return
        section = section.strip()
        if not section:
            messagebox.showwarning(APP_TITLE, "Section / field is required for citation import.")
            return
        subsection = simpledialog.askstring(APP_TITLE, "Subsection for these entries (required):", parent=self)
        if subsection is None:
            return
        subsection = subsection.strip()
        if not subsection:
            messagebox.showwarning(APP_TITLE, "Subsection is required for citation import.")
            return
        try:
            with open(path, encoding="utf-8-sig") as file:
                entries = self.parse_citation(file.read())
            imported = skipped = 0
            columns = ("item_type", "title", "authors", "year", "source", "volume_issue_pages", "doi_isbn", "keywords", "section", "subsection", "corresponding_author", "author_email", "file_link", "supplementary_paths", "bibtex_path", "image_paths", "notes_path", "notes")
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
                source = bib.get("journal") or bib.get("booktitle") or bib.get("publisher") or bib.get("school") or bib.get("institution", "")
                volume_data = ", ".join(filter(None, (bib.get("volume"), bib.get("number"), bib.get("pages"))))
                file_link = bib.get("file", "")
                if file_link and ":" in file_link:
                    candidates = [part for part in file_link.split(":") if part.lower().endswith(".pdf")]
                    file_link = candidates[0] if candidates else file_link
                author_text = bib.get("author", "").strip()
                if not author_text:
                    skipped += 1
                    continue
                corresponding = (
                    bib.get("correspondingauthor") or bib.get("corresponding_author")
                    or bib.get("corresponding-author") or ""
                )
                item_type = "Manual" if entry_type == "manual" else "Book" if entry_type in ("book", "inbook") else "Thesis" if entry_type in ("phdthesis", "mastersthesis", "thesis") else "Paper"
                self.fields["item_type"].set(item_type)
                self.fields["authors"].set(author_text.replace(" and ", "; "))
                self.fields["section"].set(section)
                self.fields["subsection"].set(subsection)
                self.fields["corresponding_author"].set(corresponding)
                self.fields["title"].set(title)
                if file_link and os.path.isfile(os.path.expanduser(file_link)) and file_link.lower().endswith(".pdf"):
                    file_link = self.store_document(file_link, "PDF")
                else:
                    file_link = ""
                stored_bib = self.store_bibtex_entry(path, title, entry_type, bib)
                notes = bib.get("note") or bib.get("abstract", "")
                if bib.get("url"):
                    notes = (notes + "\n\n" if notes else "") + "Source URL: " + bib["url"]
                notes_path = self.write_notes_file(notes, section, subsection, self.folder_author(corresponding, author_text), title, item_type)
                values = (
                    item_type,
                    title,
                    author_text.replace(" and ", "; "),
                    bib.get("year", ""), source, volume_data, doi_isbn,
                    bib.get("keywords", ""), section, subsection, corresponding, bib.get("email", ""),
                    file_link, "", stored_bib, "", notes_path, notes,
                )
                self.conn.execute(f"INSERT INTO literature ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})", values)
                imported += 1
            self.conn.commit()
            self.sync_csv()
            self.refresh_table()
            messagebox.showinfo(APP_TITLE, f"Imported {imported} citation entries.\nSkipped {skipped} incomplete or duplicate entries.")
        except (OSError, sqlite3.Error) as error:
            self.conn.rollback()
            messagebox.showerror(APP_TITLE, f"Citation import failed:\n{error}")

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
        return self.portable_stored_path(destination)

    def sort_table(self, column, reverse):
        rows = [(self.tree.set(item, column), item) for item in self.tree.get_children("")]
        rows.sort(key=lambda pair: pair[0].casefold(), reverse=reverse)
        for index, (_value, item) in enumerate(rows):
            self.tree.move(item, "", index)
        self.tree.heading(column, command=lambda: self.sort_table(column, not reverse))

    def close_app(self):
        if self._preview_job is not None:
            self.after_cancel(self._preview_job)
        if self._latex_poll_job is not None:
            self.after_cancel(self._latex_poll_job)
        if self._pdf_poll_job is not None:
            self.after_cancel(self._pdf_poll_job)
        self._latex_executor.shutdown(wait=False, cancel_futures=True)
        self.conn.close()
        self.destroy()


if __name__ == "__main__":
    NMRCatalog().mainloop()
