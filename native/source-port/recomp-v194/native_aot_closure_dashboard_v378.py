#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V378: private aggregate AOT/COFF gap accounting, never a game-ready claim.

Accepts ONLY the already-anonymized output shapes from V207 and V287.
Neither input source addresses, retail names nor private paths are printed.
No original game files or original COFF objects are opened by this tool.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

MAX_JSON = 32768
MAX_FUNCS = 1_000_000
MAX_OBJECTS = 512

class InvalidEvidence(ValueError):
    pass


def bounded(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise InvalidEvidence("missing or linked aggregate report")
    if not 2 <= path.stat().st_size <= MAX_JSON:
        raise InvalidEvidence("aggregate report outside size budget")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError, OSError) as exc:
        raise InvalidEvidence("invalid aggregate report") from exc
    if type(value) is not dict:
        raise InvalidEvidence("unexpected aggregate root")
    return value


def integer(src: dict, key: str, maximum: int) -> int:
    n = src.get(key)
    if type(n) is not int or not 0 <= n <= maximum:
        raise InvalidEvidence("invalid aggregate field")
    return n


def report(coverage: dict | None, coff: dict | None) -> dict:
    aot_scanned = aot_generated = missing_aot = None
    external_unresolved = blocked_objects = verified_objects = None
    if coverage is not None:
        aot_scanned = integer(coverage, "functions_scanned", MAX_FUNCS)
        aot_generated = integer(coverage, "aot_functions_registered", MAX_FUNCS)
        missing_aot = integer(coverage, "functions_not_in_aot_table", MAX_FUNCS)
        good = coverage.get("complete_scanner_to_aot_registration")
        if (not aot_scanned or not aot_generated or
            aot_generated > aot_scanned or
            missing_aot != aot_scanned-aot_generated or
            type(good) is not bool or good != (missing_aot == 0)):
            raise InvalidEvidence("inconsistent scanner coverage")
    if coff is not None:
        verified_objects = integer(coff, "verified_amd64_coff_objects", MAX_OBJECTS)
        external_unresolved = integer(coff,
            "external_references_unresolved_in_game_objects", 5_000_000)
        blocked_objects = integer(coff,
            "object_modules_blocked_by_host_imports", MAX_OBJECTS)
        if verified_objects == 0 or blocked_objects > verified_objects or (
                (external_unresolved == 0) != (blocked_objects == 0)):
            raise InvalidEvidence("inconsistent COFF aggregate")
        if (coff.get("native_pe_link_complete") is not False or
            coff.get("guest_runtime_removed") is not False):
            # These V287 counters represent COFF symbol inventory only.
            raise InvalidEvidence("unexpected promotion of V287 proof")
    blockers = []
    if coverage is None:
        blockers.append("missing_original_aot_table_coverage")
    elif missing_aot:
        blockers.append("original_functions_missing_from_aot")
    if coff is None:
        blockers.append("missing_verified_original_coff_closure")
    elif external_unresolved:
        blockers.append("unresolved_external_symbols")
    # Deliberately mandatory, not deducible from AOT counts or symbol tables.
    blockers.extend(("original_native_game_pe_and_elf_link_unproven",
                     "zero_guest_runtime_execution_unproven",
                     "complete_offline_gameplay_unproven"))
    return {
        "schema": "SHYT_NATIVE_V378_AOT_AGGREGATE_ONLY",
        "functions_scanned": aot_scanned,
        "functions_registered_in_aot": aot_generated,
        "functions_absent_from_aot": missing_aot,
        "verified_amd64_coff_objects": verified_objects,
        "external_names_unresolved_in_game_objects": external_unresolved,
        "coff_objects_requiring_host_imports": blocked_objects,
        "blockers": blockers,
        "strict_native_game_ready": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="V378 private aggregate-only AOT status; never a retail game status")
    p.add_argument("--coverage", type=Path)
    p.add_argument("--coff", type=Path)
    o = p.parse_args()
    try:
        out = report(bounded(o.coverage) if o.coverage else None,
                     bounded(o.coff) if o.coff else None)
    except (InvalidEvidence, OSError):
        print("NATIVE_V378_INVALID_PRIVATE_AGGREGATE", file=sys.stderr)
        return 2
    print(json.dumps(out, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
