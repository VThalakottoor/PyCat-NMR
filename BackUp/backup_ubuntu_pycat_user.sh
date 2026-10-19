#!/usr/bin/env bash
# User-selected source and destination folders. Close PyCat before backup.
set -euo pipefail

if ! command -v rsync >/dev/null 2>&1; then
    echo 'Error: rsync is not installed. Install it with: sudo apt install rsync' >&2
    exit 1
fi

echo 'Close PyCat before backing up its database.'
echo 'Enter the full source and destination folder paths. Spaces are supported.'
IFS= read -r -p 'Initial folder (source): ' SOURCE
IFS= read -r -p 'Final folder (destination): ' DESTINATION

clean_path() {
    local value=$1
    if [[ ${#value} -ge 2 ]]; then
        if [[ ( ${value:0:1} == '"' && ${value: -1} == '"' ) ||
              ( ${value:0:1} == "'" && ${value: -1} == "'" ) ]]; then
            value=${value:1:${#value}-2}
        fi
    fi
    case "$value" in
        '~') value=$HOME ;;
        '~/'*) value="$HOME/${value:2}" ;;
    esac
    printf '%s' "$value"
}
SOURCE=$(clean_path "$SOURCE")
DESTINATION=$(clean_path "$DESTINATION")

if [[ -z "$SOURCE" || ! -d "$SOURCE" ]]; then
    echo "Error: source folder does not exist: $SOURCE" >&2
    exit 1
fi
if [[ -z "$DESTINATION" ]]; then
    echo 'Error: enter a destination folder.' >&2
    exit 1
fi
if [[ -e "$DESTINATION" && ! -d "$DESTINATION" ]]; then
    echo 'Error: the destination is not a folder.' >&2
    exit 1
fi

source_real=$(realpath -e -- "$SOURCE")
destination_real=$(realpath -m -- "$DESTINATION")
if [[ "$source_real" == / || "$destination_real" == / ||
      "$source_real" == "$destination_real" ||
      "$source_real" == "$destination_real/"* ||
      "$destination_real" == "$source_real/"* ]]; then
    echo 'Error: choose separate folders, neither inside the other, and not a filesystem root.' >&2
    exit 1
fi

echo "Source:      $source_real/"
echo "Destination: $destination_real/"

echo 'Copies new and changed files; destination-only items are kept.'
mkdir -p -- "$destination_real"
rsync -rlt --partial --human-readable --info=progress2,stats2 \
    -- "$source_real/" "$destination_real/"
echo 'Backup complete.'
