# PyCat NMR

### Python Catalog for NMR

PyCat NMR is a cross-platform desktop application for organizing NMR papers and books. It stores bibliographic information in a local SQLite database, organizes PDFs and related files into a structured library, and provides fast searching by title, author, keyword, section, and subsection.

The application works locally on Windows, macOS, and Linux. No internet connection is required for its cataloging features.

## Author

Vineeth Francis Thalakottoor

## Features

- Catalog NMR papers and books
- Import one or many references from BibTeX files
- Store titles, authors, years, journals, publishers, DOI, ISBN, and keywords
- Record corresponding-author names and email addresses
- Add editable notes to each reference
- Automatically create a readable `Notes.txt` file
- Attach PDFs, BibTeX files, and images
- Open PDFs, BibTeX files, notes, and entry folders from the application
- Organize files by section, subsection, corresponding author, and title
- Search by title, author, keyword, section, or subsection
- Filter papers and books separately
- Use linked Section and Subsection dropdown filters
- Automatically maintain a spreadsheet-readable CSV catalog
- Preserve all catalog information in a local SQLite database

## Library structure

Uploaded files are organized using the following structure:

```text
NMR_Library/
â””â”€â”€ Section/
    â””â”€â”€ Subsection/
        â””â”€â”€ Corresponding author/
            â””â”€â”€ Paper or book title/
                â”œâ”€â”€ paper.pdf
                â”œâ”€â”€ reference.bib
                â”œâ”€â”€ Notes.txt
                â””â”€â”€ attached-images
```

## Requirements

- Python 3.9 or later
- Tkinter

All other modules used by the current version are included with Python's standard library.

## Installation

### Ubuntu or Debian

```bash
sudo apt update
sudo apt install python3 python3-tk
```

### Fedora, AlmaLinux, or RHEL

```bash
sudo dnf install python3 python3-tkinter
```

### Windows

Install Python from [python.org](https://www.python.org/downloads/) and enable **Add Python to PATH** during installation. Tkinter is included with the standard Windows Python installer.

### macOS

Install Python from [python.org](https://www.python.org/downloads/macos/). The standard installer includes Tkinter.

## Running PyCat NMR

Clone or download the repository, enter its directory, and run:

```bash
python3 NMR_Catalog.py
```

On Windows, use:

```powershell
py NMR_Catalog.py
```

## Using the catalog

1. Open the **Upload / Edit** tab.
2. Enter the paper or book information.
3. Choose a Section and Subsection.
4. Attach the PDF, BibTeX file, or images if available.
5. Add keywords and notes.
6. Click **Add**.

To modify an entry, select it in **Search Library**, click **Edit Selected**, make the changes, and click **Update**.

## BibTeX import

Click **Import BibTeX** and select a `.bib` file. PyCat NMR reads common bibliographic fields, including:

- Title
- Authors
- Year
- Journal, book title, or publisher
- Volume, issue, and pages
- DOI or ISBN
- Keywords
- Abstract or notes

Duplicate entries are detected using the title or DOI.

## Search and filtering

The catalog supports free-text searching and field-specific searching. The Section dropdown contains all created sections. After selecting a section, the Subsection dropdown shows only subsections belonging to it.

## Data files

PyCat NMR creates the following files beside the program:

- `nmr_catalog.db` â€” primary SQLite database
- `PyCat_NMR_Catalog.csv` â€” automatically synchronized catalog table
- `NMR_Library/` â€” default document library

The `.db` file is a binary SQLite database and should not be opened or edited with a normal text editor.

## Backups

Back up the following items together:

```text
nmr_catalog.db
PyCat_NMR_Catalog.csv
NMR_Library/
```

## Privacy

The current version stores its database, metadata, notes, and documents locally. It does not upload papers or catalog information to an online service.

## Planned development

- Optional offline question answering for selected papers and books
- OCR support for scanned documents
- Equation and experimental-parameter extraction
- Packaged installers for Windows, macOS, and Linux
