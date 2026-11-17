#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline startup inventory. A structural match is not a completed constructor."""
import argparse
from collections import Counter
from pathlib import Path
import struct

from ps4_ctor_order_v567 import inspect
from ps4_guarded_publish_v569 import decode
from scan_class_family_v601 import classify


def plan(blob, first, last):
    order, _ = inspect(blob)
    if not 1 <= first <= last <= len(order):
        raise ValueError('invalid constructor window')
    _, family, _, _ = classify(blob)
    classes = {n: a for n, a, _ in family}
    phoff = struct.unpack_from('<Q', blob, 32)[0]
    count = struct.unpack_from('<H', blob, 56)[0]
    loads = [(f, o, v, fs, ms) for typ, f, o, v, _, fs, ms, _ in
             struct.iter_unpack('<II6Q', blob[phoff:phoff+56*count]) if typ == 1]
    for n in range(first, last + 1):
        a = order[n-1]
        offsets = [o+a-v for f, o, v, fs, _ in loads if f&1 and v<=a<=v+fs-41]
        row = decode(blob[offsets[0]:offsets[0]+41], a) if len(offsets)==1 else None
        if row:
            guard, dst, target = row
            if (not any(f&2 and v<=dst and guard<=v+ms-8 for f, _, v, _, ms in loads)
                    or not any(v<=target<=v+fs-8 for _, _, v, fs, _ in loads)):
                raise ValueError(f'invalid guard publication at ordinal {n}')
            yield n, a, 'guard-shape'
        elif classes.get(n) == a:
            yield n, a, 'class-shape'
        else:
            yield n, a, 'unclassified'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump', type=Path)
    p.add_argument('--first', type=int, default=90)
    p.add_argument('--last', type=int, default=18444)
    p.add_argument('--strict', action='store_true', help='exit 3 at first unclassified entry')
    args = p.parse_args()
    counts = Counter()
    try:
        for n, a, label in plan(args.dump.read_bytes(), args.first, args.last):
            counts[label] += 1
            if args.strict or args.last-args.first < 50:
                print(n, hex(a), label, sep='\t')
            if args.strict and label == 'unclassified':
                return 3
    except (OSError, ValueError) as exc:
        p.exit(2, f'audit failed: {exc}\n')
    print(dict(sorted(counts.items())))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
