# SPDX-License-Identifier: GPL-2.0-or-later
"""Identify the attested constructor-90 prefix family and resolve its query."""
from hashlib import sha256
from struct import unpack_from

SIZE = 0x14f
DISP = ((0xe,0x12),(0x1d,0x21),(0x2c,0x30),(0x37,0x3b),(0x3c,0x40),
        (0x46,0x4b),(0x4e,0x52),(0x53,0x57),(0x59,0x5e),(0x63,0x67),
        (0x77,0x7b),(0x87,0x8b),(0x9d,0xa1),(0xb4,0xb9),(0xbc,0xc0),
        (0xcb,0xcf),(0xd6,0xda),(0xdb,0xdf),(0xe6,0xea),(0xeb,0xef),
        (0xf2,0xf6),(0x102,0x106),(0x11f,0x123),(0x12d,0x131))
VARY = {1, 14, 15, 16, 18, 20}


def shape(body):
    masked = bytearray(body)
    for off, _ in DISP:
        masked[off:off+4] = bytes(4)
    return masked


def refs(va, body):
    return [va + end + unpack_from('<i', body, off)[0] for off, end in DISP]


def audit(read, order, reloc):
    first = order[89]
    sample = read(first, SIZE)
    if sha256(sample).hexdigest() != 'f5377643ba7e0d6d86130a576770635451601c0394e9ff436d1f9f3af22916e5':
        raise ValueError('unexpected constructor 90 prefix')
    reference = refs(first, sample)
    form = shape(sample)
    rows = []
    for i, va in enumerate(order, 1):
        if read(va, 11) != sample[:11]:
            continue
        body = read(va, SIZE)
        if shape(body) != form:
            continue
        r = refs(va, body)
        if any(a != b for j, (a, b) in enumerate(zip(r, reference)) if j not in VARY):
            continue
        if not (r[1] == r[14] and r[15] == r[16] == r[18] and r[20] == r[1]+8
                and r[15] == r[20]+0x58):
            raise ValueError('unexpected singleton layout')
        rows.append((i, r[1]))
    helper = reference[-1]
    inst = read(helper+0x13e, 15)
    if inst[:3] != b'\x48\x8d\x05' or inst[7:] != b'\x4a\x89\x84\x23\x58\x04\x00\x00':
        raise ValueError('unexpected query table publication')
    table = helper+0x145+unpack_from('<i', inst, 3)[0]
    kind, target = reloc[table+0x20]
    leaf = read(target, 10)
    if kind != 8 or leaf[:2] != b'\xc7\x07' or leaf[6:] != b'\x48\x89\xf8\xc3':
        raise ValueError('unexpected query relocation or leaf')
    return dict(prefixes=len(rows), singleton_slots=len({s for _, s in rows}),
                first=rows[0][0], last=rows[-1][0], query=unpack_from('<I',leaf,2)[0])


def main():
    import argparse
    import json
    from pathlib import Path
    from audit_modules_v628 import file_reader, link_tables
    from ps4_ctor_order_v567 import inspect
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot', type=Path)
    blob = p.parse_args().eboot.read_bytes()
    order, _ = inspect(blob)
    ph, file = file_reader(blob)
    details = {}
    link_tables(blob, details=details)

    def read(va, size):
        (s,) = (s for s in ph if s[0] == 1 and s[1]&1 and s[3] <= va <= s[3]+s[5]-size)
        return bytes(file(s[2]+va-s[3], size))

    reloc = {s: (t, a) for s, t, a in details['relocations']}
    print(json.dumps(audit(read, order, reloc), sort_keys=True))


if __name__ == '__main__':
    main()
