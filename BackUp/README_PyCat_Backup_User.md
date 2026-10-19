# PyCat backup scripts — user-selected folders

These scripts copy the contents of an initial folder into a final folder. Each run asks you to enter both locations in Ubuntu Terminal or Windows Command Prompt (CMD). You do not need to edit the scripts.

**Close PyCat before starting a backup so its SQLite database and attachments are saved consistently.**

## Included files

| System | File | Mode |
|---|---|---|
| Ubuntu / Linux | `backup_ubuntu_pycat_user.sh` | Backup: keep destination-only files |
| Ubuntu / Linux | `backup_ubuntu_pycat_mirror_user.sh` | Mirror: delete destination-only files |
| Windows | `backup_windows_pycat_user.bat` | Backup: keep destination-only files |
| Windows | `backup_windows_pycat_mirror_user.bat` | Mirror: delete destination-only files |

The `_user` suffix means you enter the folders when running the script.

## Backup or mirror?

| Change in the source folder | Backup | Mirror |
|---|---|---|
| New file or subfolder | Copied to destination | Copied to destination |
| Changed file | Previous destination copy is overwritten when detected as changed | Destination copy is updated |
| Deleted file or folder | Old destination copy is kept | Old destination copy is deleted |
| Renamed file or folder | New name is copied; old destination name is kept | New name is copied; old destination name is removed |
| Extra files already in the destination | Kept | Deleted |

**Mirror permanently deletes destination files and folders absent from the source. Choose a dedicated backup folder and check both paths before confirming.** Mirror scripts ask for confirmation; ordinary backup scripts start after the folder checks.

Neither mode keeps a version history of overwritten files. Copying is one-way: these scripts do not synchronize changes back to the source.

## What folders should I enter?

- **Initial folder (source):** the folder containing the current files you want to copy, for example the USB drive's `PyCat` folder.
- **Final folder (destination):** the folder where the backup should be stored.

Enter the complete paths. Paths containing spaces are supported. The source must already exist. A missing destination folder is created when the backup starts, provided you have permission to create it.

The scripts copy the **contents** of the source into the destination. For example, choosing `E:\PyCat` and `C:\Backups\PyCat` puts the database directly in `C:\Backups\PyCat`, without creating another nested `PyCat` folder.

To back up your full catalog, choose the folder containing `PyCat_NMR.py`, `nmr_catalog.db`, `PyCat_NMR_Catalog.csv`, and `NMR_Library`. Hidden files and ordinary subfolders are included.

## Ubuntu / Linux Terminal

### Requirements

The Linux scripts use Bash, rsync, and standard Ubuntu utilities. Install rsync if needed:

```bash
sudo apt update
sudo apt install rsync
```

No Python installation or virtual environment is required for these scripts.

### Run an ordinary backup

Open Terminal and change to the folder containing the downloaded scripts. For example:

```bash
cd ~/Downloads
bash backup_ubuntu_pycat_user.sh
```

At the prompts, enter your paths. For example:

```text
Initial folder (source): /media/vineeth/UBUNTU 24_0/PyCat
Final folder (destination): /home/vineeth/Documents/LSDRM/Bibliography/PyCat
```

Press Enter after each path. Spaces are accepted without quotes; matching surrounding quotes are also supported. The Linux scripts also accept `~` or `~/...` for your home folder.

### Run a mirror backup

```bash
cd ~/Downloads
bash backup_ubuntu_pycat_mirror_user.sh
```

Enter both folder paths, review the displayed locations, then enter `y` to proceed. Enter `n` or press Enter at the confirmation prompt to cancel.

Linux backup mode detects changes using file size and modification time. Linux mirror mode additionally checks file contents using rsync checksums, including changes that retain the same size and modification time. These checks can make mirror mode slower.

The Linux scripts reject identical folders, folders nested inside each other, and filesystem-root paths. They resolve symbolic links when checking the selected locations. Unlike the earlier fixed-path scripts, these versions do not require a particular USB mount location: connect and mount your drive before entering its folder path.

## Windows Command Prompt (CMD)

### Requirements

The Windows scripts use Robocopy, CMD, and Windows PowerShell. No Python installation or virtual environment is required.

### Run an ordinary backup

Open CMD and change to the folder containing the scripts. For example:

```bat
cd /d "%USERPROFILE%\Downloads"
backup_windows_pycat_user.bat
```

Alternatively, double-click the `.bat` file to open its command window.

At the prompts, enter complete paths, for example:

```text
Initial folder (source): E:\PyCat
Final folder (destination): C:\Users\Vineeth\Documents\LSDRM\Bibliography\PyCat
```

Replace the drive letter and user folder with your actual locations. Spaces are supported, and surrounding double quotes are accepted. At these interactive folder prompts, enter full paths rather than variables such as `%USERPROFILE%` or `~`.

### Run a mirror backup

```bat
cd /d "%USERPROFILE%\Downloads"
backup_windows_pycat_mirror_user.bat
```

Enter both paths and review them. Press `Y` to mirror, or `N` to cancel. The window pauses after completion so you can read its messages.

Windows backup mode uses Robocopy's `/E` option to include subfolders and keep destination-only items. Windows mirror mode uses `/MIR` to remove destination-only items and `/IS /IT` to recopy files even when their usual comparison metadata matches. This can make mirror mode slower. Both Windows scripts skip directory junctions to avoid following linked directory trees, so their targets are not included in the mirror.

The Windows scripts reject identical or nested folder paths. The mirror script also rejects drive-root locations. Use normal, separate folders for the source and destination.

## Completion and troubleshooting

Wait for **Backup complete** or **Mirror backup complete** before disconnecting the drive. If a transfer fails, fix the reported problem and run the script again.

| Message or problem | What to do |
|---|---|
| Source folder does not exist | Connect the drive, check its mount location or drive letter, and enter the existing folder path. |
| Missing destination | Enter a full destination folder path; there is no preset default. |
| Destination is not a folder | Choose a directory path rather than an existing file. |
| Identical or nested folders | Choose two separate locations; neither should contain the other. |
| Permission denied | Choose a destination you can write to, and check source-file permissions. |
| rsync not installed | Install it using the Ubuntu commands above. |
| Robocopy exit code 8 or higher | The Windows copy failed or was incomplete. Review the preceding error messages. |

Robocopy codes 0–7 are handled as non-failing results by these scripts. Filesystem permissions, ownership, and platform-specific metadata may differ across drives; these are folder-content backup tools rather than system-image backups.

The Linux transfers were tested using temporary folders. The Windows scripts were structurally checked but were not executed on Windows in the creation environment.
