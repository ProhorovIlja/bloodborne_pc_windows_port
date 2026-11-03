#!/usr/bin/env python3
"""V220: compare private original PS4 import names with public BBHost PLT map.

Both input files stay local. Output contains ONLY aggregate counts, never
private code, addresses, NIDs, identifiers, game bytes or unmatched names.
Matching an import NAME is not evidence of an implemented native replacement.
"""
from __future__ import annotations
import argparse
from collections import Counter
from difflib import SequenceMatcher
import json
from pathlib import Path
import re
import tempfile

MAX_BYTES = 512 * 1024
PLT_COUNT = re.compile(r'\bkPltNameCount\s*=\s*(\d+)\s*;')
PLT_ITEM = re.compile(r'^\s*"((?:[^"\\]|\\.)*)"\s*,?\s*$')


def public_names(path: Path) -> list[str]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError("unsafe public import map")
    data = path.read_text(encoding="utf-8")
    count = PLT_COUNT.search(data)
    if not count or not 0 < int(count.group(1)) <= 2000:
        raise ValueError("public table count missing/unsafe")
    begin = data.find("kPltNames[]")
    if begin < 0:
        raise ValueError("public PLT array absent")
    subset = data[begin:]
    start = subset.find("{")
    end = subset.find("};", start + 1)
    if min(start, end) < 0:
        raise ValueError("public PLT array malformed")
    names = []
    for line in subset[start + 1:end].splitlines():
        if not line.strip():
            continue
        match = PLT_ITEM.fullmatch(line)
        if not match:
            raise ValueError("unrecognized public PLT row")
        raw = match.group(1)
        if "\\" in raw:
            raise ValueError("unexpected escape in public PLT row")
        names.append(raw)
    if len(names) != int(count.group(1)):
        raise ValueError("public PLT row count inconsistent")
    return names


def private_names(path: Path) -> list[str]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError("unsafe original scanner imports TSV")
    with path.open("r", encoding="utf-8") as source:
        if source.readline().rstrip("\r\n") != "stub\tname":
            raise ValueError("not a V213 original imports.tsv")
        names = []
        for line in source:
            cols = line.rstrip("\r\n").split("\t")
            if len(cols) != 2 or not cols[0].startswith("0x") or not cols[1]:
                raise ValueError("malformed private import row")
            if not re.fullmatch(r'0x[0-9a-fA-F]{1,16}', cols[0]):
                raise ValueError("malformed private import slot")
            names.append(cols[1])
    if not 0 < len(names) <= 2000:
        raise ValueError("unsafe original import row count")
    return names


def inspect(left: list[str], right: list[str]) -> dict:
    a, b = Counter(left), Counter(right)
    matched_multiset = sum((a & b).values())
    prefix = 0
    while prefix < min(len(left), len(right)) and left[prefix] == right[prefix]:
        prefix += 1
    blocks = SequenceMatcher(None, left, right, autojunk=False).get_matching_blocks()
    ordered_matches = sum(x.size for x in blocks)
    return {
        "format": "SHYT_V220_PRIVATE_ORIGINAL_BBHOST_PUBLIC_IMPORT_COMPARISON",
        "original_scanner_import_count": len(left),
        "public_bbhost_plt_entries": len(right),
        "exact_ordinal_prefix": prefix,
        "ordered_name_subsequence_matches": ordered_matches,
        "shared_name_occurrences_multiset": matched_multiset,
        "original_occurrences_not_in_public_table": sum((a-b).values()),
        "public_occurrences_not_in_original_table": sum((b-a).values()),
        "original_distinct_names": len(a),
        "public_distinct_names": len(b),
        "no_original_names_or_NIDs_in_report": True,
        "full_native_import_implementation_proven": False,
        "original_game_native_boot_proven": False,
        "note": ("Name/order mapping proves neither working ABI semantics nor "
                 "actual native implementations, and does not authorize copying GPL code.")
    }


def selftest() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        pub = root / "plt.inc"
        pri = root / "original.tsv"
        pub.write_text('static const int kPltNameCount = 3;\n'
                       'static const char* kPltNames[] = {\n'
                       '    "a",\n    "b",\n    "c",\n};\n')
        pri.write_text('stub\tname\n0x100\ta\n0x110\tb\n')
        assert public_names(pub) == ["a", "b", "c"]
        assert private_names(pri) == ["a", "b"]
        report = inspect(private_names(pri), public_names(pub))
        assert report["original_scanner_import_count"] == 2
        assert report["public_occurrences_not_in_original_table"] == 1
        assert report["ordered_name_subsequence_matches"] == 2
        assert not report["full_native_import_implementation_proven"]
        assert "0x100" not in json.dumps(report)
        pri.write_text("stub\tname\n0x110\tbad\n")
        assert inspect(private_names(pri), public_names(pub))[
            "original_occurrences_not_in_public_table"] == 1
        pub.write_text(pub.read_text().replace("= 3", "= 4"))
        try:
            public_names(pub)
        except ValueError:
            pass
        else:
            raise AssertionError("inconsistent public PLT count accepted")
    print("SHYT_V220_PUBLIC_PLT_PRIVATE_IMPORT_COMPARE_SELFTEST_PASS")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--original-imports", type=Path)
    ap.add_argument("--bbhost-plt", type=Path)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        selftest()
    else:
        if not args.original_imports or not args.bbhost_plt:
            ap.error("both private V213 imports.tsv and public BBHost table required")
        try:
            print(json.dumps(inspect(private_names(args.original_imports),
                                     public_names(args.bbhost_plt)), separators=(",", ":")))
        except (ValueError, OSError, UnicodeError) as exc:
            ap.error(str(exc))
