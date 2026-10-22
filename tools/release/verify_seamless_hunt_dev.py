"""Verify a self-contained native Windows developer ZIP before publishing it.

No code execution or extraction. Refuses game assets, user data, traversal,
duplicate/case-colliding paths, missing licenses/runtime, and bad file hashes.
A passing verdict is package integrity, NOT proof of multiplayer/gameplay.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

REQUIRED = frozenset({
    "out/bbport.exe", "launch_gui.bat", "run.bat", "launcher.py",
    "python/python.exe", "python/pythonw.exe", "python/python312.dll",
    "python/LICENSE.txt", "python/LICENSE-tcltk.txt",
    "python/Lib/tkinter/__init__.py", "python/DLLs/_tkinter.pyd",
    "python/tcl/tk8.6/tk.tcl", "patches/Bloodborne.xml",
    "out/licenses/LICENSE",
})
ALLOWED_TOP = frozenset({"out", "python", "scripts", "patches", "launcher",
                         "licenses", "docs", "tools", "VERSION", "LICENSE",
                         "README.md", "README.ru.md", "CHANGELOG.md", "launch_gui.bat",
                         "run.bat", "launcher.py", "MANIFEST.json",
                         "README-DEVELOPER-BUILD.txt"})
DENIED_PARTS = frozenset({"user", "savedata", "save", "secrets", "mods", ".git",
                          ".github", "site-packages", "logs", "__MACOSX"})
MAX_ENTRY_BYTES = 512 * 1024 * 1024
MAX_CONTENT_BYTES = 3 * 1024 * 1024 * 1024
REVISION = re.compile(r"[0-9a-f]{40}\Z")


def _legal(path: str) -> bool:
    if not path or "\\" in path or path.startswith("/") or ":" in path:
        return False
    parts = path.split("/")
    if any(x in ("", ".", "..") or x.endswith((" ", ".")) or
           any(ord(ch) < 32 for ch in x) for x in parts):
        return False
    if parts[0] not in ALLOWED_TOP or any(x in DENIED_PARTS for x in parts):
        return False
    if parts[0] == "out" and len(parts) > 2 and parts[1] != "licenses":
        return False
    return True


def verify(path: Path) -> dict:
    if not path.is_file():
        raise ValueError("missing Windows package")
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if len(members) < len(REQUIRED) + 2 or len(members) > 100000:
            raise ValueError("invalid file count")
        by_name: dict[str, zipfile.ZipInfo] = {}
        names_casefold: set[str] = set()
        total = 0
        for info in members:
            name = info.filename
            if not _legal(name):
                raise ValueError(f"unsafe package path: {name!r}")
            low = name.casefold()
            if low in names_casefold:
                raise ValueError("duplicate/case-colliding package path")
            names_casefold.add(low)
            if info.is_dir() or (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError(f"directory or symlink member forbidden: {name}")
            if info.flag_bits & 1:
                raise ValueError("encrypted package entry is forbidden")
            if info.file_size > MAX_ENTRY_BYTES:
                raise ValueError(f"oversized package entry: {name}")
            total += info.file_size
            if total > MAX_CONTENT_BYTES:
                raise ValueError("package exceeds decompressed content limit")
            by_name[name] = info
        if not REQUIRED <= by_name.keys():
            raise ValueError(f"missing runtime entrypoints: {sorted(REQUIRED - by_name.keys())}")
        try:
            manifest = json.loads(archive.read("MANIFEST.json"))
        except (ValueError, KeyError) as exc:
            raise ValueError("invalid manifest") from exc
        if manifest.get("format") != "seamless-hunt-native-windows-dev-v2":
            raise ValueError("unsupported package schema; Python runtime required")
        revision = manifest.get("source_commit")
        if not isinstance(revision, str) or not REVISION.fullmatch(revision):
            raise ValueError("invalid source revision")
        records = manifest.get("files")
        if not isinstance(records, list):
            raise ValueError("missing file inventory")
        expected = set(by_name) - {"MANIFEST.json", "README-DEVELOPER-BUILD.txt"}
        if len(records) != len(expected):
            raise ValueError("file inventory count mismatch")
        seen = set()
        for record in records:
            if not isinstance(record, dict):
                raise ValueError("invalid file record")
            name = record.get("path")
            if not isinstance(name, str) or name not in expected or name in seen:
                raise ValueError("unlisted or repeated inventory entry")
            seen.add(name)
            info = by_name[name]
            if not isinstance(record.get("bytes"), int) or record["bytes"] != info.file_size:
                raise ValueError(f"byte count mismatch: {name}")
            digest = record.get("sha256")
            if not isinstance(digest, str) or not re.fullmatch("[0-9a-f]{64}", digest):
                raise ValueError(f"invalid hash: {name}")
            h = hashlib.sha256()
            with archive.open(info) as fp:
                for chunk in iter(lambda: fp.read(1024 * 1024), b""):
                    h.update(chunk)
            if h.hexdigest() != digest:
                raise ValueError(f"package content hash mismatch: {name}")
        if seen != expected:
            raise ValueError("package contains unlisted files")
        return {"source_commit": revision, "files_verified": len(records),
                "uncompressed_bytes": total, "portable_python": True,
                "game_files_included": False, "live_coop_verified": False}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--zip", type=Path, required=True)
    args = p.parse_args()
    try:
        print(json.dumps(verify(args.zip), sort_keys=True))
    except (OSError, ValueError, zipfile.BadZipFile) as ex:
        p.error(str(ex))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
