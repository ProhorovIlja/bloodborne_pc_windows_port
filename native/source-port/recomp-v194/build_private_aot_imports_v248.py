#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V248 private build-time only: original import slots -> native C link unit.

Run on an owner-controlled machine. Original game bytes and import addresses
must never enter public Git, CI, debug logs or API responses. At native
Windows launch there is NO PS4 EBOOT or ELF reader.
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import re

MATH_NAMES = (
    "acos","acosf","asin","asinf","atan","atan2","atan2f","atanf",
    "exp","exp2","exp2f","expf","fmod","fmodf","frexp","frexpf",
    "ldexp","ldexpf","pow","powf","tan","tanf","tanhf"
)
CLOCK_NAMES = ("sceKernelReadTsc", "sceKernelGetTscFrequency")
MAX_INDEX_BYTES = 512000
MAX_ROWS = 2001


def read_original_imports(path: Path) -> dict[str, int]:
    if path.is_symlink() or not path.is_file() or not (0 < path.stat().st_size <= MAX_INDEX_BYTES):
        raise ValueError("missing, linked, or oversized original import index")
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "stub\tname" or len(lines) > MAX_ROWS:
        raise ValueError("original imports TSV has unsupported schema")
    found: dict[str,int] = {}
    seen_offset = set()
    for row in lines[1:]:
        match = re.fullmatch(r"(0x[0-9a-fA-F]{1,16})\t([^\t\r\n]{1,128})", row)
        if not match:
            raise ValueError("invalid original import record")
        offset = int(match.group(1),16)
        name = match.group(2)
        if name in found or offset in seen_offset or offset == 0:
            raise ValueError("duplicate or zero import name/offset")
        found[name] = offset
        seen_offset.add(offset)
    requested = MATH_NAMES + CLOCK_NAMES
    if not all(name in found for name in requested):
        # No guessing or claiming that BBHost's HLE registration implies
        # a function really exists in THIS user's retail imports table.
        raise ValueError("required real game imports absent; no native binding generated")
    return {name:found[name] for name in requested}


def assert_private_output(path: Path) -> None:
    if path.exists() or path.is_symlink() or not path.parent.is_dir():
        raise ValueError("private generated target must be a new regular file path")
    for ancestor in (path.parent, *path.parent.parents):
        if ancestor.is_symlink() or (ancestor / ".git").exists():
            raise ValueError("refusing output inside Git worktree or linked directory")


def generate_source(index: dict[str,int]) -> str:
    output = [
        "/* GENERATED PRIVATELY FROM OWNER'S GAME IMPORTS: NEVER DISTRIBUTE. */",
        "/* No original PS4 executable is loaded or needed at runtime. */",
        '#include "native_aot_services_bootstrap_v245.h"',
        '#include <stdint.h>',
        "int shyt_private_aot_imports_v248_init(uint64_t image_base,",
        "    ShytMathImportTable *math, ShytClockTargetsV239 *clock) {",
        "    if (!image_base || !math || !clock) return 0;",
        "    const ShytMathImportDesc originals[23] = {",
    ]
    output.extend(
        f'        {{UINT64_C(0x{index[name]:x}), "{name}"}},'
        for name in MATH_NAMES
    )
    output.extend([
        "    };",
        "    if (!shyt_math_import_table_v224_init(math, image_base, originals, 23))",
        "        return 0;",
        "    const ShytClockTargetsV239 candidate = {",
        "        image_base,",
        f'        UINT64_C(0x{index[CLOCK_NAMES[0]]:x}),',
        f'        UINT64_C(0x{index[CLOCK_NAMES[1]]:x})',
        "    };",
        "    if (candidate.read_tsc_offset > UINT64_MAX-image_base ||",
        "        candidate.get_tsc_frequency_offset > UINT64_MAX-image_base)",
        "        return 0;",
        "    *clock = candidate;",
        "    return 1;",
        "}",
        "",
    ])
    return "\n".join(output)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--original-imports", type=Path, required=True)
    parser.add_argument("--private-output", type=Path, required=True)
    args = parser.parse_args()
    try:
        # Validate paths before scanning real import material.
        assert_private_output(args.private_output)
        mapping = read_original_imports(args.original_imports)
        generated = generate_source(mapping)
        flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(args.private_output,flags,0o600)
        with os.fdopen(fd,"w",encoding="utf-8") as stream:
            stream.write(generated)
    except (OSError, UnicodeError, ValueError) as exc:
        parser.error(f"V248 private code generation failed: {type(exc).__name__}")
    print("SHYT_V248_PRIVATE_AOT_IMPORTS_READY math=23 clock=2 no_offsets_disclosed")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
