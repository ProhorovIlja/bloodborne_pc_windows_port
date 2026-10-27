#!/usr/bin/env python3
"""Apply the official YT PR429 patch ONLY to a byte-pinned disposable YT1.3 tree.

This staging does not disable TLS verification and does not modify a user's
Bloodborne, Windows system store, saved games or installed launcher. Imported
upstream GPL-2.0-or-later content is preserved verbatim in the companion .patch.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import re
import subprocess

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
BLOBS = {
    "bbport/launcher/bbport_coop.py": "9c54b2cd577b1fd4d50cd500c64c0b9d0f1e8b24",
    "bbport/launcher/bbport_launcher_win.py": "b54974c649610bef59e53a61ae294edc2d386cda",
    "bbport/packaging/windows/package.sh": "461da8ebc4630346814a52c5673a1c2818d4a931",
    "bbport/tests/test_coop_launcher.py": "5d4a55c732a21990f1b00b3b33b9e9c8d6aec825",
    "tools/make-release.ps1": "ff9efbb3bf05d3b1aa407996ddcfcce7725c2a7e",
}
PATCH = Path(__file__).with_name("upstream-YT-PR429.patch")
GIT_DIFF = re.compile(r"^diff --git a/(\S+) b/(\S+)$", re.MULTILINE)


def check_patch(data: str) -> None:
    seen = GIT_DIFF.findall(data)
    if len(seen) != 5 or any(a != b for a, b in seen):
        raise ValueError("Changed file list differs from audited upstream PR429")
    if set(a for a, b in seen) != set(BLOBS):
        raise ValueError("Patch touches unapproved native launcher source")
    for expected in ("use_system_certificates", "truststore.SSLContext",
                     "ssl.PROTOCOL_TLS_CLIENT", "ssl.CERT_REQUIRED",
                     "context.check_hostname", "--hidden-import truststore",
                     "|True|True"):
        if expected not in data:
            raise ValueError("Patch lacks security gate: " + expected)
    for forbidden in ("CERT_NONE", "check_hostname = False", "verify=False",
                      "check_hostname=False"):
        if forbidden in data:
            raise ValueError("Unsafe TLS bypass in patch")


def run(root: Path) -> None:
    root = root.resolve()
    patch = PATCH.read_text(encoding="utf-8")
    check_patch(patch)
    def git(*args: str) -> str:
        return subprocess.check_output(
            ["git", "-C", str(root), *args], text=True
        ).strip()
    if git("rev-parse", "HEAD") != PIN or git("status", "--porcelain"):
        raise ValueError("Not a clean pinned YT1.3.0 checkout; no writes")
    for path, sha in BLOBS.items():
        if git("rev-parse", "HEAD:" + path) != sha:
            raise ValueError("Unexpected upstream blob; no writes: " + path)
    # Run a separate read-only preflight; the actual apply is atomic at patch level.
    subprocess.run(["git", "-C", str(root), "apply", "--check", str(PATCH)],
                   check=True)
    subprocess.run(["git", "-C", str(root), "apply", str(PATCH)], check=True)
    if git("diff", "--name-only").splitlines() != sorted(BLOBS):
        raise ValueError("Unexpected resulting source paths; refuse")
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("YT130_PR429_TRUSTSTORE_ORIGINAL_AUTHOR_PATCH_STAGED_DISPOSABLE_ONLY")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("disposable_yt130_checkout", type=Path)
    run(parser.parse_args().disposable_yt130_checkout)
