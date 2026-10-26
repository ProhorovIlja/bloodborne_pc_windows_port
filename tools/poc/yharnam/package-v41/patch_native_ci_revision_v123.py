#!/usr/bin/env python3
"""CI-only original bbcoop revision: no Git/jj probes while Ninja starts C++.

The checkout is strictly pinned, all overlays applied, so its Git revision is
known AND dirty. Local builds without the opt-in environment behave unchanged.
"""
import argparse
import hashlib
from pathlib import Path

FILE = "bbport/gpu/bbcoop/revision.cmake"
PIN = "77e350743a7cb4524cfcc1782fb6e3af64e25b15"
ORIGINAL_BLOB = "9b8aec040f81ef1a65f838065ad46de87046f040"
MARKER = "SHYT-V123-ORIGINAL-GIT-FREE-BBCOOP-REV"
ANCHOR = 'set(revision "")\nset(dirty FALSE)'
GUARD = r"""set(revision "")
set(dirty FALSE)
# SHYT-V123-ORIGINAL-GIT-FREE-BBCOOP-REV
# CI checked the SHA and staged all overlays BEFORE CMake.
if(DEFINED ENV{SHYT_BBCOOP_CI_PINNED_REVISION})
    if(NOT "$ENV{SHYT_BBCOOP_CI_PINNED_REVISION}" STREQUAL "77e350743a7cb4524cfcc1782fb6e3af64e25b15-dirty")
        message(FATAL_ERROR "SHYT_V123_WRONG_PINNED_DIRTY_REVISION")
    endif()
    set(revision "$ENV{SHYT_BBCOOP_CI_PINNED_REVISION}")
    set(content "#pragma once\n#define BB_SCM_REV \"@REV@\"\n")
    if(EXISTS "@OUT@")
        file(READ "@OUT@" previous)
    endif()
    if(NOT previous STREQUAL content)
        file(WRITE "@OUT@" "@CONTENT@")
    endif()
    message(STATUS "SHYT_V123_BBCOOP_REVISION_GIT_FREE_PASS")
    return()
endif()""".replace("@REV@", "$"+"{revision}").replace("@OUT@", "$"+"{OUT}").replace("@CONTENT@", "$"+"{content}")


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def transform(text: str) -> str:
    required = (
        "execute_process(COMMAND git status --porcelain",
        "execute_process(COMMAND git rev-parse HEAD",
        "execute_process(COMMAND @JJ@ log".replace("@JJ@", "$"+"{jj}"),
        'set(content "#pragma once',
    )
    if MARKER in text:
        raise ValueError("V123 revision already transformed")
    if text.count(ANCHOR) != 1 or not all(x in text for x in required):
        raise ValueError("V123 original pinned bbcoop revision source changed")
    return text.replace(ANCHOR, GUARD, 1)


def stage(pinned: Path) -> None:
    path = pinned / FILE
    if not path.is_file() or path.is_symlink():
        raise ValueError("V123 missing/symlinked pinned original revision.cmake")
    data = path.read_bytes()
    if git_blob(data) != ORIGINAL_BLOB:
        raise ValueError("V123 original upstream revision.cmake blob mismatch")
    path.write_text(transform(data.decode("utf-8")), encoding="utf-8")
    print("SHYT_V123_ORIGINAL_DIRTY_CI_BBCOOP_REVISION_STAGED")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("pinned_upstream_checkout", type=Path)
    stage(p.parse_args().pinned_upstream_checkout)
