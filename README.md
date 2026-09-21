# PyCat NMR

PyCat NMR is a desktop catalog for organizing NMR papers, books, theses,
images, equations, notes, BibTeX records, and supplementary material. It uses
Python, Tkinter, and SQLite and runs from source on Linux, Windows, and macOS.

**Author:** Vineeth Francis Thalakottoor  
**Contact:** vineeth.thalakottoor@cea.fr

## Features

- Five entry types: **Paper**, **Book**, **Thesis**, **Image**, and **Equation**.
- Search by title, author, keyword, section, subsection, or all fields.
- Filters for entry type, section, and subsection.
- Attach a document or web link, multiple supplementary files, BibTeX, and
  multiple images.
- Attach BibTeX from an existing `.bib` file or paste BibTeX directly into
  PyCat.
- Editable notes for every entry type, also saved as `Notes.txt`.
- Equation editor for Papers, Books, Theses, and Equation entries.
- Quick equation preview, full LaTeX preview, mixed text and equations, and PDF
  export.
- Automatic CSV synchronization in `PyCat_NMR_Catalog.csv`.
- Portable relative paths for moving the complete PyCat folder between
  computers or using it from a USB drive.

## Files and folders

Keep the complete PyCat directory together:

```text
PyCat/
├── PyCat_NMR.py
├── PyCat_NMR_README.md
├── nmr_catalog.db
├── PyCat_NMR_Catalog.csv
├── .venv/                     # local only; do not move between operating systems
└── NMR_Library/
    ├── Papers/
    ├── Books/
    ├── Thesis/
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
- Optional: a LaTeX distribution and Poppler for Full LaTeX preview and PDF
  export in `Text + equations` or `Full LaTeX` mode.

The Python packages installed with `pip` are:

```text
matplotlib
pillow
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

3. Create the virtual environment:

   ```bash
   python3 -m venv .venv
   ```

4. Activate it:

   ```bash
   source .venv/bin/activate
   ```

5. Install the Python dependencies:

   ```bash
   python -m pip install --upgrade pip
   python -m pip install matplotlib pillow
   ```

6. Optional: install Full LaTeX support:

   ```bash
   sudo apt install texlive-latex-base texlive-latex-recommended texlive-latex-extra poppler-utils
   ```

7. Run PyCat:

   ```bash
   python PyCat_NMR.py
   ```

For later sessions:

```bash
cd ~/Documents/LSDRM/Bibliography/PyCat
source .venv/bin/activate
python PyCat_NMR.py
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

3. Create a Windows virtual environment:

   ```powershell
   py -m venv .venv
   ```

4. Activate it in PowerShell:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

   In Command Prompt instead, use:

   ```bat
   .venv\Scripts\activate.bat
   ```

5. Install the Python dependencies:

   ```powershell
   python -m pip install --upgrade pip
   python -m pip install matplotlib pillow
   ```

6. Optional: install MiKTeX or TeX Live for Full LaTeX and install Poppler so
   `pdflatex` and `pdftoppm` are available on `PATH`.

7. Run PyCat:

   ```powershell
   python PyCat_NMR.py
   ```

If PowerShell blocks activation, either use Command Prompt with
`activate.bat`, or run PyCat without activation by calling the environment's
interpreter directly:

```powershell
.\.venv\Scripts\python.exe PyCat_NMR.py
```

## macOS installation

1. Install a current Python 3 distribution from
   [python.org](https://www.python.org/downloads/macos/). The python.org macOS
   installer includes Tk support.

2. Open Terminal and go to the PyCat folder:

   ```bash
   cd ~/Documents/PyCat
   ```

3. Create and activate the virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

4. Install the Python dependencies:

   ```bash
   python -m pip install --upgrade pip
   python -m pip install matplotlib pillow
   ```

5. Optional: install MacTeX for Full LaTeX. If Homebrew is installed, install
   Poppler with:

   ```bash
   brew install poppler
   ```

6. Run PyCat:

   ```bash
   python PyCat_NMR.py
   ```

## Important virtual-environment rule

A virtual environment contains operating-system-specific executables and
absolute interpreter paths. **Do not copy `.venv` between Linux, Windows, and
macOS.** Create a new `.venv` on each computer or keep separate environments
outside the portable PyCat folder.

If PyCat is on a USB drive, a convenient approach is:

```text
Computer's internal drive: local .venv and installed dependencies
USB drive: PyCat_NMR.py, database, CSV, and NMR_Library
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
2. Select Paper, Book, Thesis, Image, or Equation.
3. Enter the title, section, and subsection.
4. For literature, complete the authors, corresponding author, year, source,
   DOI/ISBN, and keywords as available.
5. Attach the relevant files.
6. Enter notes or equation content if required.
7. Click **Add**.

For Image and Equation entries, fields not relevant to that type are disabled.
If an Image or Equation title is left empty, PyCat generates one automatically.

## Editing or deleting an entry

1. Select the entry under **Search Library**.
2. Click **Edit Selected**.
3. Make changes and click **Update**.

To remove the database entry, click **Delete** and confirm. Review the files in
the entry folder separately if you also want to remove stored attachments.

## Adding multiple supplementary files

1. Select or create an entry.
2. Click **Supplement...**.
3. Hold `Ctrl` on Linux/Windows or `Command` on macOS to select multiple files.
   Use `Shift` to select a range.
4. Click **Open**.
5. Click **Add** for a new entry or **Update** for an existing entry.

Clicking **Supplement...** again adds more files without discarding existing
ones. **Open Supplementary** opens every available supplementary attachment in
its default application. A ZIP file opens in the operating system's default
archive manager; PyCat does not extract it automatically.

## BibTeX

There are two attachment methods:

- **BibTeX...** selects an existing `.bib` file.
- **Paste...** opens an editor where BibTeX can be pasted and saved as a `.bib`
  attachment.

After either method, click **Add** or **Update** to save the catalog entry.
**Import BibTeX** can create multiple catalog entries from a BibTeX database;
incomplete or duplicate entries are skipped.

## Notes

Notes are available for all five entry types. PyCat stores the notes in the
SQLite catalog and writes `Notes.txt` into the entry folder. Use **Open Notes**
to open that file in the operating system's default text editor.

## Equations, text, previews, and PDF export

The equation editor is available for Papers, Books, Theses, and Equation
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
`Title-Equations.pdf`; the save dialog starts in the entry's own folder. Click
**Add** or **Update** to retain the editable source in the catalog.

## Images

Use **File...** for a primary image or **Images...** to attach several images.
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

Your operating system protects its system Python. Create and activate `.venv`
and install packages there; do not use `--break-system-packages` for PyCat.

### `.venv` is not visible on Linux or macOS

Names beginning with a dot are hidden. In a terminal use:

```bash
ls -la
```

In many graphical file managers, press `Ctrl+H` to show hidden files.

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

### `No module named matplotlib` or `No module named PIL`

Activate the correct environment, then run:

```bash
python -m pip install matplotlib pillow
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

