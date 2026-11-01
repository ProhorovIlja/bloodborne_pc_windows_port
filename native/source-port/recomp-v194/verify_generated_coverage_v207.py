#!/usr/bin/env python3
"""V207: fail-closed coverage accounting for original full-game bbrecomp.

The upstream generator omits functions that call setjmp and import stubs.
Counting scanner rows alone therefore overstates the native AOT output.
This checks the genuine generated RcFunction table WITHOUT publishing any
game addresses, functions, names, bytes, or generated C.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re

HEADER = re.compile(r"^\s*static const RcFunction table\[\] = \{\s*$")
ENTRY = re.compile(
    r"^\s*\{\s*0x([0-9a-fA-F]+)\s*,\s*([0-9]+)\s*,"
    r"\s*0x[0-9a-fA-F]+ull\s*,\s*f_([0-9a-fA-F]+)\s*,"
    r"\s*&d_([0-9a-fA-F]+)\s*\},\s*$"
)
MAX_TABLE_BYTES = 64 * 1024 * 1024
MAX_FUNCTIONS = 1_000_000


def count_table(text: str, scanned: int) -> dict:
    if type(scanned) is not int or not 1 <= scanned <= MAX_FUNCTIONS:
        raise ValueError("invalid original scanner function count")
    begun = False
    ended = False
    previous = -1
    count = 0
    for line in text.splitlines():
        if not begun:
            if HEADER.fullmatch(line):
                begun = True
            continue
        if not ended:
            if line.strip() == "};":
                ended = True
                continue
            m = ENTRY.fullmatch(line)
            if not m:
                raise ValueError("unrecognized original bbrecomp function table row")
            addr, size, fn, dispatch = (
                int(m.group(1), 16), int(m.group(2), 10),
                int(m.group(3), 16), int(m.group(4), 16)
            )
            if addr <= previous or addr != fn or addr != dispatch or size < 1:
                raise ValueError("original AOT function table inconsistent")
            previous = addr
            count += 1
            if count > scanned:
                raise ValueError("AOT table larger than scanner index")
        elif HEADER.fullmatch(line):
            raise ValueError("multiple generated function tables")
    if not begun or not ended or count == 0:
        raise ValueError("original AOT function table missing or empty")
    return {
        "functions_scanned": scanned,
        "aot_functions_registered": count,
        "functions_not_in_aot_table": scanned - count,
        "complete_scanner_to_aot_registration": count == scanned,
    }


def inspect_file(path: Path, scanned: int) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("missing or unsafe original generated function table")
    if path.stat().st_size > MAX_TABLE_BYTES:
        raise ValueError("generated function table exceeds safety bound")
    return count_table(path.read_text(encoding="utf-8"), scanned)


def selftest() -> None:
    def unit(a: int, n: int = 3) -> str:
        return "{0x%x, %d, 0x9ull, f_%x, &d_%x}," % (a, n, a, a)

    def table(*rows: str) -> str:
        return "\n".join(["/* public artificial test only */",
                          "static const RcFunction table[] = {", *rows, "};"])
    good = count_table(table(unit(1), unit(2)), 3)
    assert good == {
        "functions_scanned": 3, "aot_functions_registered": 2,
        "functions_not_in_aot_table": 1,
        "complete_scanner_to_aot_registration": False,
    }
    assert count_table(table(unit(1), unit(2)), 2)["complete_scanner_to_aot_registration"]
    for blob, scanned in (
        (table(unit(2), unit(1)), 3),
        (table(unit(1), unit(1)), 3),
        (table(unit(1).replace("f_1", "f_3")), 3),
        (table(unit(1).replace("&d_1", "&d_3")), 3),
        (table("{0x1, 0, 0x9ull, f_1, &d_1},"), 3),
        (table(unit(1), unit(2)), 1),
        (table("/* missing content */"), 2),
        ("/* no function table */", 2),
        (table(unit(1)).replace("};", ""), 2),
    ):
        try:
            count_table(blob, scanned)
        except ValueError:
            pass
        else:
            raise AssertionError("unsafe AOT coverage accepted")
    print("SHYT_NATIVE_V207_FULL_FUNCTION_TABLE_COVERAGE_SELFTEST_PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not args.self_test:
        parser.error("V207 must be called privately by V204; --self-test is public")
    selftest()
