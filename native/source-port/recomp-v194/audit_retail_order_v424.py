#!/usr/bin/env python3
"""Compare private replay return identities with SCE constructor relocation order.

The driver emits a CTOR_ID ordinal address line immediately after each
successful RETURN line. This checks trace consistency, not binary provenance.
Input paths, addresses and game data must not be printed or exported.
"""
import argparse
import json
import mmap
from pathlib import Path
import re
import sys

from audit_startup_prefix_v422 import SUCCESS, lines, verify

IDENTITY = re.compile(rb"CTOR_ID ([1-9][0-9]{0,5}) ([0-9a-f]{16})")
MAX_IMAGE = 512 << 20


def check(out, err, targets, first, last):
    if last > len(targets):
        raise ValueError("replay exceeds constructor table")
    verify(out, err, first, last)
    records = 0
    pending = None
    for line in err:
        if pending is not None:
            match = IDENTITY.fullmatch(line)
            if not match or int(match[1]) != pending or int(match[2], 16) != targets[pending-1]:
                raise ValueError("incorrect or missing return identity")
            pending = None
            records += 1
        elif line.startswith(b"RETURN "):
            pending = first + records
        elif line.startswith(b"CTOR_ID"):
            raise ValueError("unpaired return identity")
    if pending is not None or records != last-first+1:
        raise ValueError("incomplete identity records")
    return records


def self_test():
    targets = [0x100, 0x200, 0x100]
    good = [b"RETURN 2", b"CTOR_ID 2 0000000000000200",
            b"RETURN 3", b"CTOR_ID 3 0000000000000100"]
    if check([SUCCESS], good, targets, 2, 3) != 2:
        raise AssertionError("valid repeated target refused")
    for bad in (good[:-1], good + good[-1:],
                good[:1] + [good[-1]] + good[2:],
                good[:3] + [b"CTOR_ID 3 0000000000000200"],
                good[:1] + [b"noise"] + good[1:]):
        try:
            check([SUCCESS], bad, targets, 2, 3)
        except ValueError:
            continue
        raise AssertionError("invalid identity sequence accepted")
    print("NATIVE_V424_RETAIL_ORDER_AUDIT_PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--elf", type=Path)
    parser.add_argument("--legacy-cursor", type=lambda x: int(x, 0))
    parser.add_argument("--first", type=int, default=93)
    parser.add_argument("--last", type=int)
    parser.add_argument("--run", type=Path, nargs=2, action="append")
    a = parser.parse_args()
    if a.self_test and all(x is None for x in (a.elf,a.legacy_cursor,a.last,a.run)):
        self_test()
        return 0
    if a.self_test or any(x is None for x in (a.elf,a.legacy_cursor,a.last,a.run)) or len(a.run)>8:
        parser.error("choose self-test or provide the private image, cursor, and transcripts")
    try:
        from audit_private_ctor_closure_v410 import legacy_plan
        paths = [a.elf, *(p for pair in a.run for p in pair)]
        if (any(p.is_symlink() or not p.is_file() for p in paths)
                or len({(p.stat().st_dev,p.stat().st_ino) for p in paths}) != len(paths)
                or not 64 <= a.elf.stat().st_size <= MAX_IMAGE):
            raise ValueError("invalid private inputs")
        with a.elf.open("rb") as f, mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as image:
            targets, _ = legacy_plan(image, a.legacy_cursor)
        for out,err in a.run:
            check(lines(out),lines(err),targets,a.first,a.last)
    except (ValueError,OSError,ImportError):
        print("private constructor order evidence refused", file=sys.stderr)
        return 2
    print(json.dumps(dict(runs=len(a.run), first=a.first, last=a.last,
        identities_per_run=a.last-a.first+1, retail_order_rows=len(targets),
        executable_identity_attested=False)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
