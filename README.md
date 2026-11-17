# PyCat NMR

PyCat NMR is a desktop application for cataloging NMR papers, books, manuals, theses, reports, and notes.

## Before you start

Put these files in the same folder:

- `PyCat_NMR.py`
- `requirements.txt`
- `Run_PyCat.sh` for Linux or `Run_PyCat.bat` for Windows

If your downloaded Python script has a numbered name such as `PyCat_NMR(9).py`, rename it to `PyCat_NMR.py`. If you already have a catalog, keep your existing database and attachment folder beside the script.

## Linux

You need Python 3.9 or newer with `venv` and Tkinter. On Ubuntu or Debian, run the following **only if these prerequisites are missing**. If PyCat already opens using your existing `pycat` environment, skip this step.

```bash
sudo apt update
sudo apt install python3 python3-venv python3-tk
```

Open a terminal in your PyCat folder and run:

```bash
bash Run_PyCat.sh
```

## Windows

1. Install Python 3.9 or newer with Tcl/Tk support if you need to set up Python.
2. Open your PyCat folder and double-click **Run_PyCat.bat**.

You can also run `Run_PyCat.bat` from Command Prompt in the PyCat folder.

## What the launcher does

The launcher reuses your existing `pycat` environment or creates one at the default location below.

| System | Default environment |
| --- | --- |
| Linux | `~/venv/pycat` |
| Windows | `%USERPROFILE%\venv\pycat` |

It also recognizes an existing `venvs/pycat` environment when the default folder is absent. The launcher uses the environment’s Python directly, so you can skip manual activation.

On first run, the launcher uses `pip` to install Matplotlib, Pillow, and tkinterdnd2 from `requirements.txt`. Have an internet connection available for the initial package download. Once setup succeeds, PyCat can launch offline. The launcher runs the install step again when `requirements.txt` changes.

To rerun that step, use the corresponding command in the PyCat folder.

**Linux**

```bash
bash Run_PyCat.sh --install
```

**Windows Command Prompt**

```bat
Run_PyCat.bat --install
```

## Optional features

- **Full LaTeX previews** use `pdflatex` and `pdftoppm`. On Ubuntu or Debian, install them with `sudo apt install texlive-latex-base texlive-latex-recommended texlive-latex-extra poppler-utils`. On Windows, install a LaTeX distribution and Poppler, and put both commands on PATH. Quick equation previews use Matplotlib.
- **Pasting images from the Linux clipboard** can use `xclip` on X11 or `wl-paste` on Wayland. On Ubuntu or Debian, install these with `sudo apt install xclip wl-clipboard`.

## Keep your catalog together

For a backup or a move to another computer, close PyCat and copy the whole PyCat folder, including `nmr_catalog.db`, `PyCat_NMR_Catalog.csv`, and `NMR_Library` if present. Run the launcher on each computer so it uses that computer’s own Python environment.
