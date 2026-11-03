#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V344: no retail input; symlink/junction ancestor escape CI regression.

The real full-game AOT and COFF compilers must never write original-derived
sources/objects into a worktree through an innocent-looking path alias.
"""
from __future__ import annotations

from pathlib import Path
import tempfile

import prepare_private_full_game_v204 as prepare
import compile_private_win64_coff_v217 as coff

GUARDS=(prepare.private,coff.private)

def reject(path:Path) -> None:
    for private in GUARDS:
        try:
            private(path)
        except ValueError as error:
            assert "Git" in str(error)
        else:
            raise AssertionError("private original source path entered a Git worktree")

def check() -> None:
    with tempfile.TemporaryDirectory(prefix="fictional-native-v344-") as work:
        root=Path(work)
        outside=root/"owner-private"
        outside.mkdir()
        gitroot=root/"public-checkout"
        gitroot.mkdir()
        (gitroot/".git").mkdir()  # invented Git root, never real game
        public=gitroot/"game-derived"
        public.mkdir()
        for private in GUARDS:
            assert private(outside/"new-bloodborne-aot") == (outside/"new-bloodborne-aot").absolute()
        reject(public/"recomp_00001.c")
        reject(gitroot/"nested"/"future"/"source.obj")
        # A direct link to the public checkout, or an ancestor pointing
        # into its interior, was incorrectly accepted by the old guard.
        alias=root/"misleading-private"
        try:
            alias.symlink_to(public,target_is_directory=True)
        except (OSError,NotImplementedError):
            pass  # Windows without symlink privilege: direct Git guard still tested.
        else:
            reject(alias/"private-game-derived-output"/"recomp.c")
        # Also ensure a symlink to a safe external path cannot silently
        # re-route output between admission and writing.
        safe_alias=root/"alias-owner"
        try:
            safe_alias.symlink_to(outside,target_is_directory=True)
        except (OSError,NotImplementedError):
            pass
        else:
            reject(safe_alias/"future"/"object.obj")
        for private in GUARDS:
            assert private(outside/"original.exe") != public/"original.exe"

if __name__=="__main__":
    check()
    print("SHYT_NATIVE_V344_PRIVATE_AOT_COFF_NO_GIT_SYMLINK_ESCAPE_SYNTHETIC_PASS")
