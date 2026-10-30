#!/usr/bin/env python3
"""Summarize native bbport PS4 ABI coverage without exporting executable content.

Accepts the exact JSON shapes emitted by scripts/prepare.py (analysis.json)
and scripts/link_modules.py (link.json). Reports *aggregate* counts only:
never disclose NIDs, symbol names, raw module names, game paths, bytes,
executable hashes, game identifiers, addresses or any source/game files.
An unresolved import is NOT necessarily missing: it may be implemented by
the host shim. This is a link-stage census, not runtime feature coverage.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

SCHEMA = "SHYT_NATIVE_ABI_AGGREGATE_V147"
MAX_REPORT_BYTES = 16 * 1024 * 1024
MAX_SYMBOLS = 200_000


class AbiReportError(ValueError):
    pass


def small_nonnegative(value: object, name: str, limit: int = MAX_SYMBOLS) -> int:
    if type(value) is not int or not (0 <= value <= limit):
        raise AbiReportError("invalid " + name + " counter")
    return value


def read_json(path: Path) -> dict:
    if not path.is_file() or path.is_symlink():
        raise AbiReportError("expected a regular local native loader report")
    if path.stat().st_size > MAX_REPORT_BYTES:
        raise AbiReportError("native loader report larger than safety limit")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        raise AbiReportError("invalid native loader JSON") from None
    if not isinstance(data, dict):
        raise AbiReportError("native loader report must be an object")
    return data


def library_class(spelling: str) -> str:
    # The loader can record 'nid#lib#module' or 'nid#library'. Do not echo
    # arbitrary strings from the user's binary, regardless of source.
    fields = spelling.split("#")
    if len(fields) not in (2, 3) or not fields[0] or not fields[1]:
        return "unknown_symbol_format"
    lib = fields[1].lower()
    if lib.startswith("libscenet"):
        return "sce_network"
    if lib.startswith(("libscelibc", "libc")):
        return "native_libc"
    if lib.startswith("libsce"):
        return "sce_platform"
    return "other_host_library"


def summarize(analysis: dict, link: dict | None = None) -> dict:
    # Parse only the few expected source fields; copy no raw source strings.
    declared = small_nonnegative(analysis.get("import_count"), "original imports")
    raw_imports = analysis.get("imports")
    if not isinstance(raw_imports, list) or len(raw_imports) != declared or (
            not all(isinstance(v, str) for v in raw_imports)):
        raise AbiReportError("original analyzed import inventory inconsistent")
    needed = analysis.get("needed")
    if not isinstance(needed, list) or len(needed) > 2048 or not all(
            isinstance(v, str) for v in needed):
        raise AbiReportError("original required module array invalid")
    output = {
        "schema": SCHEMA,
        "privacy": {"game_bytes_uploaded": False,
                    "symbol_names_included": False,
                    "host_paths_included": False,
                    "game_title_or_hash_included": False},
        "source": "original bbport prepare.py and link_modules.py metadata only",
        "original_executable_imports": declared,
        "required_system_module_count": len(needed),
        "runtime_proven": False,
        "link_stage_proven": False,
        "limitation": (
            "Host-shim and native-module coverage requires runtime resolver tests; "
            "unresolved_linker_imports are not necessarily unimplemented."
        ),
    }
    if link is None:
        output["linked_import_census"] = "not_provided"
        return output
    imported = small_nonnegative(link.get("imports"), "linked imports")
    bindings = small_nonnegative(link.get("bindings"), "module bindings")
    unresolved = link.get("unresolved_imports")
    modules = link.get("modules")
    if not isinstance(unresolved, list) or len(unresolved) > MAX_SYMBOLS or not all(
            isinstance(v, str) for v in unresolved):
        raise AbiReportError("native link unresolved import inventory invalid")
    if not isinstance(modules, list) or len(modules) > 2048 or not all(
            isinstance(v, dict) for v in modules):
        raise AbiReportError("native link bundled module inventory invalid")
    if declared > imported or bindings + len(unresolved) > imported:
        raise AbiReportError("original/linker import totals are inconsistent")
    groups = Counter(library_class(x) for x in unresolved)
    output.update({
        "link_stage_proven": True,
        "linked_import_census": "available",
        "linked_module_count": len(modules),
        "linked_total_import_slots": imported,
        "native_module_bound_symbols": bindings,
        "unresolved_linker_imports": len(unresolved),
        "unresolved_by_host_library_class": dict(sorted(groups.items())),
    })
    return output


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--analysis", type=Path, required=True,
                   help="local out/analysis.json from original scripts/prepare.py")
    p.add_argument("--link", type=Path, help="optional local out/link.json")
    p.add_argument("--output", type=Path, help="optional aggregate JSON output file")
    args = p.parse_args(argv)
    try:
        report = summarize(read_json(args.analysis),
                           read_json(args.link) if args.link else None)
        result = json.dumps(report, indent=2, ensure_ascii=True) + "\n"
        if args.output:
            # Never overwrite original source reports or game files. Require
            # an explicit new report filename, no existing file or symlink.
            target = args.output.resolve(strict=False)
            source_paths = [args.analysis.resolve()]
            if args.link:
                source_paths.append(args.link.resolve())
            if target in source_paths or target.exists():
                raise AbiReportError("refuse to overwrite an input/existing file")
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("x", encoding="utf-8") as f:
                f.write(result)
            print("Saved private aggregate-only native ABI census.")
        else:
            sys.stdout.write(result)
        return 0
    except (AbiReportError, OSError):
        print("Native ABI summary failed: invalid, missing or unsafe input", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
