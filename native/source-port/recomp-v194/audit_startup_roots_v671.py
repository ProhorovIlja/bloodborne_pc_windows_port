# SPDX-License-Identifier: GPL-2.0-or-later
"""Build an offline startup seed list, not an AOT coverage claim."""
import argparse
import json
from pathlib import Path
from struct import iter_unpack, unpack_from

from ps4_ctor_order_v567 import inspect

SCE = 0x61000000
CALL_OFFSETS = (0x14, 0x1c, 0x28, 0x2d, 0x3a, 0x43, 0x4a)


def audit(blob):
    order, unwind = inspect(blob)
    entry, phoff = unpack_from('<QQ', blob, 24)
    entsize, count = unpack_from('<HH', blob, 54)
    if entsize != 56:
        raise ValueError('unexpected program header size')
    ph = list(iter_unpack('<II6Q', blob[phoff:phoff+entsize*count]))

    def segment(kind):
        (row,) = [r for r in ph if r[0] == kind]
        return blob[row[2]:row[2]+row[5]]

    def code(va, size):
        (row,) = [r for r in ph if r[0] == 1 and r[1]&1
                  and r[3] <= va <= r[3]+r[5]-size]
        off = row[2]+va-row[3]
        return blob[off:off+size]

    tags = {}
    for tag, value in iter_unpack('<QQ', segment(2)):
        if not tag:
            break
        tags[tag] = value
    dynlib = segment(SCE)

    def table(offset, length):
        off, size = tags[SCE+offset], tags[SCE+length]
        if off+size > len(dynlib):
            raise ValueError('dynamic table outside backing segment')
        return dynlib[off:off+size]

    strings, symbols = table(0x35, 0x37), table(0x39, 0x3f)
    jumps = {}
    for slot, info, addend in iter_unpack('<QQq', table(0x29, 0x2d)):
        if slot in jumps or info & 0xffffffff != 7 or addend:
            raise ValueError('unexpected PLT relocation')
        index = info >> 32
        off, _, _, section = unpack_from('<IBBH', symbols, index*24)
        if section or off >= len(strings):
            raise ValueError('expected undefined import')
        jumps[slot] = strings[off:strings.index(b'\0', off)].decode('ascii')

    init = tags[12]
    calls = []
    internal = {entry, init}
    for off in CALL_OFFSETS:
        at = entry+off
        opcode, delta = unpack_from('<Bi', code(at, 5))
        if opcode != 0xe8:
            raise ValueError('unexpected startup call opcode')
        dest = at+5+delta
        inst = code(dest, 6)
        if inst[:2] == b'\xff\x25':
            slot = dest+6+unpack_from('<i', inst, 2)[0]
            calls.append(dict(site=at, target=dest, import_key=jumps[slot]))
        else:
            internal.add(dest)
            calls.append(dict(site=at, target=dest))
    if init not in {c['target'] for c in calls if 'import_key' not in c}:
        raise ValueError('entry did not call DT_INIT')
    return dict(entry=entry, dt_init=init, direct_calls=calls,
                jump_slots=len(jumps), unwind_starts=len(unwind),
                constructor_slots=len(order), unique_constructors=len(set(order)),
                missing_unwind=sorted((internal | set(order))-unwind),
                required_roots=sorted(internal | set(order)))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot', type=Path)
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--roots', action='store_true', help='print seed RVAs as hexadecimal lines')
    mode.add_argument('--check', type=Path, help='check a manifest of emitted entry RVAs (hex, one per line)')
    a = p.parse_args()
    result = audit(a.eboot.read_bytes())
    roots = result.pop('required_roots')
    if a.roots:
        for va in roots:
            print(f'{va:x}')
    elif a.check:
        emitted = {int(line, 16) for line in a.check.read_text().splitlines() if line.strip()}
        missing = sorted(set(roots)-emitted)
        print(json.dumps(dict(required=len(roots), missing=[f'{va:x}' for va in missing])))
        return 1 if missing else 0
    else:
        print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
