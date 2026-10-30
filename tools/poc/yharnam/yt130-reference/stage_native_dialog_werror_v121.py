#!/usr/bin/env python3
"""V121: repair pinned original Windows C -Wunused-but-set-global failure.

Actual native Protocol8 Windows run 41013821139 got to Ninja 418/431 after
V119 unstuck revision.cmake. Clang -Werror rejected runtime_services.c:189,
because common_initialized is written but nowhere read. Preserve exported
sceCommonDialogInitialize => common_init returns zero, with no phantom
unused process-global. No -Werror suppression, game network/PSN policy change
or production modification.
"""
from pathlib import Path
import subprocess
import sys

PIN = "0645740a33ae21c56df3b4a0d9777086dbca6053"
PATH = "bbport/src/runtime_services.c"
BLOB = "2e62aadf665b5c19d3fabe4536f31da9a060536f"
MARK = "SHYT-V121-PINNED-COMMON-DIALOG-CLANG64-WERROR"
BEFORE = """static int common_initialized;
static ABI int32_t common_init(void) { common_initialized=1; return 0; }"""
AFTER = """/* SHYT-V121-PINNED-COMMON-DIALOG-CLANG64-WERROR:
 * There is no common dialog state: this no-op returns the same ABI code.
 * The previous private common_initialized was written but never read and
 * tripped Clang -Werror,-Wunused-but-set-global on original YT1.3 Windows.
 */
static ABI int32_t common_init(void) { return 0; }"""
REGISTRATION = '{"sceCommonDialogInitialize",common_init}'

def rewrite(source: str) -> str:
    if MARK in source or source.count(BEFORE) != 1:
        raise ValueError("V121 original YT1.3 common dialog source drift/double stage")
    if source.count(REGISTRATION) != 1:
        raise ValueError("V121 original exported C dialog symbol changed")
    return source.replace(BEFORE, AFTER, 1)

def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()

def stage(root: Path) -> None:
    root = root.resolve(strict=True)
    target = root / PATH
    if (git(root, "rev-parse", "HEAD") != PIN or
            git(root, "rev-parse", "HEAD:" + PATH) != BLOB or
            not target.is_file() or target.is_symlink() or
            git(root, "diff", "--", PATH)):
        raise ValueError("V121 unknown/modified original native service source")
    candidate = rewrite(target.read_text(encoding="utf-8"))
    target.write_text(candidate, encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("YT130_V121_ORIGINAL_WINDOWS_DIALOG_C_SOURCE_STAGED_NOT_FULL_GAME_BUILD")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: stage_native_dialog_werror_v121.py PINNED_YT13")
    stage(Path(sys.argv[1]))
