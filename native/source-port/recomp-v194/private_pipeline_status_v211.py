#!/usr/bin/env python3
"""V211 bounded and privacy-safe status of the whole Bloodborne private AOT.

Reads only V210 stage summaries and a V204 manifest. NEVER prints log lines,
source paths, game offsets, game-code hashes, personal IDs or raw bytecode.
Safe to run after an interrupted ChatGPT session to recover actual progress.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile

STEPS = ("extract_elf", "pointers", "function_scan",
         "original_imports", "generate_functions")
MAX_JSON = 1_000_000
ALLOWED = {"passed", "failed", "timeout", "missing", "invalid"}


def read_json(path: Path) -> dict | None:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_JSON:
        return None
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return None
    return result if isinstance(result, dict) else None


def status(work: Path) -> dict:
    if work.is_symlink() or not work.is_dir():
        raise ValueError("work directory missing or unsafe")
    logs = work / "_private_stage_logs"
    if logs.is_symlink():
        raise ValueError("private stage log directory is a symlink")
    result = {}
    for step in STEPS:
        item = read_json(logs / (step + ".summary.json"))
        value = item.get("status") if item is not None else "missing"
        if value not in ALLOWED or value == "invalid":
            value = "invalid"
        result[step] = value
    manifest = read_json(work / "full-original-preparation.json")
    valid = bool(
        manifest and manifest.get("format") == "SHYT_PRIVATE_FULL_IMAGE_V204"
        and isinstance(manifest.get("functions_scanned"), int)
        and manifest.get("functions_scanned", 0) > 0
        and isinstance(manifest.get("aot_functions_registered"), int)
        and 0 < manifest["aot_functions_registered"] <= manifest["functions_scanned"]
        and isinstance(manifest.get("c_hashes"), dict)
        and manifest["c_hashes"]
    )
    return {
        "phase": "prepared" if valid and all(x == "passed" for x in result.values())
                 else "blocked_or_incomplete",
        "stages": result,
        "complete_original_manifest_present": valid,
        "native_windows_exe_game_boot_proven": False,
        "bounded_diagnostics": True,
        "note": "Metadata only. NEVER infer original game launch from a completed source scan.",
    }


def selftest() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "private"
        logs = root / "_private_stage_logs"
        logs.mkdir(parents=True)
        assert status(root)["phase"] == "blocked_or_incomplete"
        for step in STEPS:
            (logs / (step + ".summary.json")).write_text(json.dumps({
                "status": "passed", "output_bytes_seen": 400000,
                "original_private_path": "/ABSOLUTELY-NOT-FOR-PUBLIC"
            }))
        (root / "full-original-preparation.json").write_text(json.dumps({
            "format": "SHYT_PRIVATE_FULL_IMAGE_V204",
            "functions_scanned": 12, "aot_functions_registered": 4,
            "c_hashes": {"recomp.c": "private-hash-value"},
            "input_sha256": "private-file-fingerprint",
        }))
        actual = status(root)
        assert actual["phase"] == "prepared"
        encoded = json.dumps(actual)
        assert "ABSOLUTELY" not in encoded
        assert "private-hash" not in encoded
        (logs / "generate_functions.summary.json").write_text('{"status":"failed"}')
        assert status(root)["phase"] == "blocked_or_incomplete"
    print("SHYT_NATIVE_V211_PRIVATE_PIPELINE_STATUS_SELFTEST_PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--work", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        selftest()
    elif args.work:
        try:
            print(json.dumps(status(args.work), ensure_ascii=False,
                             separators=(",", ":")))
        except (ValueError, OSError) as exc:
            parser.error(str(exc))
    else:
        parser.error("provide --work or --self-test")
