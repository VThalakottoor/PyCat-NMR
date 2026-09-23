# PyCat NMR v1.0.2

PyCat NMR is a desktop catalog for organizing NMR papers, books, manuals,
theses, lectures, notes, images, equations, BibTeX records, and supplementary material. It uses
Python, Tkinter, and SQLite and runs from source on Linux, Windows, and macOS.

**Author:** Vineeth Francis Thalakottoor  
**Contact:** vineeth.thalakottoor@cea.fr

## Features

- Eight entry types: **Paper**, **Book**, **Manual**, **Thesis**, **Lecture**, **Note**,
  **Image**, and **Equation**.
- Search by title, author, keyword, section, subsection, or all fields.
- Filters for entry type, section, and subsection.
- Attach a local PDF, supplementary files, BibTeX, and images by file selection
  or drag-and-drop.
- Attach BibTeX from an existing `.bib` or `.bibtex` file or paste BibTeX directly into
  PyCat.
- Rearrange imported author names from `Family, Given` to `Given Family` with
  the **Rearrange authors** button.
- Editable notes for every entry type, also saved as `Notes.txt`.
- Equation editor for Papers, Books, Manuals, Theses, Notes, and Equation entries.
- Quick equation preview, full LaTeX preview, mixed text and equations, and PDF
  export.
- Separate storage and opening of the main literature PDF and the exported
  LaTeX/equation PDF.
- Automatic CSV synchronization in `PyCat_NMR_Catalog.csv`.
- Portable relative paths for moving the complete PyCat folder between
  computers or using it from a USB drive.

## Files and folders

Keep the complete PyCat directory together:

```text
PyCat/
├── PyCat_NMR_v1.0.2.py
├── README_v1.0.2.md
├── nmr_catalog.db
├── PyCat_NMR_Catalog.csv
└── NMR_Library/
    ├── Papers/
    ├── Books/
    ├── Thesis/
    ├── Manuals/
    ├── Lectures/
    ├── Notes/
    ├── Images/
    └── Equations/
```

Each catalog item is organized as:

```text
NMR_Library/
└── Category/
    └── Section/
        └── Subsection/
            └── Corresponding author-Title/
                ├── main-document.pdf
                ├── reference.bib
                ├── Notes.txt
                ├── supplementary-files
                ├── attached-images
                └── Title-Equations.pdf
```

The final folder uses the corresponding author. If that field is empty, PyCat
uses the first author in **Authors**. If both fields are empty, it uses
`Unknown author`.

## Requirements

- Python 3.10 or newer is recommended.
- Tkinter for the desktop interface.
- Matplotlib for quick equation preview.
- Pillow for full LaTeX preview image processing.
- Optional: tkinterdnd2 for dragging PDFs, supplementary files, BibTeX, and
  images from the desktop into PyCat.
- Optional: a LaTeX distribution and Poppler for Full LaTeX preview and PDF
  export in `Text + equations` or `Full LaTeX` mode.

The Python packages installed with `pip` are:

```text
matplotlib
pillow
tkinterdnd2
```

SQLite, CSV, and Tkinter interfaces are used from Python's standard library,
although some Linux distributions package Tkinter separately.

## Linux installation

The following commands are suitable for Ubuntu and Debian-based systems.

1. Open a terminal and install Python virtual-environment and Tkinter support:

   ```bash
   sudo apt update
   sudo apt install python3 python3-venv python3-tk
   ```

2. Go to the PyCat folder. Quote the path if it contains spaces:

   ```bash
   cd ~/Documents/LSDRM/Bibliography/PyCat
   ```

3. Create a local virtual-environment folder and an environment named `pycat`:

   ```bash
   mkdir -p ~/venv
   python3 -m venv ~/venv/pycat
   ```

4. Activate it:

   ```bash
   source ~/venv/pycat/bin/activate
   ```

5. Install the Python dependencies:

   ```bash
   python -m pip install --upgrade pip
   python -m pip install matplotlib pillow tkinterdnd2
   ```

6. Optional: install Full LaTeX support:

   ```bash
   sudo apt install texlive-latex-base texlive-latex-recommended texlive-latex-extra poppler-utils
   ```

7. Run PyCat:

   ```bash
   python PyCat_NMR_v1.0.2.py
   ```

For later sessions:

```bash
cd ~/Documents/LSDRM/Bibliography/PyCat
source ~/venv/pycat/bin/activate
python PyCat_NMR_v1.0.2.py
```

Leave the virtual environment with:

```bash
deactivate
```

## Windows installation

1. Install Python 3 from [python.org](https://www.python.org/downloads/windows/).
   During installation, enable the Python launcher and Tcl/Tk support.

2. Open PowerShell in the PyCat folder, or navigate to it:

   ```powershell
   cd "C:\Users\Vineeth\Documents\PyCat"
   ```

3. Create a local virtual-environment folder and an environment named `pycat`:

   ```powershell
   New-Item -ItemType Directory -Force "$env:USERPROFILE\venv"
   py -m venv "$env:USERPROFILE\venv\pycat"
   ```

4. Activate it in PowerShell:

   ```powershell
   & "$env:USERPROFILE\venv\pycat\Scripts\Activate.ps1"
   ```

   In Command Prompt instead, use:

   ```bat
   %USERPROFILE%\venv\pycat\Scripts\activate.bat
   ```

5. Install the Python dependencies:

   ```powershell
   python -m pip install --upgrade pip
   python -m pip install matplotlib pillow tkinterdnd2
   ```

6. Optional: install MiKTeX or TeX Live for Full LaTeX and install Poppler so
   `pdflatex` and `pdftoppm` are available on `PATH`.

7. Run PyCat:

   ```powershell
   python PyCat_NMR_v1.0.2.py
   ```

If PowerShell blocks activation, either use Command Prompt with
`activate.bat`, or run PyCat without activation by calling the environment's
interpreter directly:

```powershell
& "$env:USERPROFILE\venv\pycat\Scripts\python.exe" PyCat_NMR_v1.0.2.py
```

## macOS installation

1. Install a current Python 3 distribution from
   [python.org](https://www.python.org/downloads/macos/). The python.org macOS
   installer includes Tk support.

2. Open Terminal and go to the PyCat folder:

   ```bash
   cd ~/Documents/PyCat
   ```

3. Create a local virtual-environment folder, create an environment named
   `pycat`, and activate it:

   ```bash
   mkdir -p ~/venv
   python3 -m venv ~/venv/pycat
   source ~/venv/pycat/bin/activate
   ```

4. Install the Python dependencies:

   ```bash
   python -m pip install --upgrade pip
   python -m pip install matplotlib pillow tkinterdnd2
   ```

5. Optional: install MacTeX for Full LaTeX. If Homebrew is installed, install
   Poppler with:

   ```bash
   brew install poppler
   ```

6. Run PyCat:

   ```bash
   python PyCat_NMR_v1.0.2.py
   ```

## Important virtual-environment rule

A virtual environment contains operating-system-specific executables and
absolute interpreter paths. **Do not copy a virtual environment between Linux,
Windows, and macOS.** Create a separate local environment named `pycat` on each
computer. Keeping it in the computer's local `venv` folder means it does not
travel with or clutter the portable PyCat folder.

If PyCat is on a USB drive, a convenient approach is:

```text
Linux/macOS internal drive: ~/venv/pycat
Windows internal drive:     %USERPROFILE%\venv\pycat
USB drive: PyCat_NMR_v1.0.2.py, database, CSV, and NMR_Library
```

You do not have to activate a virtual environment if you call its Python
interpreter directly.

## Running from a USB drive

For use across Linux, Windows, and macOS:

1. Format the drive as **exFAT**.
2. Copy the complete `PyCat` folder to the drive.
3. Before the first move, run PyCat and click **Organize Files** so externally
   linked files are copied into `NMR_Library`.
4. Close PyCat before ejecting the drive.
5. On each computer, run the script using that computer's Python environment.

PyCat stores files inside its directory using relative paths such as:

```text
NMR_Library/Papers/NMR/Relaxation/Author-Title/paper.pdf
```

Therefore, changing a Windows USB drive letter or a Linux/macOS mount location
does not break organized file links.

Do not run the same database simultaneously from two computers, and never
disconnect the drive while PyCat is open. SQLite may be writing to the database
at that moment.

## Adding an entry

1. Open **Upload / Edit**.
2. Select a type from the visible choices: Paper, Book, Manual, Thesis, Lecture, Note, Image, or Equation. The form displays only fields relevant to that type.
3. Enter the required **Title**, **Section**, and **Subsection**. These three
   fields are compulsory for every entry type.
4. For Paper, Book, Manual, Thesis, and Lecture, enter at least one name in **Authors**.
   Authors are not required for Note, Image, or Equation. Corresponding author,
   year, source, DOI/ISBN, and keywords remain optional.
   For imported BibTeX authors such as `Li, Jing; Léonce, Estelle`, click
   **Rearrange authors** to display `Jing Li; Estelle Léonce`. Review the
   editable field, then click **Add** or **Update** to save the change.
5. Enter the title, then select the PDF with **Select PDF...**, or drag one PDF
   from the operating system's file manager onto **Drop PDF here**.
6. Enter notes or equation content if required.
7. Click **Add**.

PyCat will not add or update an entry while a compulsory field is empty. Manual
uses the same full metadata and attachment controls as Paper. For Note,
only Title, Section, Subsection, Notes, and the equation editor remain visible;
enter at least a note or an equation. Image and Equation also disable fields
that are not relevant. Titles are never generated automatically.

## Lectures with multiple PDFs

Choose **Lecture** in **Upload / Edit**, then enter **Title**, **Authors**, **Section**, and **Subsection**. These four fields are required. Click **Select PDFs…** to select several PDF files at once (`Ctrl` or `Shift` on Linux/Windows, `Command` or `Shift` on macOS), or drop several PDFs onto **Drop lecture PDFs here**. Repeat either action to add more files, then click **Add** or **Update**. The selected PDFs are copied into `NMR_Library/Lectures/Section/Subsection/Author-Title/` with their original filenames. Non-PDF files are skipped. Under **Search Library**, select the lecture and click **Open / View** to choose one PDF; **Open Entry Folder** displays all files in the folder. Lecture PDF paths are stored separately from the single PDF used for papers, books, manuals, and theses. Notes are optional.

## Editing or deleting an entry

1. Select the entry under **Search Library**.
2. Click **Edit Selected**.
3. Make changes and click **Update**.

To remove the database entry, click **Delete** and confirm. Review the files in
the entry folder separately if you also want to remove stored attachments.

## Adding multiple supplementary files

There are two ways to add supplementary material:

- Drag one or several files from the operating system's file manager onto
  **Drop supplementary files here**.
- Click **Supplement...**, hold `Ctrl` on Linux/Windows or `Command` on macOS,
  select multiple files, and click **Open**. Use `Shift` to select a range.

Then click **Add** for a new entry or **Update** for an existing entry.

Dropping more files or clicking **Supplement...** again adds them without
discarding existing ones. Duplicate stored locations are not added twice.
Folders in a drop are skipped. **Open Supplementary** opens every available
supplementary attachment in its default application. A ZIP file opens in the
operating system's default archive manager; PyCat does not extract it
automatically.

## BibTeX

There are two attachment methods:

- **BibTeX...** selects an existing `.bib` or `.bibtex` file.
- **Drop .bib/.bibtex here** accepts one `.bib` or `.bibtex` file dragged from the operating
  system's file manager. If several files are dropped, PyCat uses the first.
- **Paste...** opens an editor where BibTeX can be pasted and saved as a `.bib`
  attachment.

After selecting or dropping a `.bib` or `.bibtex` file, PyCat asks whether its metadata
should fill the form. After any attachment method, click **Add** or **Update**
to save the catalog entry.
**Import BibTeX** can create multiple catalog entries from a BibTeX database;
it asks for one compulsory Section and Subsection for the imported group.
Entries without a title or author, and duplicate entries, are skipped.

## Notes

Notes are available for all eight entry types. PyCat stores the notes in the
SQLite catalog and writes `Notes.txt` into the entry folder. Use **Open Notes**
to open that file in the operating system's default text editor.

## Equations, text, previews, and PDF export

The equation editor is available for Papers, Books, Manuals, Theses, Notes, and Equation
entries. It provides three modes:

### Text + equations

Write normal paragraphs with inline math between `$...$` and displayed math
between `\[...\]`.

```latex
The magnetization $M_z$ approaches its equilibrium value $M_0$.

\[
\frac{dM_z}{dt}=-\frac{M_z-M_0}{T_1}
\]

Here, $T_1$ is the longitudinal relaxation time.
```

### Quick preview

Use common LaTeX mathematics without a full LaTeX installation. Matplotlib's
MathText renderer provides the preview.

### Full LaTeX

Use environments such as `align`, matrices, cases, or a complete LaTeX
document. This mode requires `pdflatex`, `pdftoppm`, and Pillow.

Click **Preview** to render the content. Click **Save PDF...** to export
`Title-Equations.pdf`; the save dialog starts in the entry's own folder. PyCat
stores this as a separate LaTeX PDF attachment, without replacing the paper,
book, manual, or thesis PDF. Click **Open PDF** in the equation editor to open the
current form's exported PDF. Under **Search Library**, select an entry and click
**Open LaTeX PDF** to open it independently of **Open / View**, which opens the
main literature PDF. Click **Add** or **Update** after exporting to retain the
editable source and the LaTeX PDF location in the catalog.

For files exported by an older PyCat version, v1.0.2 also checks the entry folder
for the standard `Title-Equations.pdf` filename and records it automatically
when opened.

## PDF attachment and drag-and-drop

The **PDF attachment** field stores only the location of a local PDF copied
into the entry folder. It does not accept typed paths or web links. For a Paper,
Book, or Thesis:

1. Enter the title first so PyCat can create the correct Author-Title folder.
2. Click **Select PDF...** and choose one PDF, or drag one PDF onto
   **Drop PDF here**.
3. Click **Add** or **Update** to save the catalog entry.

Drag-and-drop requires `tkinterdnd2`. Without it, PyCat still works and shows
the normal **Select PDF...** button. Install it in the active `pycat`
environment with:

```bash
python -m pip install tkinterdnd2
```

## Images

Use **Images...** to attach one or several images, or drag multiple image files
onto **Drop images here**. PNG, JPEG, TIFF, BMP, GIF, and WebP are supported.
Additional drops preserve images that are already attached, and duplicate
stored locations are not added twice.
**Open Images** launches saved images in the operating system's default image
viewer.

## Organize Files

**Organize Files** processes every catalog entry. It:

- Creates the Category/Section/Subsection/Author-Title structure.
- Copies local main documents, supplementary files, BibTeX files, images, and
  notes into the correct entry folder.
- Updates the SQLite database and CSV with portable relative paths.
- Preserves the original source files.
- Reuses an identical destination file instead of creating a duplicate.
- Reports references whose source files cannot be found.

Run it after importing an older catalog, changing the folder conventions, or
before moving PyCat to a USB drive.

## Automatic database and CSV files

- `nmr_catalog.db` is the authoritative SQLite catalog.
- `PyCat_NMR_Catalog.csv` is updated automatically and can be opened in a
  spreadsheet application.

Do not edit the database while PyCat is running. The CSV is useful for reading
and backup, but changes made directly to the CSV are not imported automatically.

## Backup and safe use

Regularly back up the complete PyCat folder, especially:

```text
nmr_catalog.db
NMR_Library/
```

Before copying, backing up, ejecting, or disconnecting the drive, close PyCat
so SQLite can finish writing. The **Organize Files** operation copies rather
than deletes originals, but a separate backup is still recommended.

## Troubleshooting

### `externally-managed-environment`

Your operating system protects its system Python. Create and activate the local
`pycat` environment and install packages there; do not use
`--break-system-packages` for PyCat.

### Find the local environment

On Linux or macOS:

```bash
ls -la ~/venv/pycat
```

On Windows PowerShell:

```powershell
Get-ChildItem "$env:USERPROFILE\venv\pycat"
```

### Confirm which environment is active

On Linux or macOS:

```bash
echo "$VIRTUAL_ENV"
which python
```

On Windows PowerShell:

```powershell
$env:VIRTUAL_ENV
Get-Command python
```

### `No module named matplotlib`, `PIL`, or `tkinterdnd2`

Activate the correct environment, then run:

```bash
python -m pip install matplotlib pillow tkinterdnd2
```

### Full LaTeX preview fails

Check that these commands are available:

```bash
pdflatex --version
pdftoppm -v
```

Full LaTeX is intentionally compiled with shell escape disabled. Correct any
LaTeX syntax error displayed by PyCat and try Preview again.

### A linked file cannot be found

If it is still available, attach it again and click **Update**. Then use
**Organize Files** to copy it into the portable library.

### ZIP files do not open

Assign a default archive application in the operating system. On Ubuntu or
Debian, Archive Manager can be installed with:

```bash
sudo apt install file-roller
```

## References

- [Python virtual environments](https://docs.python.org/3/library/venv.html)
- [Python Packaging User Guide: venv and pip](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/)
- [Matplotlib: text rendering with LaTeX](https://matplotlib.org/stable/users/explain/text/usetex.html)
