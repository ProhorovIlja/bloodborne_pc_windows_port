#!/usr/bin/env python3
"""Inventory the V601 family offline; report addresses and lengths, not game bytes."""
import argparse
from collections import Counter
from pathlib import Path
import struct
from scan_class_family_v601 import classify


def inventory(data):
    _, rows, _, long_getters = classify(data)  # validates the image digest
    rel = {a: v for a, t, v in struct.iter_unpack(
        '<QQq', memoryview(data)[0x53f4d30:0x5951e78]) if t == 8}

    def read(rva, n):
        if rva < 0 or rva+n > 0x50d96dc:
            raise ValueError(f'RX read outside the pinned segment: {rva:#x}')
        return data[0x4000+rva:0x4000+rva+n]

    def lea(pc, op):
        ins = read(pc, 7)
        if ins[:3] != bytes.fromhex(op):
            raise ValueError(f'unexpected LEA at {pc:#x}')
        return pc+7+struct.unpack_from('<i', ins, 3)[0]

    def name(addr, width):
        buf = bytearray()
        for i in range(256):
            part = read(addr+i*width, width)
            if not any(part):
                return buf.decode('ascii' if width == 1 else 'utf-16-le')
            buf.extend(part)
        raise ValueError(f'unterminated class name at {addr:#x}')

    result = []
    for n, ctor, getter in rows:
        child = lea(ctor+0xef, '4c8d3d')
        table = lea(ctor+0x194, '488d0d')
        parent = lea(getter+(0xf2 if getter in long_getters else 0x63), '4c8d3d')
        narrow = name(lea(ctor+0x1bc, '488d05'), 1)
        wide = name(lea(ctor+0x1c7, '488d05'), 2)
        if not narrow or narrow != wide:
            raise ValueError(f'name mismatch in constructor {n}')
        if (read(rel[table+0x10], 5), read(rel[table+0x18], 5)) != (
                bytes.fromhex('488b4740c3'), bytes.fromhex('488b4748c3')):
            raise ValueError(f'unexpected name accessor in constructor {n}')
        keys = []
        for slot in range(0x20, 0x40, 8):
            target = rel[table+slot]
            if read(target+7, 1) != b'\xc3':
                raise ValueError(f'non-leaf key accessor at {target:#x}')
            keys.append(lea(target, '488d05'))
        result.append((n, child, parent, len(narrow), *keys))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('decrypted_elf', type=Path)
    p.add_argument('--list', action='store_true')
    args = p.parse_args()
    try:
        rows = inventory(args.decrypted_elf.read_bytes())
    except (OSError, ValueError, KeyError, StopIteration) as exc:
        p.exit(2, f'inventory failed: {exc}\n')
    children = {row[1]: row[0] for row in rows}
    lengths = Counter(row[3] for row in rows)
    print(f'classes={len(rows)} child_identities={len(children)} '
          f'parent_identities={len({row[2] for row in rows})} '
          f'secondary_keys={len({k for row in rows for k in row[4:]})} '
          f'primary_length_collision_groups={sum(x>1 for x in lengths.values())}')
    print('parent edges inside selected constructors:', [(n, children[p]) for n, _, p, *_ in rows if p in children])
    if args.list:
        for n, c, p, length, *keys in rows:
            print(n, hex(c), hex(p), length, *map(hex, keys), sep='\t')


if __name__ == '__main__':
    main()
