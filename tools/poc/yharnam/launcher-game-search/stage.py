#!/usr/bin/env python3
"""Fail-closed permission guard for source-pinned native YT game discovery.

Discovered by actual YT PR429 native launcher GitHub CI 40551081103:
stock is_game_folder -> Path(.../eboot.bin).is_file() can raise PermissionError
on inaccessible directory. It must skip and keep searching, not fail setup.
Never modify game folders, files, installation or saves; only disposable checkout.
"""
from pathlib import Path
import argparse
import subprocess

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
FILE = "bbport/launcher/bbport_coop.py"
BLOB = "9c54b2cd577b1fd4d50cd500c64c0b9d0f1e8b24"

OLD_IS_GAME = """def is_game_folder(folder):
    return (Path(folder) / 'eboot.bin').is_file()
"""
NEW_IS_GAME = """def is_game_folder(folder):
    # A nearby folder or a drive can contain inaccessible system directories.
    # Path.is_file may raise PermissionError, especially on restricted Windows
    # folders and Linux runners. Keep searching instead of breaking setup.
    try:
        return (Path(folder) / 'eboot.bin').is_file()
    except OSError:
        return False
"""

OLD_FIND = """    folder = Path(folder)
    if not folder.is_dir():
        return None
    if is_game_folder(folder):"""
NEW_FIND = """    folder = Path(folder)
    try:
        if not folder.is_dir():
            return None
    except OSError:
        return None
    if is_game_folder(folder):"""

OLD_FIRST = """        found = find_game_folder(folder, 2) if folder and Path(folder).is_dir() else None
        if found and is_bloodborne(found):
            return found"""
NEW_FIRST = """        # find_game_folder already handles missing / inaccessible roots.
        found = find_game_folder(folder, 2) if folder else None
        if found and is_bloodborne(found):
            return found"""


def patch_text(before: str) -> str:
    for old, new in ((OLD_IS_GAME, NEW_IS_GAME), (OLD_FIND, NEW_FIND),
                     (OLD_FIRST, NEW_FIRST)):
        if before.count(old) != 1:
            raise ValueError("Ambiguous or drifted original game-search path")
        before = before.replace(old, new)
    return before


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True).strip()


def run(root: Path) -> None:
    root = root.resolve()
    if git(root, "rev-parse", "HEAD") != PIN:
        raise ValueError("Wrong original YT1.3.0 revision; no writes")
    if git(root, "rev-parse", "HEAD:" + FILE) != BLOB:
        raise ValueError("Unexpected native launcher original blob; no writes")
    if git(root, "status", "--porcelain"):
        raise ValueError("No dirty original upstream tree allowed")
    path = root / FILE
    changed = patch_text(path.read_text(encoding="utf-8"))
    path.write_text(changed, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("YT130_GAME_SEARCH_PERMISSION_GUARD_DISPOSABLE_ONLY")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("disposable_yt130_checkout", type=Path)
    run(p.parse_args().disposable_yt130_checkout)
