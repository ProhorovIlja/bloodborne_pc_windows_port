#!/usr/bin/env python3
"""V119: source-pinned Windows original YT1.3 coop revision generation.

Two native Protocol8 Windows jobs stalled on the same Ninja [120/431]
custom command: cmake -P bbcoop/revision.cmake. The original script runs
unbounded jj log and git status each time Ninja asks for bbcoop_revision.h,
including on an extensive modified checkout. Use truthful pinned HEAD-dirty
for the internal test build, with no SCM invocation inside the Ninja step.
Not a release, no game/coop protocol changes, no production deployment.
"""
from __future__ import annotations
from pathlib import Path
import subprocess
import sys

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
PATH = "bbport/gpu/bbcoop/revision.cmake"
BLOB = "9b8aec040f81ef1a65f838065ad46de87046f040"
MARK = "SHYT-V119-NATIVE-WINDOWS-REVISION-FASTPATH"
REV = PIN + "-dirty"

# Upstream's actual BB_SCM_REV macro, truthful modified source revision.
# Both the initial header generation and repeat no-op must finish quickly.
PATCHED = rf"""# {MARK}
# This copy of bbport/gpu is an internal source-pinned CI build with
# known staged patches. Never invoke jj/git from a Windows Ninja target.
if (NOT DEFINED OUT OR OUT STREQUAL "")
    message(FATAL_ERROR "V119: missing original bbcoop_revision.h output")
endif()
set(revision "{REV}")
set(content "#pragma once\n#define BB_SCM_REV \"__DOLLAR__{{revision}}\"\n")
if (EXISTS "__DOLLAR__{{OUT}}")
    file(READ "__DOLLAR__{{OUT}}" previous)
endif()
if (NOT previous STREQUAL content)
    file(WRITE "__DOLLAR__{{OUT}}" "__DOLLAR__{{content}}")
endif()
""".replace("__DOLLAR__", "$")

def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def rewrite(original: str) -> str:
    # Source-identical original revision.cmake or fail closed. Git blob guard
    # in stage() additionally validates every byte of the upstream file.
    anchors = [
        "execute_process(COMMAND git rev-parse HEAD WORKING_DIRECTORY",
        "execute_process(COMMAND git status --porcelain --untracked-files=no",
        "execute_process(COMMAND",
        "if (NOT previous STREQUAL content)",
        "set(revision",
    ]
    if any(original.count(s) < 1 for s in anchors) or MARK in original:
        raise ValueError("V119 source drift or duplicate revision stage")
    return PATCHED

def stage(root: Path) -> None:
    root = root.resolve(strict=True)
    target = root / PATH
    if (git(root, "rev-parse", "HEAD") != PIN or
            git(root, "rev-parse", "HEAD:" + PATH) != BLOB or
            not target.is_file() or target.is_symlink() or
            git(root, "diff", "--", PATH)):
        raise ValueError("V119 rejects non-pinned or already-modified revision source")
    candidate = rewrite(target.read_text(encoding="utf-8"))
    target.write_text(candidate, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("YT130_V119_PINNED_DIRTY_REVISION_NO_SCM_TARGET_STAGED_NOT_FULL_BUILD_PASS")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: stage_windows_revision_v119.py DISPOSABLE_ORIGINAL_YT13")
    stage(Path(sys.argv[1]))
