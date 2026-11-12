#!/usr/bin/env python3
"""V403: source-attested synthetic AOT route inventory and default-deny guard.

This is NOT an original Bloodborne function graph or a native game port.
Only run after the exact V402 two-source identity/fallback audit; main()
recomputes that audit and its byte-exact instrumentation/abort overlays.
Dynamic host-import edges are not resolved guest-to-guest call targets.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

import audit_native_only_v402 as v402

ROOT = Path(__file__).resolve().parent
MAX_REPORT = 20000
DIRECT_C_CALL = re.compile(r"\bf_([0-9a-f]+)\s*\(")
EXPECTED_LEDGER_KEYS = {
    "generated_source_functions", "quarantined_fallbacks",
    "native_only_functions", "failclosed_guest_bail_tail_edges",
    "native_indirect_call_sites", "runtime_original_game_proven",
}


def classify(manifest: dict, ledger: dict, table: str, raw_shard: str) -> dict:
    """Make explicit the difference between native codegen and safe game boot."""
    v400 = v402.module("v403_source_v400", "verify_native_function_identity_v400.py")
    if (not isinstance(ledger, dict) or
            set(ledger) != EXPECTED_LEDGER_KEYS or
            ledger["generated_source_functions"] != 12 or
            ledger["native_only_functions"] != 11 or
            ledger["quarantined_fallbacks"] != {"0x1140": ["rc->step"]} or
            ledger["native_indirect_call_sites"] != 2 or
            type(ledger["runtime_original_game_proven"]) is not bool or
            ledger["runtime_original_game_proven"]):
        raise ValueError("untrusted V402 full/approved corpus ledger")
    if (manifest.get("scope") != "invented-test-only" or
            manifest.get("image_sha256") != v402.EXPECTED_SHA or
            manifest.get("upstream_revision") != v400.PINNED):
        raise ValueError("unattested original-free image identity")
    inventory = v402.inventory(table, raw_shard)
    offsets = [int(s, 16) for s in manifest["function_offsets"]]
    if (offsets != sorted(inventory) or len(offsets) != 11 or
            0x1140 in inventory):
        raise ValueError("invented native compiled coverage differs")
    edges = []
    for item in manifest["calls"]:
        if not isinstance(item, dict):
            raise ValueError("malformed typed import edge")
        caller = int(item["function_offset"], 16)
        next_offset = int(item["next_offset"], 16)
        target = int(item["guest_target"], 16)
        if caller not in inventory or next_offset <= caller or target == 0:
            raise ValueError("invalid typed host import edge")
        edges.append((caller, next_offset, target, item["service"]))
    if len(edges) != 2 or len(set(edges)) != 2:
        raise ValueError("duplicated or missing host import callsites")
    states = []
    total_fallback = 0
    observed_callers = []
    for off, record in sorted(inventory.items()):
        calls = record["callbacks"].count("call")
        bail = record["callbacks"].count("bail")
        tail = record["callbacks"].count("tail")
        if (set(record["callbacks"]) - {"call", "bail", "tail"} or
                bail < 1 or tail < 1 or calls > 1):
            raise ValueError("unsupported guest callback in candidate")
        if DIRECT_C_CALL.search(record["body"]):
            # A generated direct call not covered by the typed import
            # manifest must NOT silently become a native route.
            raise ValueError("unattested direct generated C-to-C call")
        total_fallback += bail + tail
        if calls:
            observed_callers.append(off)
        states.append({
            "offset": "0x%x" % off,
            "size": record["size"],
            "source_hash": "0x%x" % record["hash"],
            "state": ("native_codegen_guarded_host_import" if calls else
                      "native_codegen_abort_on_unhandled_transfer"),
            "typed_host_import_sites": calls,
            "unhandled_transfer_policy": "abort",
            "game_runtime_entry_proven": False,
        })
    if (sorted(observed_callers) != sorted(x[0] for x in edges) or
            total_fallback != ledger["failclosed_guest_bail_tail_edges"]):
        raise ValueError("source callbacks conflict with V402 ledger/imports")
    return {
        "schema_version": 1,
        "scope": "invented-test-only",
        "generator_revision": v400.PINNED,
        "synthetic_image_sha256": v402.EXPECTED_SHA,
        "compiled_candidate_count": 11,
        "excluded_step_function": "0x1140",
        "functions": states,
        "host_import_edges": [{
            "caller": "0x%x" % c, "continuation": "0x%x" % n,
            "target": "0x%x" % t, "service": svc,
            "target_kind": "typed_native_host_import_not_guest_function",
        } for c, n, t, svc in sorted(edges)],
        "full_guest_call_graph_closed": False,
        "original_game_native_entry_proven": False,
        "native_runtime_dispatch_wired": False,
        "executable_scope": "synthetic_testing_only",
    }


def header(report: dict) -> str:
    rows = []
    for item in report["functions"]:
        off = int(item["offset"], 16)
        imported = item["typed_host_import_sites"]
        rows.append("  {UINT64_C(0x%x), %d}," % (off, imported))
    return ("/* V403: ONLY source-attested invented synthetic AOT addresses.\n"
            " * Default-deny. This example check is NOT integrated with the\n"
            " * actual Bloodborne runtime or a game call graph. */\n"
            "#ifndef SHYT_NATIVE_V403_SYNTHETIC_ROUTE_GUARD\n"
            "#define SHYT_NATIVE_V403_SYNTHETIC_ROUTE_GUARD\n"
            "#include <stdint.h>\n"
            "typedef struct { uint64_t offset; unsigned host_imports; } "
            "ShytV403Route;\n"
            "static const ShytV403Route shyt_v403_routes[] = {\n" +
            "\n".join(rows) +
            "\n};\n"
            "static inline int shyt_v403_is_synthetic_candidate(uint64_t offset) {\n"
            "  unsigned lo = 0u;\n"
            "  unsigned hi = (unsigned)(sizeof(shyt_v403_routes) / "
            "sizeof(shyt_v403_routes[0]));\n"
            "  while (lo < hi) {\n"
            "    unsigned mid = lo + (hi - lo) / 2u;\n"
            "    if (shyt_v403_routes[mid].offset < offset) lo = mid + 1u;\n"
            "    else hi = mid;\n"
            "  }\n"
            "  return lo < sizeof(shyt_v403_routes) / sizeof(shyt_v403_routes[0])\n"
            "      && shyt_v403_routes[lo].offset == offset;\n"
            "}\n#endif\n")


def read(path: Path, suffix: str) -> bytes:
    return v402.checked_file(path, suffix)


def output(path: Path, suffix: str, content: str) -> None:
    if (path.exists() or path.suffix != suffix or
            not path.parent.is_dir() or path.parent.is_symlink() or
            any((p / ".git").exists() for p in
                (path.parent, *path.parent.parents)) or
            len(content.encode("utf-8")) > MAX_REPORT):
        raise ValueError("unsafe or oversized original-free output")
    path.write_text(content, encoding="utf-8")


def main() -> None:
    p = argparse.ArgumentParser()
    for arg in ("full-table", "full-shard", "full-image",
                "native-table", "native-shard", "native-image",
                "native-v390-shard", "native-overlay", "manifest",
                "v402-ledger", "out-report", "out-header"):
        p.add_argument("--" + arg, type=Path, required=True)
    a = p.parse_args()
    v396 = v402.module("v403_manifest", "audit_import_closure_v396.py")
    manifest = v396.load_manifest(a.manifest, "invented-test-only")
    fulltable = read(a.full_table, ".c").decode("utf-8")
    fullshard = read(a.full_shard, ".c").decode("utf-8")
    nativetable = read(a.native_table, ".c").decode("utf-8")
    nativeshard = read(a.native_shard, ".c").decode("utf-8")
    recomputed = v402.evaluate(fulltable, fullshard,
                read(a.full_image, ".elf"), nativetable, nativeshard,
                read(a.native_image, ".elf"), manifest)
    ledger = json.loads(read(a.v402_ledger, ".json"))
    if ledger != recomputed:
        raise ValueError("V402 audit output differs from current generated sources")
    v390 = v402.module("v403_memory", "instrument_generated_aot_memory_v390.py")
    staged, _ = v390.transform(nativeshard)
    if staged != read(a.native_v390_shard, ".c").decode("utf-8"):
        raise ValueError("generated guest-memory mediation changed")
    overlay = v402.module("v403_abort", "native_failclosed_overlay_v402.py")
    compiled, _ = overlay.transform(staged)
    if compiled != read(a.native_overlay, ".c").decode("utf-8"):
        raise ValueError("compiled native source bypasses V402 abort guard")
    report = classify(manifest, ledger, nativetable, nativeshard)
    report_text = json.dumps(report, sort_keys=True, indent=2) + "\n"
    # Fail before writing either output: cannot overwrite existing files.
    for path, suffix in ((a.out_report, ".json"), (a.out_header, ".h")):
        if (path.exists() or path.suffix != suffix or
                not path.parent.is_dir() or path.parent.is_symlink() or
                any((p / ".git").exists() for p in
                    (path.parent, *path.parent.parents))):
            raise ValueError("unsafe V403 output path")
    if a.out_report == a.out_header:
        raise ValueError("output paths must differ")
    output(a.out_report, ".json", report_text)
    output(a.out_header, ".h", header(report))
    print("NATIVE_V403_EXACT_SYNTHETIC_SOURCE_ROUTE_LEDGER_PASS")
    print("approved_codegen=11 unsupported_step_excluded=1 original_game_boot=FALSE")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError, UnicodeError) as e:
        print("NATIVE_V403_ROUTE_AUDIT_REFUSED: " + str(e)[:180], file=sys.stderr)
        raise SystemExit(2)
