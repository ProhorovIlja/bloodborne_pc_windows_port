# SPDX-License-Identifier: GPL-2.0-or-later
"""Generate a private replay of the V569 family in DT_INIT order, not full startup."""
import argparse
import struct
from pathlib import Path


def normalize(rows):
    pairs, targets, plan = {}, {}, []
    last = 0
    for ordinal, guard, dst, target in rows:
        if ordinal <= last or guard - dst != 8 or (guard | dst | target) & 7:
            raise ValueError('invalid publication order or layout')
        last = ordinal
        pairs.setdefault(dst, len(pairs))
        targets.setdefault(target, len(targets))
        plan.append((ordinal, pairs[dst], targets[target]))
    if not plan or set(pairs) & {d + 8 for d in pairs}:
        raise ValueError('empty or overlapping publication layout')
    return plan, len(pairs), len(targets)


def extract(blob):
    from ps4_ctor_order_v567 import inspect
    from ps4_guarded_publish_v569 import decode
    order, _ = inspect(blob)
    off = struct.unpack_from('<Q', blob, 32)[0]
    n = struct.unpack_from('<H', blob, 56)[0]
    loads = [p for p in struct.iter_unpack('<II6Q', blob[off:off+56*n]) if p[0] == 1]
    for ordinal, va in enumerate(order, 1):
        (rx,) = (p for p in loads if p[1]&1 and p[3] <= va <= p[3]+p[5]-41)
        x = rx[2] + va - rx[3]
        row = decode(blob[x:x+41], va)
        if row is None:
            continue
        guard, dst, target = row
        if not any(p[1]&2 and p[3] <= dst and guard+8 <= p[3]+p[6] for p in loads):
            raise ValueError('invalid writable extent')
        if not any(p[3] <= target <= p[3]+p[5]-8 for p in loads):
            raise ValueError('invalid address point extent')
        yield ordinal, guard, dst, target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('eboot', type=Path)
    a = parser.parse_args()
    plan, slots, targets = normalize(extract(a.eboot.read_bytes()))
    print('/* Private generated replay. Not an inventory of executable game code. */')
    print(f'#define SLOTS {slots}\n#define TARGETS {targets}')
    print('static const struct pub_row rows[] = {')
    for ordinal, slot, target in plan:
        print(f'    {{{ordinal},{slot},{target}}},')
    print('};')


if __name__ == '__main__':
    main()
