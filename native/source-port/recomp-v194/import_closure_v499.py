# SPDX-License-Identifier: GPL-2.0-or-later
"""Compare exact-image SCE imports with a candidate host binding inventory offline."""
import argparse
import hashlib
import json
import mmap
from pathlib import Path
import re
import struct
import sys

from census_v480 import EH, census
from import_edges_v482 import import_index
from plan_symbol_reloc_v467 import TOKEN


def read_profile(path):
    def unique(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("duplicate JSON field")
            result[key] = value
        return result

    if path.is_symlink() or not path.is_file() or path.stat().st_size > 4 << 20:
        raise ValueError("invalid profile")
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)


def compare(imports, profile, digest):
    if (type(profile) is not dict or set(profile) != {"format", "image_sha256", "bindings"}
            or profile["format"] != "bb-host-import-inventory-v1"
            or profile["image_sha256"] != digest
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
            or type(profile["bindings"]) is not list):
        raise ValueError("invalid or mismatched profile")
    declared = set()
    for row in profile["bindings"]:
        if (type(row) is not list or len(row) != 4
                or any(type(x) is not str or not 1 <= len(x) <= 63 for x in row[:3])
                or type(row[3]) is not int or row[3] not in (1, 2)):
            raise ValueError("invalid scoped binding")
        fields = tuple(x.encode("ascii") for x in row[:3])
        if len(fields[0]) != 11 or not all(map(TOKEN.fullmatch, fields)):
            raise ValueError("invalid NID or selector")
        key = (*fields, row[3])
        if key in declared:
            raise ValueError("duplicate scoped binding")
        declared.add(key)
    required = {row[2] for row in imports.values()}
    if not required:
        raise ValueError("empty import inventory")
    matched = required & declared
    missing = required - declared
    return {
        "required_keys": len(required),
        "matched_keys": len(matched),
        "unused_profile_keys": len(declared - required),
        "required_slots": len(imports),
        "matched_slots": sum(row[2] in matched for row in imports.values()),
        "missing_keys": [[*(x.decode("ascii") for x in key[:3]), key[3]]
                         for key in sorted(missing)],
        "runtime_bindings_verified": False,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--elf", required=True, type=Path)
    p.add_argument("--first-load-slot", required=True, type=lambda x: int(x, 0))
    p.add_argument("--profile", required=True, type=Path)
    a = p.parse_args()
    try:
        profile = read_profile(a.profile)
        if a.elf.is_symlink() or not a.elf.is_file() or not EH.size <= a.elf.stat().st_size <= 512 << 20:
            raise ValueError("invalid input")
        with a.elf.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as im:
            digest = hashlib.sha256(im).hexdigest()
            evidence = {}
            census(im, a.first_load_slot, evidence=evidence)
            result = compare(import_index(im, evidence), profile, digest)
    except (ValueError, OSError, KeyError, struct.error, RecursionError):
        print("V499 refused: invalid image, profile or relocation metadata", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 3 if result["missing_keys"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
