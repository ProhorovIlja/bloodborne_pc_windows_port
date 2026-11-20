# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline SCE import extraction and strict symbol relocation write planning."""
import re
import struct
from collections import Counter

LIMIT = 1 << 64
TOKEN = re.compile(rb'[A-Za-z0-9+\-]+')
SYM = struct.Struct('<IBBHQQ')


def extract(relocations, symbols, strings):
    """Inputs are already bounded SCE tables; V466 checks destinations."""
    if not len(symbols) or len(symbols) % SYM.size or not len(strings):
        raise ValueError('invalid symbol or string table')
    result = []
    for slot, info, addend in relocations:
        if info == 8:
            continue
        i, kind = divmod(info, 1 << 32)
        if kind not in (1, 6, 7) or not 0 < i < len(symbols)//SYM.size:
            raise ValueError('invalid relocation symbol index')
        offset, tag, visibility, shndx, value, size = SYM.unpack_from(symbols, i*SYM.size)
        if (tag not in (0x11, 0x12) or visibility not in (0, 3) or shndx or value or size
                or (kind == 7 and tag != 0x12) or not 0 < offset < len(strings)):
            raise ValueError('unsupported imported symbol')
        end = strings.find(b'\0', offset, min(len(strings), offset+64))
        if end < 0:
            raise ValueError('unterminated import')
        parts = strings[offset:end].split(b'#')
        if len(parts) != 3 or len(parts[0]) != 11 or not all(map(TOKEN.fullmatch, parts)):
            raise ValueError('invalid scoped NID')
        result.append((slot, kind, addend, tuple(parts)+(tag & 15,)))
    return result


def plan(rows, bindings):
    """Key=(NID, library selector, module selector, ELF symbol type).
    Value=(guest base or callable ID, extent); callable IDs are not host pointers.
    No partial write plan on missing bindings or malformed inputs.
    """
    missing, writes = Counter(), []
    end = 0
    for slot, kind, addend, key in sorted(rows):
        if not end <= slot <= LIMIT-8 or kind not in (1, 6, 7):
            raise ValueError('invalid or overlapping relocation destination')
        end = slot+8
        if key[3] not in (1, 2) or (kind == 7 and key[3] != 2):
            raise ValueError('invalid binding kind')
        delta = addend if kind == 1 else 0
        if delta < 0 or (key[3] == 2 and delta):
            raise ValueError('unsupported addend')
        if key not in bindings:
            missing[key] += 1
            continue
        base, extent = bindings[key]
        if not 0 < base < LIMIT or not 0 <= delta < extent <= LIMIT-base:
            raise ValueError('binding outside declared guest span')
        if key[3] == 2 and extent != 1:
            raise ValueError('callable binding must be a single ID')
        writes.append((slot, (base+delta).to_bytes(8, 'little')))
    return ([], missing) if missing else (writes, missing)


def self_test():
    a, b = b'ABCDEFGHIJK', b'LMNOPQRSTUV'
    strings = b'\0'+a+b'#m#n\0'+b+b'#m#n\0'
    symbols = bytes(24)+SYM.pack(1, 0x11, 0, 0, 0, 0)+SYM.pack(17, 0x12, 3, 0, 0, 0)
    rows = extract([(8,(1<<32)+1,16),(16,(1<<32)+6,88),(24,(2<<32)+7,99)], symbols, strings)
    obj, fn = (a,b'm',b'n',1), (b,b'm',b'n',2)
    assert plan(rows,{obj:(0x100,17),fn:(0x200,1)})[0] == [
        (8,struct.pack('<Q',0x110)),(16,struct.pack('<Q',0x100)),(24,struct.pack('<Q',0x200))]
    assert plan(rows,{obj:(0x100,17),(b,b'm',b'other',2):(0x200,1)}) == ([],Counter({fn:1}))
    cases = [lambda: plan(rows,{obj:(0x100,16),fn:(0x200,1)}),
             lambda: plan(rows,{obj:(LIMIT-8,17),fn:(0x200,1)}),
             lambda: plan(rows+[rows[0]],{}),
             lambda: extract([(8,(3<<32)+1,0)], symbols, strings),
             lambda: extract([(8,(2<<32)+7,0)], symbols, strings[:-1]),
             lambda: extract([(8,(1<<32)+7,0)], symbols, strings)]
    for case in cases:
        try:
            case()
        except ValueError:
            continue
        raise AssertionError('invalid input accepted')
    print('NATIVE_V467_SCOPED_IMPORT_PLAN_PASS')


if __name__ == '__main__':
    self_test()
