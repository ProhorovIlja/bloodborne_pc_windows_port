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
    return {"format": "seamless-hunt-bbsc-source-parity-v1",
            "upstream": "CLSAMG22/BBSC v0.0.2",
            "port": "deadinside28/bloodborne_pc gpu/bbnet20",
            "components": rows, "summary": stats,
            "note": "Byte equivalence does NOT establish game or protocol compatibility."}


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
    print(json.dumps({"summary": result["summary"], "format": result["format"]},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
