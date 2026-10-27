#!/usr/bin/env python3
"""Compose 4 independently reviewed YT1.3 native launcher fixes on ONE checkout.

Does NOT replace / ship any Windows binaries, touch accounts/saves or deploy.
Source of changes:
  YT official #429 SSL truststore (exact 5-file original author patch)
  Native game search permission skip (our draft PR28)
  YT official #433 UTF-8/Cyrillic/startup crash (source adapted PR29)
  Native atomic settings JSON/INI/mods/patches (our draft PR31)
All must pass their original source SHA/anchor guards; fail before any release.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import importlib.util
import subprocess

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
TEST_NAME = "bbport/tests/test_launcher_code_page.py"


def load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ValueError("Missing reviewed source module: " + str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(root: Path, *argv: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *argv], text=True).strip()


def integrate(root: Path) -> dict:
    root = root.resolve()
    trust = load_module("yt_trust", TOOLS / "launcher-truststore/stage.py")
    game = load_module("yt_game_search", TOOLS / "launcher-game-search/stage.py")
    unicode = load_module("yt_unicode", TOOLS / "launcher-unicode/stage.py")
    atomic = load_module("yt_atomic", TOOLS / "launcher-atomic-settings/stage.py")
    if git(root, "rev-parse", "HEAD") != PIN or git(root, "status", "--porcelain"):
        raise ValueError("Must use pristine pinned original YT1.3 upstream checkout")
    if len({trust.PIN, game.PIN, unicode.PIN, atomic.PIN, PIN}) != 1:
        raise ValueError("Fixes based on incompatible upstream revisions")
    if game.BLOB != trust.BLOBS[game.FILE]:
        raise ValueError("Conflicting game discovery source pin")
    if unicode.BLOB != atomic.BLOB or unicode.BLOB != trust.BLOBS[unicode.FILE]:
        raise ValueError("Conflicting native Windows launcher source pin")

    original = root / unicode.FILE
    coop = root / game.FILE
    test = root / unicode.ADDED_TEST
    if test.exists():
        raise ValueError("Unexpected existing original Unicode regression test")
    original_coop = coop.read_text(encoding="utf-8")
    original_launcher = original.read_text(encoding="utf-8")
    if original_coop.count(game.OLD_IS_GAME) != 1:
        raise ValueError("Original native game search has changed")
    if original_launcher.count(unicode.OLD_MAIN) != 1:
        raise ValueError("Original native Windows launcher has changed")

    # Exact original upstream #429 patch includes PyInstaller packaging and
    # truststore verification from frozen BLauncher.exe; requires CLEAN tree.
    trust.run(root)
    # Apply the three other self-contained patches to the exact same binary/
    # installer source checkout. Conflict guards trigger rather than guessing.
    coop_patched = game.patch_text(coop.read_text(encoding="utf-8"))
    launcher_patched = unicode.backport(original.read_text(encoding="utf-8"))
    launcher_patched = atomic.patch_text(launcher_patched)
    upstream_patch = unicode.PATCH.read_text(encoding="utf-8")
    unicode.validate(upstream_patch)
    author_tests = unicode.original_tests(upstream_patch)

    # All transforms successful: complete writes in our disposable checkout.
    coop.write_bytes(coop_patched.encode("utf-8"))
    original.write_bytes(launcher_patched.encode("utf-8"))
    test.write_bytes(author_tests.encode("utf-8"))
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    changed = set(git(root, "diff", "--name-only").splitlines())
    expected = set(trust.BLOBS) | {game.FILE, unicode.FILE, atomic.PATH}
    if changed != expected:
        raise ValueError(f"Unexpected source changes: {changed ^ expected}")
    if not test.is_file():
        raise ValueError("Original Windows Unicode tests were not staged")
    for signal in (
        "use_system_certificates", "atomic_utf8_write", "record_startup_failure",
        "command-line arguments withheld for privacy",
    ):
        if signal not in launcher_patched and signal not in coop_patched:
            raise ValueError("Integrated critical launcher feature missing " + signal)
    result = {
        "original_commit": PIN,
        "tested_original_sha": unicode.BLOB,
        "tracked_modified_sources": sorted(changed),
        "untracked_original_windows_test": unicode.ADDED_TEST,
        "features": ["YT_429_SECURE_TLS", "PERMISSION_SAFE_DISCOVERY",
                     "YT_433_WINDOWS_UTF8_CRASH_LOG_PRIVACY", "ATOMIC_NATIVE_SETTINGS"],
        "scope": "DISPOSABLE_WINDOWS_SOURCE_QA_ONLY_NO_DEPLOY",
    }
    print("YT130_FOUR_NATIVE_LAUNCHER_FIXES_COEXIST_DISPOSABLE_ONLY")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("disposable_yt130_checkout", type=Path)
    args = parser.parse_args()
    import json
    print(json.dumps(integrate(args.disposable_yt130_checkout), indent=2))
