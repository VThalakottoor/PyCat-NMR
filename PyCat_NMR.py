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
    "Note": "Notes", "Image": "Images", "Equation": "Equations",
}

ITEM_TYPES = ("Paper", "Book", "Manual", "Thesis", "Note", "Image", "Equation")


APP_VERSION = "1.0.0"
APP_TITLE = f"PyCat NMR v{APP_VERSION}"
APP_SUBTITLE = "Python Catalog for NMR"
__author__ = "Vineeth Francis Thalakottoor"
__email__ = "vineeth.thalakottoor@cea.fr"
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


class NMRCatalog(CatalogWindow):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1180x720")
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

        search_frame = ttk.Frame(self, padding=(14, 0, 14, 10))
        search_frame.pack(fill="x")
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
            values=("All", *ITEM_TYPES),
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

        # Scroll metadata independently so Add/Update remain accessible on small screens.
        editor = ttk.Panedwindow(upload_tab, orient="horizontal")
        editor.pack(fill="both", expand=True)
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
        self.equation_panel = ttk.LabelFrame(editor, text="Equation editor", padding=12)
        editor.add(self.equation_panel, weight=2)
        table_frame = ttk.LabelFrame(search_tab, text="Papers, books, manuals, theses, notes, images, and equations", padding=8)
        table_frame.pack(fill="both", expand=True)

        self.fields = {}
        self.field_widgets = {}
        self.attachment_buttons = {}
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
            ("supplementary_paths", "Supplementary files", None),
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
                widget = ttk.Entry(form, textvariable=var, state="readonly" if key == "file_link" else "normal")
            self.field_widgets[key] = widget
            widget.grid(row=row, column=1, sticky="ew", pady=(0, 8))

        # Stored separately from the main paper PDF. It is managed through the
        # equation editor and the dedicated Open LaTeX PDF buttons.
        self.fields["equation_pdf_path"] = tk.StringVar()

        for row, key, label, command in (
            (12, "file_link", "Select PDF…", self.browse_file),
            (13, "supplementary_paths", "Supplement…", self.browse_supplementary),
            (14, "bibtex_path", "BibTeX…", self.browse_bibtex_attachment),
            (15, "image_paths", "Images…", self.browse_images),
        ):
            actions = ttk.Frame(form)
            actions.grid(row=row, column=2, padx=(6, 0), pady=(0, 8), sticky="w")
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
                drop_text = "Drop .bib here" if DND_AVAILABLE else "Drag-and-drop: install tkinterdnd2"
                self.bibtex_drop_target = ttk.Label(actions, text=drop_text, relief="groove", padding=(8, 6))
                self.bibtex_drop_target.pack(side="left", padx=(5, 0))
                if DND_AVAILABLE:
                    for target in (self.bibtex_drop_target, self.field_widgets["bibtex_path"]):
                        target.drop_target_register(DND_FILES)
                        target.dnd_bind("<<Drop>>", self.drop_bibtex)
            if key == "image_paths":
                drop_text = "Drop images here" if DND_AVAILABLE else "Drag-and-drop: install tkinterdnd2"
                self.images_drop_target = ttk.Label(actions, text=drop_text, relief="groove", padding=(8, 6))
                self.images_drop_target.pack(side="left", padx=(5, 0))
                if DND_AVAILABLE:
                    for target in (self.images_drop_target, self.field_widgets["image_paths"]):
                        target.drop_target_register(DND_FILES)
                        target.dnd_bind("<<Drop>>", self.drop_images)
        ttk.Label(form, text="Notes").grid(row=16, column=0, sticky="nw")
        self.notes = tk.Text(form, height=7, width=35, wrap="word")
        self.notes.grid(row=16, column=1, columnspan=2, sticky="nsew")
        form.columnconfigure(1, weight=1)
        form.rowconfigure(16, weight=1)

        buttons = ttk.Frame(upload_tab)
        buttons.pack(fill="x", pady=(12, 0))
        ttk.Button(buttons, text="Add", command=self.add_item).pack(side="left")
        ttk.Button(buttons, text="Update", command=self.update_item).pack(side="left", padx=5)
        ttk.Button(buttons, text="Clear", command=self.clear_form).pack(side="left")
        ttk.Button(buttons, text="Delete", command=self.delete_item).pack(side="right")

        self._build_equation_editor()
        self.fields["item_type"].trace_add("write", self.update_type_controls)
        self.update_type_controls()

        columns = ("type", "title", "authors", "year", "section", "subsection", "source")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
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
        ttk.Button(footer, text="Open / View", command=self.open_selected_file).pack(side="right")
        ttk.Button(footer, text="Open Supplementary", command=self.open_supplementary).pack(side="right", padx=5)
        ttk.Button(footer, text="View BibTeX", command=self.open_bibtex_file).pack(side="right", padx=5)
        ttk.Button(footer, text="Open Notes", command=self.open_notes_file).pack(side="right")
        footer_more = ttk.Frame(table_frame)
        footer_more.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        ttk.Button(footer_more, text="Open Images", command=self.open_images).pack(side="left")
        ttk.Button(footer_more, text="Open LaTeX PDF", command=self.open_selected_equation_pdf).pack(side="left", padx=5)
        ttk.Button(footer_more, text="Open Entry Folder", command=self.open_entry_folder).pack(side="right", padx=5)
        ttk.Button(footer_more, text="Edit Selected", command=lambda: self.tabs.select(1)).pack(side="right")
        ttk.Button(footer_more, text="Import BibTeX", command=self.import_bibtex).pack(side="right", padx=5)
        ttk.Button(footer_more, text="Organize Files", command=self.organize_existing_files).pack(side="left", padx=5)


    def _build_equation_editor(self):
        panel = self.equation_panel
        ttk.Label(panel, text="Text and LaTeX equations").pack(anchor="w")
        self.renderer_var = tk.StringVar(value="Text + equations")
        self.renderer_combo = ttk.Combobox(panel, textvariable=self.renderer_var,
            values=("Text + equations", "Quick preview", "Full LaTeX"), state="readonly")
        self.renderer_combo.pack(fill="x", pady=6)
        self.renderer_combo.bind("<<ComboboxSelected>>", self._renderer_changed)
        ttk.Label(panel, text="Text + equations: write paragraphs; use $...$ for inline\nmath and \\[...\\] for displayed equations.\nClick Preview to render, or Save PDF to export.",
                  foreground="#555555").pack(anchor="w", pady=(4, 8))
        self.equation_text = tk.Text(panel, height=9, width=32, wrap="word", undo=True)
        self.equation_text.pack(fill="x")
        self.equation_text.bind("<<Modified>>", self._equation_modified)
        self._preview_job = None
        self._equation_photo = None
        actions = ttk.Frame(panel)
        actions.pack(fill="x", pady=8)
        self.preview_button = ttk.Button(actions, text="Preview", command=lambda: self.preview_equation(compile_full=True))
        self.preview_button.pack(side="left")
        self.example_button = ttk.Button(actions, text="Example", command=self.insert_equation_example)
        self.example_button.pack(side="left", padx=4)
        self.save_pdf_button = ttk.Button(actions, text="Save PDF…", command=self.save_equation_pdf)
        self.save_pdf_button.pack(side="left", padx=4)
        self.open_latex_pdf_button = ttk.Button(actions, text="Open PDF", command=self.open_current_equation_pdf)
        self.open_latex_pdf_button.pack(side="left")
        self.equation_status = ttk.Label(panel, text="", wraplength=330)
        self.equation_status.pack(fill="x", pady=(0, 8))
        preview = ttk.Frame(panel)
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

    def _equation_modified(self, _event=None):
        if not self.equation_text.edit_modified():
            return
        self.equation_text.edit_modified(False)
        if self._preview_job is not None:
            self.after_cancel(self._preview_job)
        self._preview_job = self.after(500, self.preview_equation)

    def insert_equation_example(self):
        if self.equation_text.get("1.0", "end-1c").strip():
            self.equation_text.insert("end", "\n")
        if self.renderer_var.get() == "Text + equations":
            example = ("Longitudinal relaxation\n\n"
                       "The magnetization $M_z$ returns to its equilibrium value $M_0$.\n\n"
                       r"\[ \frac{dM_z}{dt} = -\frac{M_z-M_0}{T_1} \]" + "\n\n"
                       "Here, $T_1$ is the longitudinal relaxation time.")
        else:
            example = r"\frac{dM_z}{dt} = -\frac{M_z-M_0}{T_1}"
        self.equation_text.insert("end", example)
        self.preview_equation()

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
        latex = self.equation_text.get("1.0", "end-1c").strip()
        self.equation_canvas.delete("all")
        self._equation_photo = None
        self.equation_canvas.configure(scrollregion=(0, 0, 1, 1))
        if not latex:
            self.equation_status.configure(text="Type an equation to see its preview.", foreground="#555555")
            return
        if self.renderer_var.get() in ("Full LaTeX", "Text + equations"):
            if not compile_full:
                self.equation_status.configure(text="Click Preview to compile with Full LaTeX.", foreground="#555555")
                return
            if self._latex_future is not None:
                self.equation_status.configure(text="A compilation is finishing. Click Preview again shortly.", foreground="#555555")
                return
            self.equation_status.configure(text="Compiling LaTeX…", foreground="#555555")
            self._latex_future = self._latex_executor.submit(self.full_latex_png, latex, "png", self.renderer_var.get() == "Text + equations")
            generation = self._preview_generation
            self._latex_poll_job = self.after(100, lambda: self._poll_latex(generation))
            return
        try:
            png = self.equation_png(latex)
            self._equation_photo = tk.PhotoImage(master=self, data=base64.b64encode(png).decode("ascii"))
            self.equation_canvas.create_image(8, 8, anchor="nw", image=self._equation_photo)
            self.equation_canvas.configure(scrollregion=self.equation_canvas.bbox("all"))
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
        compact = kind in ("Equation", "Image", "Note")
        for key, widget in self.field_widgets.items():
            if key == "item_type":
                widget.configure(state="readonly")
            elif key == "file_link":
                # The primary document is selected or dropped, never typed as a URL.
                widget.configure(state="readonly" if not compact else "disabled")
            elif compact:
                widget.configure(state="normal" if key in ("title", "section", "subsection") else "disabled")
            else:
                widget.configure(state="normal")
        for key, button in self.attachment_buttons.items():
            enabled = not compact or (kind == "Image" and key == "image_paths")
            button.configure(state="normal" if enabled else "disabled")
        if hasattr(self, "pdf_drop_target"):
            self.pdf_drop_target.configure(
                text=("Drop PDF here" if DND_AVAILABLE else "PDF drag-and-drop: install tkinterdnd2"),
                state="normal" if not compact else "disabled",
            )
        if hasattr(self, "supplementary_drop_target"):
            self.supplementary_drop_target.configure(
                text=("Drop supplementary files here" if DND_AVAILABLE else "Drag-and-drop: install tkinterdnd2"),
                state="normal" if not compact else "disabled",
            )
        if hasattr(self, "bibtex_drop_target"):
            self.bibtex_drop_target.configure(
                text=("Drop .bib here" if DND_AVAILABLE else "Drag-and-drop: install tkinterdnd2"),
                state="normal" if not compact else "disabled",
            )
        if hasattr(self, "images_drop_target"):
            self.images_drop_target.configure(
                text=("Drop images here" if DND_AVAILABLE else "Drag-and-drop: install tkinterdnd2"),
                state="normal" if (not compact or kind == "Image") else "disabled",
            )
        self.notes.configure(state="normal")
        equation_enabled = kind in ("Paper", "Book", "Manual", "Thesis", "Note", "Equation")
        self.equation_text.configure(state="normal" if equation_enabled else "disabled")
        self.renderer_combo.configure(state="readonly" if equation_enabled else "disabled")
        self.preview_button.configure(state="normal" if equation_enabled else "disabled")
        self.example_button.configure(state="normal" if equation_enabled else "disabled")
        self.save_pdf_button.configure(state="normal" if equation_enabled and self._pdf_future is None else "disabled")
        self.open_latex_pdf_button.configure(state="normal" if equation_enabled else "disabled")

    def ensure_compact_title(self, image_path=None):
        # Every entry requires a meaningful user-supplied title.
        return self.fields["title"].get().strip()

    def _renderer_changed(self, _event=None):
        self.preview_equation()

    @staticmethod
    def full_latex_png(source, output_format="png", text_mode=False):
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
            document = source
        else:
            # Display environments provide their own math mode; matrix/cases need a wrapper.
            display = re.match(r"\\begin\{(?:align\*?|alignat\*?|gather\*?|multline\*?|equation\*?|flalign\*?|displaymath)\}", source)
            wrapped = source.startswith(("$", r"\[", r"\("))
            body = source if text_mode or display or wrapped else "\\[\n" + source + "\n\\]"
            document = (r"\documentclass[12pt]{article}" + "\n" +
                        r"\usepackage[margin=12mm]{geometry}" + "\n" +
                        r"\usepackage{amsmath,amssymb,bm}" + "\n" +
                        r"\pagestyle{empty}" + "\n" + r"\begin{document}" + "\n" +
                        body + "\n" + r"\end{document}")
        with tempfile.TemporaryDirectory(prefix="pycat_latex_") as directory:
            tex_path = os.path.join(directory, "equation.tex")
            with open(tex_path, "w", encoding="utf-8") as file:
                file.write(document)
            env = os.environ.copy()
            env.update({"openin_any": "p", "openout_any": "p"})
            result = subprocess.run(
                [compiler, "-no-shell-escape", "-interaction=nonstopmode", "-halt-on-error", "equation.tex"],
                cwd=directory, env=env, capture_output=True, text=True, errors="replace", timeout=30,
            )
            if result.returncode:
                log = result.stdout + result.stderr
                lines = log.splitlines()
                index = next((i for i, line in enumerate(lines) if line.startswith("!")), max(0, len(lines) - 8))
                raise ValueError("LaTeX compilation failed:\n" + "\n".join(lines[index:index + 8]))
            if output_format == "pdf":
                with open(os.path.join(directory, "equation.pdf"), "rb") as file:
                    return file.read()
            prefix = os.path.join(directory, "page")
            result = subprocess.run(
                [converter, "-png", "-r", "130", "-f", "1", "-l", "10",
                 os.path.join(directory, "equation.pdf"), prefix],
                capture_output=True, text=True, errors="replace", timeout=30,
            )
            if result.returncode:
                raise ValueError("Could not render the LaTeX PDF:\n" + result.stderr[-800:])
            names = sorted((name for name in os.listdir(directory) if re.fullmatch(r"page-\d+\.png", name)),
                           key=lambda name: int(name[5:-4]))
            images = []
            for name in names:
                with Image.open(os.path.join(directory, name)) as page:
                    page = page.convert("RGB")
                    box = ImageChops.difference(page, Image.new("RGB", page.size, "white")).getbbox()
                    if box:
                        images.append(ImageOps.expand(page.crop(box), border=16, fill="white"))
            if not images:
                raise ValueError("LaTeX produced no visible content.")
            # Keep PDF page order and preserve gaps between pages in the preview.
            width = max(page.width for page in images)
            height = sum(page.height for page in images) + 12 * (len(images) - 1)
            if width * height > 40_000_000:
                raise ValueError("Preview is too large. Shorten the LaTeX document.")
            combined = Image.new("RGB", (width, height), "white")
            y = 0
            for page in images:
                combined.paste(page, (0, y))
                y += page.height + 12
            output = io.BytesIO()
            combined.save(output, format="PNG")
            return output.getvalue()

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
            png = future.result()
            self._equation_photo = tk.PhotoImage(master=self, data=base64.b64encode(png).decode("ascii"))
            self.equation_canvas.create_image(8, 8, anchor="nw", image=self._equation_photo)
            self.equation_canvas.configure(scrollregion=self.equation_canvas.bbox("all"))
            self.equation_status.configure(text="Full LaTeX preview (up to 10 pages). Use Add or Update to save.", foreground="#27632a")
        except ImportError:
            self.equation_status.configure(text="Install image support: python -m pip install pillow", foreground="#a04020")
        except subprocess.TimeoutExpired:
            self.equation_status.configure(text="LaTeX preview timed out. Check or shorten the source.", foreground="#a04020")
        except Exception as error:
            self.equation_status.configure(text=str(error)[:700], foreground="#a04020")


    def save_equation_pdf(self):
        source = self.equation_text.get("1.0", "end-1c").strip()
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
            initialfile=self.safe_name(title, "Equation") + "-Equations.pdf",
            filetypes=(("PDF document", "*.pdf"),),
        )
        if not path:
            return
        # Capture the current editor content; never export an outdated preview image.
        renderer = self.renderer_var.get()
        self._pdf_future = self._latex_executor.submit(self.render_pdf_to_file, source, renderer, path)
        self.save_pdf_button.configure(state="disabled")
        self.equation_status.configure(text="Creating PDF…", foreground="#555555")
        self._pdf_poll_job = self.after(100, self._poll_pdf_export)

    @staticmethod
    def render_pdf_to_file(source, renderer, path):
        if renderer == "Quick preview":
            pdf = NMRCatalog.equation_png(source, output_format="pdf")
        else:
            pdf = NMRCatalog.full_latex_png(source, output_format="pdf", text_mode=renderer == "Text + equations")
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
        self.save_pdf_button.configure(state="normal" if self.fields["item_type"].get() in ("Paper", "Book", "Manual", "Thesis", "Note", "Equation") else "disabled")
        try:
            path = future.result()
            self.fields["equation_pdf_path"].set(self.portable_stored_path(path))
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
        if self.fields["item_type"].get() not in ("Paper", "Book", "Manual", "Thesis", "Note", "Equation"):
            messagebox.showinfo(APP_TITLE, "LaTeX PDFs are available for papers, books, manuals, theses, notes, and equations.")
            return
        stored = self.fields["equation_pdf_path"].get().strip()
        path = self.resolve_stored_path(stored)
        if not stored or not os.path.isfile(path):
            path = self.expected_equation_pdf(
                self.fields["section"].get(), self.fields["subsection"].get(),
                self.fields["corresponding_author"].get(), self.fields["authors"].get(),
                self.fields["title"].get(), self.fields["item_type"].get(),
            )
        if not os.path.isfile(path):
            messagebox.showinfo(APP_TITLE, "No saved LaTeX PDF was found. Use Save PDF… first.")
            return
        self.fields["equation_pdf_path"].set(self.portable_stored_path(path))
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
        if row["item_type"] not in ("Paper", "Book", "Manual", "Thesis", "Note", "Equation"):
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
        values["equation_latex"] = self.equation_text.get("1.0", "end-1c").strip()
        values["equation_renderer"] = self.renderer_var.get()
        values["notes"] = self.notes.get("1.0", "end").strip()
        return values

    def validate_entry_data(self, data):
        """Enforce the metadata needed for consistent search and folder organization."""
        required = (
            ("title", "Please enter a title."),
            ("section", "Please enter a section / field."),
            ("subsection", "Please enter a subsection."),
        )
        for key, message in required:
            if not data.get(key):
                messagebox.showwarning(APP_TITLE, message)
                return False
        if data["item_type"] in ("Paper", "Book", "Manual", "Thesis") and not data.get("authors"):
            messagebox.showwarning(APP_TITLE, "Please enter at least one author.")
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
        sql = "SELECT * FROM literature WHERE 1=1"
        parameters = []
        if query:
            pattern = f"%{query}%"
            field_map = {
                "Title": ("title",), "Keywords": ("keywords",), "Author": ("authors", "corresponding_author"),
                "Section": ("section",), "Subsection": ("subsection",),
                "All fields": ("title", "authors", "corresponding_author", "author_email", "source", "doi_isbn", "keywords", "section", "subsection", "notes", "equation_latex"),
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
        columns = ("file_link", "bibtex_path", "supplementary_paths", "image_paths", "notes_path", "equation_pdf_path")
        rows = self.conn.execute("SELECT id, " + ", ".join(columns) + " FROM literature").fetchall()
        with self.conn:
            for row in rows:
                updates = {}
                for key in columns:
                    multiple = key in ("supplementary_paths", "image_paths")
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
        for name in CATEGORY_FOLDERS.values():
            os.makedirs(os.path.join(self.library_root(), name), exist_ok=True)

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
        for key in ("file_link", "bibtex_path", "supplementary_paths", "image_paths", "equation_pdf_path"):
            multiple = key in ("supplementary_paths", "image_paths")
            paths = (data.get(key) or "").split("; ") if multiple else [data.get(key) or ""]
            stored = []
            for path in paths:
                resolved = self.resolve_stored_path(path)
                if path and os.path.isfile(resolved):
                    path = self.portable_stored_path(self.copy_to_entry(resolved, folder))
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
            columns = ("file_link", "bibtex_path", "supplementary_paths", "image_paths", "notes_path", "equation_pdf_path")
            with self.conn:
                for row in rows:
                    for key in columns:
                        paths = (row[key] or "").split("; ") if key in ("supplementary_paths", "image_paths") else [row[key] or ""]
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
        dialog.title("Paste BibTeX")
        dialog.geometry("760x520")
        dialog.minsize(520, 360)
        dialog.transient(self)
        panel = ttk.Frame(dialog, padding=12)
        panel.pack(fill="both", expand=True)
        ttk.Label(panel, text="Paste BibTeX below. Fill Form extracts its metadata; Save .bib attaches the citation file.",
                  wraplength=650).pack(anchor="w", pady=(0, 8))

        def paste():
            try:
                editor.insert("insert", self.clipboard_get())
            except tk.TclError:
                messagebox.showinfo(APP_TITLE, "The clipboard contains no text.", parent=dialog)

        def save():
            raw = editor.get("1.0", "end-1c")
            if not raw.strip():
                messagebox.showwarning(APP_TITLE, "Paste some BibTeX first.", parent=dialog)
                return
            if not self.fields["title"].get().strip():
                messagebox.showwarning(APP_TITLE, "Enter the entry title first, then paste its BibTeX.", parent=dialog)
                return
            try:
                path = self.store_pasted_bibtex(raw)
                self.fields["bibtex_path"].set(path)
            except OSError as error:
                messagebox.showerror(APP_TITLE, f"Could not save the BibTeX:\n{error}", parent=dialog)
                return
            dialog.destroy()
            messagebox.showinfo(APP_TITLE, "BibTeX file attached. Click Add or Update to save the catalog entry.")

        # Keep actions above the expanding editor so they remain visible on
        # small screens and with large desktop font/scaling settings.
        buttons = ttk.Frame(panel)
        buttons.pack(fill="x", pady=(0, 10))
        ttk.Button(buttons, text="Paste from clipboard", command=paste).pack(side="left")
        ttk.Button(buttons, text="Fill Form", command=lambda: self.fill_form_from_bibtex_text(
            editor.get("1.0", "end-1c"), parent=dialog
        )).pack(side="left", padx=5)
        ttk.Button(buttons, text="Save .bib", command=save).pack(side="right")
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
            source = os.path.join(directory, "reference.bib")
            with open(source, "w", encoding="utf-8", newline="") as file:
                file.write(text)
            return self.store_document(source, "BibTeX")

    def browse_bibtex_attachment(self):
        path = filedialog.askopenfilename(title="Attach BibTeX", filetypes=(("BibTeX files", "*.bib"), ("All files", "*.*")))
        if path:
            self.attach_bibtex_file(path)

    def attach_bibtex_file(self, path):
        """Validate, attach and optionally parse one local BibTeX file."""
        path = os.path.abspath(os.path.expanduser(path))
        if not os.path.isfile(path):
            messagebox.showwarning(APP_TITLE, "The BibTeX item is not a file.")
            return False
        if os.path.splitext(path)[1].lower() != ".bib":
            messagebox.showwarning(APP_TITLE, "Only .bib files can be attached as BibTeX.")
            return False
        try:
            self.fields["bibtex_path"].set(self.store_document(path, "BibTeX"))
            with open(path, encoding="utf-8-sig", errors="replace") as file:
                bibtex_text = file.read()
            if messagebox.askyesno(
                APP_TITLE, "BibTeX file attached. Fill the form from its metadata now?",
                default=messagebox.YES,
            ):
                self.fill_form_from_bibtex_text(bibtex_text)
            return True
        except OSError as error:
            messagebox.showerror(APP_TITLE, f"Could not store the BibTeX file:\n{error}")
            return False

    def drop_bibtex(self, event):
        """Accept the first .bib file from a desktop file-manager drop."""
        try:
            paths = list(self.tk.splitlist(event.data))
        except (tk.TclError, TypeError):
            paths = []
        if not paths:
            messagebox.showwarning(APP_TITLE, "No BibTeX file was found in the drop.")
            return "break"
        if len(paths) > 1:
            messagebox.showinfo(APP_TITLE, "Only one BibTeX attachment is supported. Using the first dropped file.")
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
        self.open_selected_attachment("bibtex_path", "BibTeX")

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
        columns = ("item_type", "title", "authors", "year", "source", "volume_issue_pages", "doi_isbn", "keywords", "section", "subsection", "corresponding_author", "author_email", "file_link", "supplementary_paths", "bibtex_path", "image_paths", "notes_path", "notes", "equation_latex", "equation_renderer", "equation_pdf_path")
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
        entries = self.parse_bibtex(text)
        if not entries:
            messagebox.showwarning(APP_TITLE, "No valid BibTeX entry was found.", parent=parent)
            return False
        if len(entries) == 1:
            self.apply_bibtex_to_form(*entries[0])
            messagebox.showinfo(
                APP_TITLE,
                "The form was filled from BibTeX. Review the fields, then click Add or Update.",
                parent=parent,
            )
            return True

        chooser = tk.Toplevel(parent or self)
        chooser.title("Choose a BibTeX entry")
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
                messagebox.showinfo(APP_TITLE, "Select a BibTeX entry first.", parent=chooser)
                return
            self.apply_bibtex_to_form(*entries[selection[0]])
            chooser.destroy()
            messagebox.showinfo(
                APP_TITLE,
                "The form was filled from the selected BibTeX entry. Review it, then click Add or Update.",
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
        path = filedialog.askopenfilename(title="Import BibTeX", filetypes=(("BibTeX files", "*.bib"), ("Text files", "*.txt"), ("All files", "*.*")))
        if not path:
            return
        section = simpledialog.askstring(APP_TITLE, "Section / field for these entries (required):", parent=self)
        if section is None:
            return
        section = section.strip()
        if not section:
            messagebox.showwarning(APP_TITLE, "Section / field is required for BibTeX import.")
            return
        subsection = simpledialog.askstring(APP_TITLE, "Subsection for these entries (required):", parent=self)
        if subsection is None:
            return
        subsection = subsection.strip()
        if not subsection:
            messagebox.showwarning(APP_TITLE, "Subsection is required for BibTeX import.")
            return
        try:
            with open(path, encoding="utf-8-sig") as file:
                entries = self.parse_bibtex(file.read())
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
