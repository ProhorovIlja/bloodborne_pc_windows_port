# SPDX-License-Identifier: GPL-2.0-or-later
"""Check that the native class-registry fixture rejects specific semantic faults."""
import os
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
TEST = "test_class_sort_v556.c"
HEADER = "class_secondary_v557.h"
MUTANTS = [
    ("missing fourth virtual result", "batch=4", "batch=3", 22),
    ("unsigned key order", "^UINT64_C(0x8000000000000000)", "^UINT64_C(0)", 23),
    ("undersized cold table", "initial=512", "initial=511", 11),
    ("store key in place of class pointer", "row+8,cls", "row+8,keys[i]", 23),
    ("leak replacement on release failure", "(void)release(ctx,owner,b.va);",
     "(void)0;", 13),
]

def run(work):
    exe = work / ("class-registry.exe" if os.name == "nt" else "class-registry")
    subprocess.run([
        "clang", "-std=c11", "-O2", "-Wall", "-Wextra", "-Wpedantic", "-Werror",
        "-I", str(HERE), str(work / TEST), "-o", str(exe)
    ], check=True, timeout=30)
    return subprocess.run([str(exe)], check=False, timeout=15).returncode

def main():
    with tempfile.TemporaryDirectory() as root:
        work = Path(root)
        for name in (TEST, HEADER, "class_sort_v556.h"):
            (work / name).write_bytes((HERE / name).read_bytes())
        baseline = run(work)
        if baseline:
            raise SystemExit(f"baseline failed: {baseline}")
        for label, before, after, expected in MUTANTS:
            path = work / ("class_sort_v556.h" if label == "unsigned key order" else HEADER)
            original = path.read_text(encoding="utf-8")
            if original.count(before) != 1:
                raise SystemExit(f"{label}: mutation anchor changed")
            try:
                path.write_text(original.replace(before, after), encoding="utf-8")
                actual = run(work)
                if actual != expected:
                    raise SystemExit(f"{label}: expected rejection {expected}, got {actual}")
                print(f"rejected: {label} ({actual})", flush=True)
            finally:
                path.write_text(original, encoding="utf-8")

if __name__ == "__main__":
    main()
