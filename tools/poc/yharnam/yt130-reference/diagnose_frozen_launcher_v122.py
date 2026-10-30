#!/usr/bin/env python3
"""Windows-only bounded diagnostic of genuine frozen YT1.3 BLauncher.exe.

Uses the exact pinned internal ZIP, starts two harmless --script subprocesses,
reports whether a marker is written, whether the EXE exits, and whether the
child stdout pipe closes. No game data, login, network or production access.
Does NOT convert a failed live smoke into a successful release check.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from zipfile import ZipFile

EXPECTED_HASH = "ee077748b3762db928d06718eea701fb1b0d0cedb0a3eac112bb9040ff0081bc"
SCRIPT = (
    "from pathlib import Path\n"
    "import sys\n"
    "Path(sys.argv[1]).write_text('YT-EXEC-OK', encoding='utf-8')\n"
    "print('YT-STDOUT-OK', flush=True)\n"
)


def probe(exe: Path, game: Path, root: Path, *, label: str) -> dict:
    work = root / label
    work.mkdir(parents=True)
    script = work / "run.py"
    result_path = work / "marker.txt"
    script.write_text(SCRIPT, encoding="utf-8")
    started = time.monotonic()
    command = [str(exe), "--script", str(script), str(result_path)]
    proc = subprocess.Popen(
        command, cwd=game, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    timed_out = False
    exit_before_kill = None
    try:
        out, err = proc.communicate(timeout=25)
        exit_before_kill = proc.returncode
    except subprocess.TimeoutExpired:
        timed_out = True
        exit_before_kill = proc.poll()
        # Only the isolated child PID and its descendants, never a production
        # service or any other test process.
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True, timeout=10, check=False)
        if proc.poll() is None:
            proc.kill()
        try:
            out, err = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            out, err = b"", b""
            for pipe in (proc.stdout, proc.stderr):
                if pipe:
                    pipe.close()
    marker = result_path.is_file() and result_path.read_text(
        encoding="utf-8", errors="replace"
    ) == "YT-EXEC-OK"
    # Only print bounded generic evidence. Never disclose runner environment.
    return {
        "label": label,
        "installation_has_cyrillic": "Ярнам" in str(game),
        "script_has_cyrillic": "Ярнам" in label,
        "marker_written": bool(marker),
        "exit_before_kill": exit_before_kill,
        "timed_out": timed_out,
        "elapsed_s": round(time.monotonic() - started, 3),
        "stdout_contains_expected": b"YT-STDOUT-OK" in out,
        "stdout_bytes": len(out),
        "stderr_bytes": len(err),
    }


def main() -> None:
    if sys.platform != "win32":
        raise RuntimeError("This test requires real native Windows BLauncher.exe")
    p = argparse.ArgumentParser()
    p.add_argument("zip_file", type=Path)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    import hashlib
    h = hashlib.sha256(args.zip_file.read_bytes()).hexdigest()
    if h != EXPECTED_HASH:
        raise ValueError("Unexpected original Windows kit SHA256")
    with tempfile.TemporaryDirectory(prefix="shyt-yt130-v122-") as tmp:
        root = Path(tmp)
        target = root / "Installed"
        unicode_target = root / "Установленный Ярнам"
        with ZipFile(args.zip_file) as z:
            z.extractall(target)
            z.extractall(unicode_target)
        game = target / "bbport-windows"
        exe = game / "BLauncher.exe"
        game_unicode = unicode_target / "bbport-windows"
        exe_unicode = game_unicode / "BLauncher.exe"
        if not exe.is_file() or not exe_unicode.is_file():
            raise ValueError("Real frozen BLauncher.exe absent")
        checks = [
            probe(exe, game, root, label="ASCII"),
            probe(exe, game, root, label="Проверка Ярнам"),
            probe(exe_unicode, game_unicode, root, label="UNICODE_INSTALL_ASCII_SCRIPT"),
            probe(exe_unicode, game_unicode, root, label="Установленный Ярнам - сценарий"),
        ]
    report = {
        "original_pinned_game_client": True,
        "real_windows_frozen_exe": True,
        "full_game_tested": False,
        "direct_p2p_tested": False,
        "checks": checks,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print("SHYT_YT130_NATIVE_FROZEN_LAUNCHER_DIAGNOSTIC_NOT_RELEASE_PASS")
    print(json.dumps(report, ensure_ascii=True))


if __name__ == "__main__":
    main()
