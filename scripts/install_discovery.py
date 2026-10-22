"""Read-only, bounded discovery of user-owned Bloodborne installations and data.

Supports regional CUSA editions, PS4/shadPS4 save locations, native PC ports,
and custom launcher directories. Discovers; NEVER migrates, edits, decrypts,
converts saves, updates game files, downloads mods or guesses compatibility.

Default fast scan checks known installations and shallow named folder roots.
Manual additional roots can be supplied when a dump is stored elsewhere.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import re
import sys
from typing import Iterable

CUSA = re.compile(r"^CUSA[0-9]{5}$", re.IGNORECASE)
SAVED_FILES = ("userdata0000", "userdata0010", "backup0000", "backup0010")
GAME_FOLDERS = ("Bloodborne", "Bloodborne GOTY", "Bloodborne PC", "BB", "CUSA03173",
                "CUSA00900", "CUSA00207", "CUSA00208", "CUSA00299", "CUSA01363",
                "CUSA03179", "CUSA03014", "CUSA03023")
LIBRARY_FOLDERS = ("games", "Games", "game", "PS4", "ps4", "roms", "ROMs",
                   "Bloodborne", "Bloodborne PC", "shadPS4", "shadps4",
                   "Awaken", "LanternEngine", "BBPort", "BBHost", "Yharnam Together")
SKIP = frozenset(("windows", "program files", "program files (x86)",
                  "system volume information", "$recycle.bin", "node_modules",
                  ".git", "shader", "cache", "logs", "temp", "tmp", "downloads"))
MAX_NODES = 1500
MAX_DEPTH = 3
MAX_USER_ROOTS = 16


@dataclass(frozen=True)
class Game:
    folder: str
    title_id: str
    app_version: str
    title: str
    executable_bytes: int
    status: str
    reason: str


@dataclass(frozen=True)
class Save:
    folder: str
    source: str
    title_id: str
    files: int
    compatibility: str


@dataclass(frozen=True)
class Extra:
    folder: str
    kind: str
    source: str
    count: int


def _canon(path: Path) -> str:
    return os.path.normcase(str(path.resolve(strict=False)))


def _dir(path: Path) -> bool:
    try:
        return path.is_dir() and not path.is_symlink() and not path.is_junction()
    except (OSError, AttributeError):
        return path.is_dir() and not path.is_symlink()


def _children(path: Path):
    try:
        # Scandir is cheap; skip symlinks and junctions so we never traverse
        # drive mappings or infinitely nested user-created links.
        with os.scandir(path) as entries:
            return [Path(item.path) for item in entries
                    if item.is_dir(follow_symlinks=False) and
                    not (item.stat(follow_symlinks=False).st_file_attributes & 0x400
                         if os.name == "nt" else False)]
    except (PermissionError, FileNotFoundError, OSError):
        return []


def _game_info(root: Path) -> Game | None:
    executable = root / "eboot.bin"
    try:
        if not executable.is_file() or executable.is_symlink():
            return None
        size = executable.stat().st_size
        if size < 16:
            return None
        sfo_path = root / "sce_sys" / "param.sfo"
        info = {}
        if sfo_path.is_file() and not sfo_path.is_symlink() and sfo_path.stat().st_size < 1024*1024:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from prepare import sfo
            try:
                info = sfo(sfo_path.read_bytes())
            except (ValueError, IndexError, KeyError, UnicodeError, OSError):
                info = {}
        title_id = str(info.get("TITLE_ID", "")).upper()
        version = str(info.get("APP_VER", ""))
        title = str(info.get("TITLE", ""))
        # Never treat random eboot.bin as Bloodborne. A CUSA folder is only a
        # hint; SFO title+identity must identify a Bloodborne retail edition.
        from game_check import SUPPORTED_TITLES, SUPPORTED_VERSION
        id_valid = title_id in SUPPORTED_TITLES
        folder_hint = root.name.upper() in SUPPORTED_TITLES
        name_valid = "bloodborne" in title.casefold()
        if not id_valid and not (folder_hint and not title_id):
            return None
        if not id_valid and not name_valid:
            return None
        if version in (SUPPORTED_VERSION, "1.09", "01.09"):
            status = "candidate_109"
            reason = "Retail edition identified; exact executable hash is checked before launch"
        elif not version:
            status = "unverified"
            reason = "Missing/unreadable param.sfo: version and original executable unverified"
        else:
            status = "unsupported_patch"
            reason = f"Detected update {version}; current native game hooks require verified 1.09 image"
        return Game(str(root.resolve()), title_id or root.name.upper(), version,
                    title[:100], size, status, reason)
    except (OSError, ValueError):
        return None


def _drive_roots() -> list[Path]:
    if os.name != "nt":
        return []
    # Directories only, not all of C:\. No volume-wide recursive search.
    return [Path(f"{letter}:\\") for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ"
            if Path(f"{letter}:\\").is_dir()]


def _hints(launcher_dir: Path, extra_roots: Iterable[Path]) -> list[Path]:
    base = Path(launcher_dir)
    home = Path.home()
    roots = [base, base.parent, home / "Documents", home / "Desktop",
             home / "Downloads"]
    for name in ("BB_GAME_DIR", "BB_MODS_DIR", "BB_PATCHES_DIR", "BB_CHEATS_DIR"):
        if os.environ.get(name):
            item = Path(os.environ[name])
            roots.append(item.parent if item.is_file() else item)
    roots.extend(Path(p) for p in list(extra_roots)[:MAX_USER_ROOTS])
    roots.extend(_drive_roots())
    for key in ("APPDATA", "LOCALAPPDATA"):
        if os.environ.get(key):
            roots.append(Path(os.environ[key]) / "shadPS4")
    return roots


def find_games(launcher_dir: Path, extra_roots=()) -> list[Game]:
    bases = _hints(launcher_dir, extra_roots)
    # Breadth-first scan *only* known likely game library folder names,
    # with limited depth and a strict global visit budget.
    queue = [(p, 0) for p in bases]
    visited: set[str] = set()
    games = []
    while queue and len(visited) < MAX_NODES:
        path, depth = queue.pop(0)
        if not _dir(path):
            continue
        key = _canon(path)
        if key in visited:
            continue
        visited.add(key)
        candidate = _game_info(path)
        if candidate:
            games.append(candidate)
            continue
        if depth >= MAX_DEPTH:
            continue
        for child in _children(path):
            name = child.name
            named_game = name.upper() in GAME_FOLDERS or bool(CUSA.fullmatch(name))
            named_library = name.casefold() in {x.casefold() for x in LIBRARY_FOLDERS}
            if named_game or named_library or (depth == 0 and name.casefold() not in SKIP):
                queue.append((child, depth + 1))
    return sorted(games, key=lambda x: (x.status != "candidate_109", x.folder.casefold()))


def _walk_save_groups(root: Path, source: str):
    """Read-only locations with either native user data or PS4 title/user ID."""
    if not _dir(root):
        return []
    candidates = [(root, 0)]
    out = []
    seen = set()
    while candidates:
        path, depth = candidates.pop(0)
        if not _dir(path) or _canon(path) in seen:
            continue
        seen.add(_canon(path))
        try:
            children = _children(path)
            files = [x for x in path.iterdir()
                     if x.is_file() and x.name.lower() in SAVED_FILES]
        except OSError:
            continue
        if files:
            title = next((x.upper() for x in path.parts if CUSA.fullmatch(x)), "")
            out.append(Save(str(path.resolve()), source, title, len(files),
                            "Detected only: copy/convert requires format and region validation"))
        if depth >= 5 or len(seen) > 650:
            continue
        for child in children:
            if child.name.lower() in ("savedata", "savedata_party", "world_warper",
                                     "home", "user", "1000", "1", "sprj0005") or
               CUSA.fullmatch(child.name) or child.name.isdigit() or depth == 0:
                candidates.append((child, depth+1))
    return out


def find_saves(launcher_dir: Path, games=(), extra_roots=()) -> list[Save]:
    base = Path(launcher_dir)
    roots = [(base / "user" / "savedata", "native:pc"),
             (base / "user" / "savedata_party", "native:party"),
             (base / "user" / "world_warper" / "savedata", "native:warper")]
    for root in _hints(base, extra_roots):
        roots.extend([(root / "user" / "savedata", "native-or-shadps4:portable"),
                      (root / "user" / "savedata_party", "native:party"),
                      (root / "savedata", "shadps4-or-pc"),
                      (root / "home" / "1000" / "savedata", "shadps4:home"),
                      (root / "user" / "home" / "1000" / "savedata", "shadps4:portable-home")])
    for key in ("APPDATA", "LOCALAPPDATA"):
        if os.environ.get(key):
            folder = Path(os.environ[key]) / "shadPS4"
            roots.extend([(folder / "savedata", "shadps4:roaming"),
                          (folder / "user" / "savedata", "shadps4:roaming"),
                          (folder / "home" / "1000" / "savedata", "shadps4:new-home")])
    out = {}
    for path, tag in roots:
        if _dir(path):
            for save in _walk_save_groups(path, tag):
                out.setdefault(_canon(Path(save.folder)), save)
    return sorted(out.values(), key=lambda s: (s.source, s.folder.casefold()))


def find_extras(launcher_dir: Path, games=(), extra_roots=()) -> list[Extra]:
    base = Path(launcher_dir)
    roots = [base, *(Path(p) for p in list(extra_roots)[:MAX_USER_ROOTS])]
    roots += [Path(x.folder) for x in games]
    for hint in _hints(base, extra_roots):
        # Do not recurse into downloads or game asset trees.
        if hint.name.casefold() in ("shadps4", "bbport", "bloodborne pc", "lanternengine"):
            roots.append(hint)
    found = {}
    for root in roots:
        for kind, aliases in {
            "mods": ("mods", "mod"),
            "patches": ("patches", "patch"),
            "cheats": ("cheats", "cheat"),
        }.items():
            for name in aliases:
                p = root / name
                if not _dir(p):
                    continue
                try:
                    count = sum(1 for x in p.iterdir() if not x.is_symlink())
                except OSError:
                    continue
                if count:
                    found.setdefault(_canon(p), Extra(str(p.resolve()), kind,
                                                       "existing user content; NOT imported", count))
    return sorted(found.values(), key=lambda x: (x.kind, x.folder.casefold()))


def scan(launcher_dir: Path, extra_roots=()) -> dict:
    games = find_games(launcher_dir, extra_roots)
    return {"games": [asdict(x) for x in games],
            "saves": [asdict(x) for x in find_saves(launcher_dir, games, extra_roots)],
            "extras": [asdict(x) for x in find_extras(launcher_dir, games, extra_roots)],
            "read_only": True, "saves_migrated": False,
            "all_patch_versions_supported": False,
            "notice": "Detection != validated executable, save conversion or live online compatibility."}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--launcher-dir", type=Path,
                   default=Path(__file__).resolve().parent.parent)
    p.add_argument("--search-root", type=Path, action="append", default=[])
    args = p.parse_args()
    print(json.dumps(scan(args.launcher_dir, args.search_root), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
