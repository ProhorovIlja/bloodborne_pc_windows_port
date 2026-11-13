#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Audit SCE startup order from the address of the first load, not a cursor.
Obtain the first-load slot by inspecting the exact image's initializer control
flow. Raw zero does not imply an empty slot when it has a relative relocation.
No addresses, bytes, hashes, or paths appear in the aggregate report.
"""
import argparse
import json
import mmap
from pathlib import Path
import struct
import sys

from audit_private_ctor_closure_v410 import EH, PH, MASK, legacy_plan
from audit_retail_order_v424 import check, lines


def from_first_load(image, slot):
    if slot < 0 or slot > MASK - 8 or slot & 7:
        raise ValueError("invalid first load")
    # V410 decrements before reading. Present a synthetic predecrement cursor.
    return legacy_plan(image, slot + 8)


def self_test():
    data = bytearray(1024)
    EH.pack_into(data, 0, b"\x7fELF\x02\x01\x01" + bytes(9),
                 0xfe10, 62, 1, 0x4000, EH.size, 0, 0, EH.size, PH.size, 3, 0, 0, 0)
    for index, row in enumerate(((1, 5, 256, 0x4000, 0x4000, 64, 64, 8),
                                 (2, 4, 384, 0, 0, 48, 48, 8),
                                 (0x61000000, 4, 512, 0, 0, 48, 48, 8))):
        PH.pack_into(data, EH.size + index * PH.size, *row)
    struct.pack_into("<6Q", data, 384, 0x6100002f, 0, 0x61000031, 48, 0, 0)
    struct.pack_into("<Q", data, 256 + 8, MASK)
    struct.pack_into("<QQqQQq", data, 512, 0x4028, 8, 0x4001, 0x4018, 8, 0x4002)
    targets, empty = from_first_load(data, 0x4028)
    if targets != [0x4001, 0x4002] or empty != 2:
        raise AssertionError("first relocated raw-zero slot lost")
    if legacy_plan(data, 0x4028)[0] != [0x4002]:
        raise AssertionError("fixture does not distinguish cursor conventions")
    from audit_startup_prefix_v422 import SUCCESS
    err = [b"RETURN 1", b"CTOR_ID 1 0000000000004001",
           b"RETURN 2", b"CTOR_ID 2 0000000000004002"]
    if check([SUCCESS], err, targets, 1, 2) != 2:
        raise AssertionError("valid order refused")
    for bad in (0x4029, MASK, -8):
        try:
            from_first_load(data, bad)
        except ValueError:
            continue
        raise AssertionError("invalid slot accepted")
    try:
        check([SUCCESS], err, targets[1:], 1, 2)
    except ValueError:
        pass
    else:
        raise AssertionError("shifted transcript accepted")
    print("NATIVE_V440_FIRST_LOAD_ORDER_PASS")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--elf", type=Path)
    p.add_argument("--first-load-slot", type=lambda value: int(value, 0))
    p.add_argument("--run", nargs=2, action="append", type=Path, metavar=("STDOUT", "STDERR"))
    p.add_argument("--first", type=int)
    p.add_argument("--last", type=int)
    p.add_argument("--self-test", action="store_true")
    a = p.parse_args()
    if a.self_test and all(v is None for v in (a.elf, a.first_load_slot, a.run, a.first, a.last)):
        self_test()
        return 0
    if (a.self_test or a.elf is None or a.first_load_slot is None
            or (a.run and (a.first is None or a.last is None or len(a.run) > 8))
            or (not a.run and (a.first is not None or a.last is not None))):
        p.error("specify an ELF and its first-load slot, optionally with bounded transcript pairs")
    try:
        if a.elf.is_symlink() or not a.elf.is_file() or not 64 <= a.elf.stat().st_size <= 512 << 20:
            raise ValueError("unsafe image")
        with a.elf.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as image:
            targets, empty = from_first_load(image, a.first_load_slot)
        if not targets:
            raise ValueError("empty plan")
        for out, err in a.run or []:
            check(lines(out), lines(err), targets, a.first, a.last)
    except (ValueError, OSError, struct.error):
        print("private first-load order evidence refused", file=sys.stderr)
        return 2
    print(json.dumps(dict(ordered_callbacks=len(targets), distinct_targets=len(set(targets)),
                          null_slots_skipped=empty, checked_transcript_pairs=len(a.run or []),
                          linked_code_attested=False, retail_boot_proven=False), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
