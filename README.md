# PyCat NMR

### Python Catalog for NMR

PyCat NMR is a cross-platform desktop application for organizing NMR papers and books. It stores bibliographic information in a local SQLite database, organizes PDFs and related files into a structured library, and provides fast searching by title, author, keyword, section, and subsection.

The application works locally on Windows, macOS, and Linux. No internet connection is required for its cataloging features.

## Author

**Vineeth Francis Thalakottoor**  
[vineeth.thalakottoor@cea.fr](mailto:vineeth.thalakottoor@cea.fr)

## Features

- Catalog NMR papers and books
- Import one or many references from BibTeX files
- Store titles, authors, years, journals, publishers, DOI, ISBN, and keywords
- Record corresponding-author names and email addresses
- Add editable notes to each reference
- Automatically create a readable `Notes.txt` file
- Attach PDFs, supplementary files, BibTeX files, and images
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
└── Section/
    └── Subsection/
        └── Corresponding author/
            └── Paper or book title/
                ├── paper.pdf
                ├── reference.bib
                ├── Notes.txt
                ├── supplementary_information.pdf
                ├── experimental_data.xlsx
                ├── additional_methods.docx
                ├── supplementary_archive.zip
                └── attached_figure.png
```

Each paper or book has its own folder. The main PDF, BibTeX reference, notes, images, and supplementary material are therefore kept together with the corresponding catalog entry.

One entry can contain multiple supplementary files. PyCat NMR accepts PDF, Word, Excel, CSV, TXT, ZIP, image, and other file formats. It copies the selected files into the paper's folder, preserves recognizable filenames, and records all file locations in both `nmr_catalog.db` and the automatically updated `PyCat_NMR_Catalog.csv` file.

Additional supplementary files can be attached later without deleting the previously stored files. Select the paper in **Search Library** and click **Open Supplementary** to open all available supplementary files using their default applications.

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

## Supplementary files

Each paper or book can have one or more supplementary files. In the **Upload / Edit** tab, click **Supplement...** and select the required files. Supported selections include PDF, Word, Excel, CSV, text, ZIP, and other document formats.

PyCat NMR copies the selected files into the same organized folder as the main paper and stores their locations in the SQLite database and automatic CSV catalog. Additional supplementary files can be attached later without removing the existing ones.

To access them, select the catalog entry in **Search Library** and click **Open Supplementary**. PyCat NMR opens every available supplementary file using the computer's default application.

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

- `nmr_catalog.db` — primary SQLite database
- `PyCat_NMR_Catalog.csv` — automatically synchronized catalog table
- `NMR_Library/` — default document library

The `.db` file is a binary SQLite database and should not be opened or edited with a normal text editor.

## Backups

Back up the following items together:

```text
nmr_catalog.db
PyCat_NMR_Catalog.csv
NMR_Library/
```

## License

PyCat NMR is released under the [MIT License](LICENSE).


