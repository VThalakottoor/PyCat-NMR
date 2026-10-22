# PyCat NMR — README

Version: **1.0.18**  
Author: Vineeth Francis Thalakottoor  
Contact: vineeth.thalakottoor@cea.fr

PyCat NMR is a desktop catalog for papers, books, manuals, theses, lecture notes, conferences, reports, researchers, and websites. It stores metadata, attachments, plain-text notes, LaTeX source, and generated PDFs beside the application.

## Requirements

- Python **3.9 or newer**, with Tkinter and a graphical desktop session.
- `matplotlib` for quick equation previews.
- `pillow` for image handling and full PDF previews.
- `tkinterdnd2` for optional drag-and-drop attachments; file browsing works without it.
- `pdflatex` for compiling reports and Beamer slides to PDF.
- Poppler's `pdftoppm` for displaying PDF previews inside PyCat.

Citation parsing uses the Python standard library; no additional BibTeX or RIS package is needed. Internet access is needed to install dependencies; normal catalog use works offline.

## Install on Ubuntu / Debian

Install the system prerequisites:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-tk
```

Create and activate an environment:

```bash
python3 -m venv ~/venvs/pycat
source ~/venvs/pycat/bin/activate
python -m pip install --upgrade pip
python -m pip install matplotlib pillow tkinterdnd2
```

For reports, slides, and full PDF previews:

```bash
sudo apt install texlive-latex-base texlive-latex-recommended texlive-latex-extra poppler-utils
```

Run the program from your PyCat folder:

```bash
cd "/path/to/PyCat"
python PyCat_NMR.py
```

Activate the environment each time you open a new terminal. Run `deactivate` when finished.

## Install on Windows — Command Prompt

Install Python 3.9 or newer with Tcl/Tk support. Open CMD, then run:

```bat
py -m venv "%USERPROFILE%\venvs\pycat"
call "%USERPROFILE%\venvs\pycat\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install matplotlib pillow tkinterdnd2
```

Run the application:

```bat
cd /d "C:\path\to\PyCat"
python PyCat_NMR.py
```

For full LaTeX support, install MiKTeX or TeX Live, including Beamer, and Poppler. Add their executable folders to PATH, then restart your terminal. Check:

```bat
where pdflatex
where pdftoppm
```

Activate the environment in each new CMD window before running PyCat. Use `deactivate` to leave it.

## Keep your catalog together

Keep these items in the same application folder:

| Item | Purpose |
| --- | --- |
| `PyCat_NMR.py` | Application |
| `nmr_catalog.db` | SQLite catalog database, created automatically |
| `PyCat_NMR_Catalog.csv` | Automatically refreshed catalog export |
| `NMR_Library/` | Stored attachments and entry folders |

Entry folders are organized by category, section, subsection, and author/title. Attachment paths are stored relative to the application folder where possible, so the complete folder can be moved between computers.

To upgrade, close PyCat and replace the application script in your existing PyCat folder. Retain the database, CSV, and `NMR_Library` folder. Back up the whole folder before upgrading.

## Add and edit entries

1. Open **Upload / Edit** and choose the entry type.
2. Enter the title, section, and subsection. Existing section/subsection values appear as suggestions.
3. Enter authors for papers, books, manuals, theses, lecture notes, and reports.
4. Attach PDFs, citations, supplementary files, or images using the available controls.
5. Add plain text or LaTeX source if needed.
6. Click **Add** for a new entry or **Update** for an existing selected entry.

Conferences and reports require a title but allow an empty section/subsection. An optional report date must use `YYYY-MM-DD`. Researchers and websites use plain-text notes. Lecture notes support multiple PDF attachments.

## BibTeX and RIS citations

Supported citation files: **`.bib`, `.bibtex`, and `.ris`**.

### Attach a citation and fill the form

1. Select Paper, Book, Manual, or Thesis in **Upload / Edit**.
2. Click **BibTeX / RIS…**, or drop a citation file onto its drop area.
3. Choose whether to fill the form from the citation metadata.
4. If the file contains multiple records, select the record to use.
5. Review the fields, supply any missing required information, and click **Add** or **Update**.

The original citation file is retained as an attachment. Only one citation attachment is supported per entry; when several files are dropped together, the first is used. Use **View BibTeX / RIS** to open the saved attachment in the system's associated application.

### Paste a citation

1. Click **Paste…** beside the citation attachment.
2. Paste BibTeX or RIS text, or click **Paste from clipboard**.
3. Click **Fill Form** to extract metadata.
4. With an entry title entered, click **Save citation** to attach the text.
5. Click **Add** or **Update** to save the catalog entry.

Pasted text is saved as `.ris` when a RIS record is detected; otherwise it is saved as `.bib`. **Fill Form** and **Save citation** are separate actions.

RIS metadata extraction supports common title, author, year/date, journal, volume, issue, pages, DOI, ISBN/ISSN, keyword, abstract, note, and URL tags. Repeated authors and keywords and multiline field continuations are supported. Review imported metadata because citation exports vary between publishers.

**Rearrange authors** changes names such as `Francis, Vineeth` to `Vineeth Francis` in the form.

## LaTeX reports and Beamer slides

Open the **LaTeX code** editor under the **LaTeX** workspace tab.

| Button | Action |
| --- | --- |
| **Clear code** | Empty the LaTeX source editor |
| **Insert default report** | Insert the existing A4 article/report template |
| **Insert default beamer** | Insert a minimal widescreen Beamer document with two slides |
| **New page** | Insert `\newpage` into LaTeX source |
| **Preview** | Compile and show the PDF in **LaTeX output** when Full LaTeX is selected |
| **Save PDF…** | Compile and save a PDF attachment |
| **Open PDF** | Open the saved PDF in an external viewer |

The template buttons insert at the cursor and select **Full LaTeX**. To start a new document, use **Clear code** before inserting a template; inserting a complete document into an existing document can cause compilation errors. The editor starts without a default template.

### Report workflow

1. Choose **Report** and enter its title and authors.
2. Click **Insert default report**.
3. Edit the title, author, date, and content in the LaTeX source.
4. Click **Preview** and use **Previous page / Next page** to inspect the result.
5. Click **Save PDF…**, then **Add** or **Update** to retain the source and attachment in the catalog.

### Beamer workflow

1. Choose an appropriate entry type, such as **Report**, and enter its metadata.
2. Click **Clear code**, then **Insert default beamer**.
3. Edit the presentation title, author, and introduction points.
4. Click **Preview** or **Save PDF…**.
5. Click **Add** or **Update** to save the catalog entry.

The default contains exactly two slides: a title slide and an introduction slide with two bullet points. It uses `aspectratio=169`; compilation preserves the slide dimensions. To add slides, duplicate a `\begin{frame}{Title} ... \end{frame}` block before `\end{document}`. Use frame blocks to create new Beamer slides rather than the **New page** button.

Full compilation supports up to 100 output pages and has a 120-second compilation timeout. **Quick preview** uses Matplotlib MathText for equations; use **Full LaTeX** for complete reports and slides.

## Search and open attachments

Use **Search Library** to search entries and filter by section/subsection. Search ignores letter case and treats punctuation as word separators; for example, `Non-Linearities` and `non linearities` match the same words.

Select an entry to open its main file, supplementary files, notes, citation, LaTeX PDF, images, or entry folder using the bottom toolbar. Use **Edit Selected** to work on the selected entry and **Update** to save changes.

## Images and clipboard

Use the image attachment control or **Copy from clipboard**. Clipboard images are saved as PNG files in the entry's Images folder. On Windows, copied image files from File Explorer are also supported.

Linux clipboard access may require:

```bash
sudo apt install xclip wl-clipboard
```

These provide clipboard access for X11 and Wayland respectively.

## Organize files and back up

- **Organize Files** moves still-used attachments into folders matching their current entry metadata.
- **Delete unused folders…** displays a review list before deletion. It checks the entire saved catalog, including entries hidden by search filters, and protects referenced attachments and the current upload form.
- To back up or move the catalog, close PyCat and copy the complete application folder, including the database and `NMR_Library`.
- Keep a Python environment on each computer; recreate it there rather than moving a virtual environment between operating systems.

## Troubleshooting

| Problem | Action |
| --- | --- |
| `No module named tkinter` | Install the system's Tkinter package; on Ubuntu/Debian use `sudo apt install python3-tk`. |
| No graphical display / `$DISPLAY` error | Run from a graphical desktop session; a terminal-only session cannot display this GUI. |
| Drag-and-drop unavailable | Install `tkinterdnd2` in the active environment and restart PyCat; browsing remains available. |
| `pdflatex` missing or Beamer class not found | Install the LaTeX packages listed above, or install Beamer through your Windows LaTeX distribution. |
| PDF export works but preview fails | Check that `pdftoppm` is on PATH and `pillow` is installed. |
| LaTeX fails after inserting a template | Keep only one complete document, with one document class and one document environment. |
| Citation metadata is incomplete | Review the citation text and complete missing fields manually before saving. |
| Attachment cannot be found after moving | Move the database, script, and entire `NMR_Library` together. |

## Changes in v1.0.18

- Added RIS support alongside BibTeX for citation attachments, drag-and-drop, pasted text, and metadata extraction.
- Renamed **Insert default code** to **Insert default report**.
- Added **Insert default beamer** with a minimal two-slide template.
- Preserved document page dimensions during compilation, including widescreen Beamer slides.
