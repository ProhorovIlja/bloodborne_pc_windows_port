"""Pinned, offline gameplay-source parity audit: CLS BBSC 0.0.2 vs native bbnet20.

This does not merge source or claim a native Windows build exists. JSON includes
only file names, byte sizes and hashes, never user data, credentials or game files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

COMPONENTS = (
    "bloodborne_re.cpp",
    "bbsc_persistence.h",
    "bbsc_messages.inc",
    "bbsc_cinematic.cpp",
    "bbsc_cinematic.h",
)
OFFICIAL = Path("emulator/src/core")
NATIVE = Path("gpu/bbnet20/bbsc/core")
CODE_EXTENSIONS = frozenset({".c", ".cpp", ".h", ".hpp", ".inc"})
MAX_FILES = 1000
MAX_FILE_BYTES = 8 * 1024 * 1024


def source_inventory(folder: Path) -> dict[str, dict]:
    """All relevant gameplay-source files, not just five handpicked samples.

    Paths/hashes only. Never import code or include game/save/account data in
    reports. Detect case-collisions and symlink injection for Windows builds.
    """
    found: dict[str, dict] = {}
    seen: set[str] = set()
    for path in sorted(folder.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"source inventory contains symlink: {path.relative_to(folder)}")
        if not path.is_file() or path.suffix.casefold() not in CODE_EXTENSIONS:
            continue
        relative = path.relative_to(folder).as_posix()
        insensitive = relative.casefold()
        if insensitive in seen:
            raise ValueError(f"case-colliding source file: {relative}")
        seen.add(insensitive)
        if len(found) >= MAX_FILES or path.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("unexpectedly large BBSC source snapshot")
        found[relative] = fingerprint(path)
    return found


def complete_comparison(official_dir: Path, native_dir: Path) -> dict:
    official = source_inventory(official_dir)
    native = source_inventory(native_dir)
    shared = sorted(official.keys() & native.keys())
    original_only = sorted(official.keys() - native.keys())
    native_only = sorted(native.keys() - official.keys())
    changed = [p for p in shared if official[p]["sha256"] != native[p]["sha256"]]
    identical = [p for p in shared if official[p]["sha256"] == native[p]["sha256"]]
    # Store hashes of every differing source for later manual review. This is
    # NOT a claim that text-different files are game-incompatible (or vice versa).
    return {
        "counts": {"official_files": len(official), "native_files": len(native),
                   "shared": len(shared), "identical": len(identical),
                   "changed": len(changed), "official_only": len(original_only),
                   "native_only": len(native_only)},
        "changed": [
            {"path": path, "official": official[path], "native": native[path]}
            for path in changed
        ],
        "identical": identical,
        "official_only": [{"path": path, "fingerprint": official[path]} for path in original_only],
        "native_only": [{"path": path, "fingerprint": native[path]} for path in native_only],
        "protocol_compatibility_proven": False,
    }


def fingerprint(path: Path) -> dict | None:
    if not path.is_file() or path.is_symlink():
        return None
    blob = path.read_bytes()
    return {"bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()}


def compare(official: Path, native: Path) -> dict:
    original, portable = official / OFFICIAL, native / NATIVE
    if not original.is_dir() or not portable.is_dir():
        raise ValueError("both the official BBSC and native bbnet20 source directories are required")
    rows = []
    for name in COMPONENTS:
        upstream = fingerprint(original / name)
        port = fingerprint(portable / name)
        status = ("missing" if upstream is None or port is None else
                  "identical" if upstream["sha256"] == port["sha256"] else "different")
        rows.append({"component": name, "status": status, "official": upstream, "native": port})
    stats = {key: sum(r["status"] == key for r in rows)
             for key in ("identical", "different", "missing")}
    detailed = complete_comparison(original, portable)
    return {"format": "seamless-hunt-bbsc-source-parity-v2",
            "upstream": "CLSAMG22/BBSC v0.0.2",
            "port": "deadinside28/bloodborne_pc gpu/bbnet20",
            "components": rows, "summary": stats,
            "full_inventory": detailed,
            "note": "Source parity is evidence for review, NOT proof of protocol/gameplay compatibility."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official", type=Path, required=True)
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = compare(args.official, args.native)
        if result["summary"]["missing"]:
            parser.error("critical gameplay file is missing; refused to infer parity")
    except (OSError, ValueError) as ex:
        parser.error(str(ex))
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(json.dumps({"summary": result["summary"], "format": result["format"],
                      "full_source_counts": result["full_inventory"]["counts"],
                      "gameplay_or_protocol_compatibility_proven": False},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
