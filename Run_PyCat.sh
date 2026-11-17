#!/usr/bin/env bash

cd -- "$(dirname -- "${BASH_SOURCE[0]}")" || exit 1

app=PyCat_NMR.py
if [[ ! -f "$app" ]]; then
    app='PyCat_NMR(7).py'
fi
if [[ ! -f "$app" || ! -f requirements.txt ]]; then
    printf '%s\n' 'Place this launcher, requirements.txt, and PyCat_NMR.py in the same folder.' >&2
    exit 1
fi

venv="$HOME/venv/pycat"
if [[ ! -e "$venv" && -x "$HOME/venvs/pycat/bin/python" ]]; then
    venv="$HOME/venvs/pycat"
fi
venv_python="$venv/bin/python"
version_check='import sys; raise SystemExit(sys.version_info < (3, 9))'

if [[ ! -x "$venv_python" ]]; then
    if ! python3 -c "$version_check"; then
        printf '%s\n' 'Install Python 3.9 or newer, then run this launcher again.' >&2
        exit 1
    fi
    if ! python3 -m venv "$venv"; then
        printf '%s\n' 'On Ubuntu/Debian, install venv support with sudo apt install python3-venv.' >&2
        exit 1
    fi
fi

if ! "$venv_python" -c "$version_check"; then
    printf 'Use Python 3.9 or newer for the PyCat environment at %s.\n' "$venv" >&2
    exit 1
fi
if ! "$venv_python" -c 'import tkinter'; then
    printf '%s\n' 'Install Tkinter for this Python. On Ubuntu/Debian, run sudo apt install python3-tk.' >&2
    exit 1
fi

installed_requirements="$venv/.pycat-requirements.txt"
if [[ ${1:-} == --install ]] || ! cmp -s requirements.txt "$installed_requirements"; then
    printf '%s\n' 'Installing PyCat Python dependencies...'
    if ! "$venv_python" -m pip --version >/dev/null 2>&1 && ! "$venv_python" -m ensurepip --upgrade; then
        printf '%s\n' 'On Ubuntu/Debian, install venv support with sudo apt install python3-venv.' >&2
        exit 1
    fi
    "$venv_python" -m pip install -r requirements.txt || exit 1
    cp -- requirements.txt "$installed_requirements" || exit 1
fi

exec "$venv_python" "$app"
