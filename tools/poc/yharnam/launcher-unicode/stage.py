#!/usr/bin/env python3
"""Exact-source staging of original YT #433 Windows UTF-8 + startup crash logs.

Read-only verification then git apply in disposable official YT v1.3 checkout.
No protocol, account, game/save, server or on-disk release modifications.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import subprocess

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
FILE = "bbport/launcher/bbport_launcher_win.py"
BLOB = "b54974c649610bef59e53a61ae294edc2d386cda"
ADDED_TEST = "bbport/tests/test_launcher_code_page.py"
PATCH = Path(__file__).with_name("upstream-YT-PR433.patch")
HEADER = re.compile(r"^diff --git a/(\S+) b/(\S+)$", re.M)


def validate(patch: str):
    pairs = HEADER.findall(patch)
    if len(pairs) != 2 or any(a != b for a, b in pairs):
        raise ValueError("Unexpected modified paths")
    if {a for a, b in pairs} != {FILE, ADDED_TEST}:
        raise ValueError("Only native Windows launcher source + own new tests allowed")
    required = (
        "reconfigure(encoding='utf-8', errors='replace', line_buffering=True)",
        "launcher-errors.txt",
        "faulthandler",
        "record_startup_failure",
        "CYRILLIC",
        "test_a_script_prints_a_cyrillic_path_in_utf8",
        "test_a_failure_before_the_window_is_logged_and_shown",
        "test_the_log_goes_to_temp_when_the_install_cannot_be_written",
    )
    for token in required:
        if token not in patch:
            raise ValueError("Missing reviewed upstream #433 feature/test token " + token)
    # Protect original startup error reporting, never silence or mask errors.
    if "except Exception:\n+        pass" in patch:
        raise ValueError("Silent exception swallowing not accepted")


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True).strip()


def apply(root: Path):
    root = root.resolve()
    content = PATCH.read_text(encoding="utf-8")
    validate(content)
    if git(root, "rev-parse", "HEAD") != PIN or git(root, "status", "--porcelain"):
        raise ValueError("Not original CLEAN official YT1.3 source")
    if git(root, "rev-parse", "HEAD:" + FILE) != BLOB:
        raise ValueError("Wrong native launcher pinned source blob")
    if (root / ADDED_TEST).exists():
        raise ValueError("Unexpected existing YT #433 test file")
    subprocess.run(["git", "-C", str(root), "apply", "--check", str(PATCH)], check=True)
    subprocess.run(["git", "-C", str(root), "apply", str(PATCH)], check=True)
    if not (root / ADDED_TEST).is_file():
        raise ValueError("Failed to stage actual upstream Windows tests")
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("YT130_NATIVE_UTF8_AND_CRASH_LOG_PR433_SOURCE_EXACT_STAGED_NOT_DEPLOYED")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("disposable_yt130_checkout", type=Path)
    apply(p.parse_args().disposable_yt130_checkout)
