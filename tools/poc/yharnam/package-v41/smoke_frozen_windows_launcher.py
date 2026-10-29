#!/usr/bin/env python3
"""Native frozen BLauncher functional smoke, run ONLY on Windows CI.

Verifies a standalone ZIP really starts its included BLauncher.exe and
runs a UTF-8 script from a Cyrillic path, without game assets, credentials,
network connections or installing anything globally.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

SCRIPT = (
    "from pathlib import Path\n"
    "import sys\n"
    "marker = Path(sys.argv[1])\n"
    "marker.write_text('SHYT\\N{CYRILLIC CAPITAL LETTER YA}\\N{CYRILLIC SMALL LETTER A}=' "
    "'OK\\n', encoding='utf-8')\n"
    "print('SHYT_LAUNCHER_UTF8_\\N{CYRILLIC CAPITAL LETTER YA}=' "
    "'OK', flush=True)\n"
)
EXPECTED_MARKER = "SHYTЯа=OK\n"
EXPECTED_STDOUT = "SHYT_LAUNCHER_UTF8_Я=OK"
ROOT = "bbport-windows/"
MAX_ZIP_FILES = 18000
MAX_EXTRACT = 3 * 1024**3


def inspect_archive(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if not infos or len(infos) > MAX_ZIP_FILES:
            raise ValueError("empty or excessive launcher ZIP")
        names = {x.filename for x in infos}
        if ROOT + "BLauncher.exe" not in names:
            raise ValueError("BLauncher.exe is missing")
        if archive.testzip() is not None:
            raise ValueError("bad game archive CRC")
        if sum(x.file_size for x in infos) > MAX_EXTRACT:
            raise ValueError("extraction volume too large")
        seen = set()
        for f in infos:
            parts = f.filename.rstrip("/").split("/")
            if (not f.filename.startswith(ROOT) or not f.filename.isascii()
                    or "\\" in f.filename or ":" in f.filename
                    or "\x00" in f.filename or ".." in parts
                    or any(not p for p in parts)):
                raise ValueError("unsafe ZIP path")
            if stat.S_IFMT(f.external_attr >> 16) == stat.S_IFLNK:
                raise ValueError("ZIP contains symbolic link")
            if f.is_dir():
                continue
            folded = f.filename.casefold()
            if folded in seen:
                raise ValueError("duplicate Windows-case-insensitive ZIP entry")
            seen.add(folded)


def digest_file(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for piece in iter(lambda: source.read(1024 * 1024), b""):
            value.update(piece)
    return value.hexdigest()


def smoke(package: Path, *, timeout: int = 65) -> dict:
    if sys.platform != "win32":
        raise RuntimeError("The actual BLauncher.exe must execute on a Windows runner")
    inspect_archive(package)
    # Fresh Unicode folder exercises launcher path handling in a default
    # Western codepage, without touching the system-wide codepage or registry.
    with tempfile.TemporaryDirectory(prefix="shyt-blauncher-") as tmp:
        install = Path(tmp) / "Установленный Ярнам"
        with zipfile.ZipFile(package) as archive:
            archive.extractall(install)
        game = install / ROOT
        executable = game / "BLauncher.exe"
        testdir = Path(tmp) / "Проверка запуска"
        testdir.mkdir(parents=True)
        script = testdir / "скрипт-проверки.py"
        marker = testdir / "результат.txt"
        script.write_text(SCRIPT, encoding="utf-8")
        result = subprocess.run(
            [str(executable), "--script", str(script), str(marker)],
            cwd=game,
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        if result.returncode != 0:
            # Avoid logging Windows machine environment and private paths.
            raise RuntimeError(f"BLauncher script role exit={result.returncode}; "
                               "consult native runner log in protected CI")
        if not marker.is_file() or marker.read_text(encoding="utf-8") != EXPECTED_MARKER:
            raise RuntimeError("frozen Windows BLauncher Unicode script role did not execute")
        stdout = result.stdout.decode("utf-8", errors="strict")
        if EXPECTED_STDOUT not in stdout:
            raise RuntimeError("frozen Windows BLauncher child stdio did not emit UTF-8")
    return {
        "verified": True,
        "launcher": ROOT + "BLauncher.exe",
        "script_from_cyrillic_path": True,
        "stdio_utf8": True,
        "game_assets_tested": False,
        "real_online_tested": False,
        "direct_p2p_tested": False,
        "package_sha256": digest_file(package),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("windows_zip", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    info = smoke(args.windows_zip)
    result = json.dumps(info, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result, encoding="utf-8")
    print("SHYT_FROZEN_BLAUNCHER_UNICODE_WINDOWS_SMOKE_PASS")
    print(result)


if __name__ == "__main__":
    main()
