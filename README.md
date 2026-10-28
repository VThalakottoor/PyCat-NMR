# PyCat NMR v1.0.19

**Python Catalog for NMR**  
**Author:** Vineeth Francis Thalakottoor  
**Contact:** vineeth.thalakottoor@cea.fr

PyCat is a local desktop catalog for papers, books, manuals, theses, lecture notes, conferences, reports, researchers, and websites. It uses Python, Tkinter, and SQLite.

This update uses the uploaded **v1.0.18** program as its base. It adds a **Backup** tab and multiple website links. Existing catalog features, citation support (including RIS), file organization, search behavior, and table/button order are retained.

## Files to keep together

Keep `PyCat_NMR.py`, `nmr_catalog.db`, `PyCat_NMR_Catalog.csv`, and the complete `NMR_Library` folder together. The database and catalog files are created beside the Python program. To update, close PyCat and replace the program file in the existing PyCat folder.

The updated program uses the existing database. Multiple links use the existing `website` field, so no new database columns are required. Keep your database and attachments when replacing the program.

## Setup and running

No additional Python packages are required specifically for Backup or multiple website links. The existing optional packages support previews, image handling, clipboard images, and drag-and-drop.

### Ubuntu / Linux Terminal

Install Python/Tkinter and rsync:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-tk rsync
```

Create and activate an environment:

```bash
python3 -m venv ~/venvs/pycat
source ~/venvs/pycat/bin/activate
python -m pip install --upgrade pip
python -m pip install --upgrade matplotlib pillow tkinterdnd2
```

Change to your actual PyCat folder and run:

```bash
cd "/path/to/PyCat"
python PyCat_NMR.py
```

For later sessions, activate the environment, change to the PyCat folder, and run the program. Use `deactivate` to leave the environment.

For Linux clipboard-image access, install the helper appropriate to your session:

```bash
sudo apt install xclip wl-clipboard
```

For full LaTeX and PDF previews:

```bash
sudo apt install texlive-latex-base texlive-latex-recommended texlive-latex-extra poppler-utils
```

Other Linux distributions use their own package manager for these system tools.

### Windows Command Prompt (CMD)

Install Python with Tcl/Tk support, then create and activate the environment:

```bat
py -m venv "%USERPROFILE%\venvs\pycat"
call "%USERPROFILE%\venvs\pycat\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install --upgrade matplotlib pillow tkinterdnd2
```

Change to your actual PyCat folder and run:

```bat
cd /d "C:\path\to\PyCat"
python PyCat_NMR.py
```

Use the activation command again in each new CMD window. Use `deactivate` when finished.

The Backup tab uses Windows' built-in **Robocopy**. For full LaTeX previews, install a LaTeX distribution and Poppler, make `pdflatex` and `pdftoppm` available on PATH, and restart PyCat.

## Tabs

- **Search Library:** search, filter, open, and select saved entries. Existing table order and action buttons remain in place.
- **Upload / Edit:** create or update catalog entries, attachments, notes, and LaTeX content.
- **ReadMe:** view setup and usage instructions inside the program.
- **Backup:** choose folders, see their sizes, and run a backup or mirror.

## Backup tab

### Inputs and controls

| Control | Meaning |
|---|---|
| Operating system | Choose **Linux** or **Windows**, matching the computer running PyCat. |
| Mode | Choose ordinary Backup or Mirror. |
| Initial folder (source) | The folder containing the current files to copy. |
| Final folder (destination) | The folder where the backup should be stored. |
| Browse… | Select a folder instead of typing its path. |
| Verbose output | Show individual file details in the output panel. When off, show summary output and errors. |
| Start backup | Start copying in the background. |
| Cancel | Stop a running transfer. The destination may be incomplete. |
| Refresh folder sizes | Recalculate both folder sizes. |

Paths may contain spaces. Folder sizes refresh after you edit the paths, and again after a backup completes or stops. A destination that does not exist shows zero bytes and is created when the transfer starts.

Sizes are displayed in **bytes and MiB**, with file counts. They measure the content sizes of regular files, including hidden files, rather than allocated disk space. Symbolic links and directory junctions are excluded from size totals. Unreadable items are reported as a partial size. Size calculations run in the background.

### Backup and mirror modes

| Source change | Backup | Mirror |
|---|---|---|
| New file/folder | Copied | Copied |
| Changed file | Updated when detected as changed | Updated |
| Deleted source file/folder | Previous destination copy is retained | Destination copy is deleted |
| Renamed source file/folder | New name is copied; old destination name remains | New name is copied; old destination name is removed |
| Destination-only files | Retained | Deleted |

**Mirror permanently deletes destination-only files and folders.** The program displays both paths and asks for confirmation before starting a mirror.

Both modes copy in one direction, from initial to final. Changes made in the destination are not copied back to the source. Overwritten files do not have a version history.

### Example: USB to computer

On Linux:

```text
Initial folder: /media/vineeth/UBUNTU 24_0/PyCat
Final folder: /home/vineeth/Documents/LSDRM/Bibliography/PyCat
```

On Windows:

```text
Initial folder: E:\PyCat
Final folder: C:\Users\Vineeth\Documents\LSDRM\Bibliography\PyCat
```

Replace these examples with your actual paths. The contents are copied directly into the final folder; no additional nested PyCat folder is added.

You must run PyCat on the selected operating system. Choosing Windows on a Linux computer does not run a remote Windows backup. These are local folder paths, including mounted drives accessible to that computer.

### Backing up while PyCat is open

1. Click **Add** or **Update** to save any form edits you want in the backup.
2. Open **Backup** and choose the source, destination, mode, and verbosity.
3. Review both paths and click **Start backup**.
4. Wait for **Backup complete** or **Mirror backup complete** before disconnecting a drive.

Catalog editing and the other tabs are temporarily disabled during the transfer. The window remains responsive, and Cancel stays available. If the source includes the running catalog database, PyCat makes a consistent **SQLite snapshot**, copies the other files, then publishes the snapshot at the corresponding destination path. This avoids copying a live SQLite database as an ordinary changing file. Obsolete destination SQLite sidecar files for that database are removed before publishing the snapshot.

Unsaved form text is not automatically saved. Close other PyCat instances or applications that may change the selected folders. The snapshot handling covers this running program's database; other databases in the source should be closed before copying. Live database journal/WAL sidecars are intentionally not copied for this database; a consistent snapshot is used instead, so source and destination byte totals can differ even in Mirror mode.

The destination must be separate from the source. Identical/nested folders, drive/filesystem roots, and destinations containing the running PyCat database are rejected. Do not use a destination that another application has open for writing.

The integrated tab does not need the separate `.sh` or `.bat` scripts. When using the standalone scripts, continue to close PyCat first.

### Copy engines and output

- **Linux:** rsync. Backup mode compares sizes/modification times; Mirror additionally checks content using checksums and uses delayed deletion. Verbose mode lists file changes.
- **Windows:** Robocopy. Backup uses `/E`; Mirror uses `/MIR` and also recopies same-metadata files with `/IS /IT`. Directory junctions are skipped with `/XJ`. Robocopy codes 0–7 are treated as non-failing; other results report an incomplete/failed transfer.

Errors and cancellation are shown in the status/output panel. After cancellation, fix any issue and rerun the backup to finish. The output panel retains the latest 10,000 lines during large verbose transfers. Folder sizes can differ in Backup mode because destination-only files are deliberately retained. Linked directories and platform-specific metadata can also differ; this is a folder-content backup rather than a system-image backup.

## Multiple websites

1. Open **Upload / Edit** and select **Websites**.
2. Enter the required **Title**, **Section**, and **Subsection**.
3. Enter addresses in **Websites (one per line)**, or use **Add website…** repeatedly.
4. Enter any plain-text notes you want to keep.
5. Click **Add** for a new entry or **Update** for an existing one.

Example:

```text
https://www.cnrs.fr
https://www.cea.fr
https://example.org/resources
```

Use **Open website** to open a link in your default browser. With one link, it opens directly. With multiple links, a list appears: select a link and click **Open selected website**, or double-click it. The chooser stays open so you can open another link.

Addresses without a scheme are given `https://` when added or opened. Only HTTP/HTTPS links are opened. The Add website action avoids duplicate normalized links. To edit or remove links, edit their lines in the field and click **Update**.

Existing single-link Conference and Researchers entries remain compatible. Their existing Open website button also supports a list if entered. Existing Websites notes remain unchanged; when the website field is empty, Open website can find HTTP/HTTPS links in old plain-text notes. New links are saved in the existing database website field and included in the automatic CSV.

## Existing catalog workflow

Search Library continues to support field search, type/section/subsection filters, and case/punctuation-insensitive word matching. Upload / Edit retains the existing category-specific fields, multiple lecture PDFs, supplementary files, image/clipboard attachments, BibTeX/RIS metadata handling, plain text, and LaTeX/PDF features.

**Organize Files** and **Delete unused folders…** retain their existing behavior and positions. No unrelated catalog behavior was changed for this release.

## Validation

The Linux copy engine was tested with temporary source/destination folders, ordinary backup, mirror deletion, equal-size/time file changes, hidden files, cancellation, path checks, folder sizes, and a live WAL-mode SQLite snapshot. Website parsing and saved multiple-link entries were checked. Windows command construction was checked; an actual Windows transfer and live desktop UI require testing on your computer.
