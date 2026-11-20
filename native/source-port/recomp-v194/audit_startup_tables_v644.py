# SPDX-License-Identifier: GPL-2.0-or-later
"""Check the real targets of startup publications before binding host tables."""
from collections import Counter
from struct import unpack_from

NAMES = (b'system', b'generic', b'iostream')


def identify(point, relative, code, read):
    if point < 16 or point % 8 or read(point - 16, 16) != bytes(16):
        raise ValueError('unexpected address-point header')
    slots = tuple(relative.get(point + 8*i) for i in range(7))
    if any(a is None or not code(a) for a in slots):
        raise ValueError('slot missing executable target')
    name = read(slots[2], 8)
    if len(name) != 8 or name[:3] != b'\x48\x8d\x05' or name[7] != 0xc3:
        raise ValueError('unexpected name method')
    address = slots[2] + 7 + unpack_from('<i', name, 3)[0]
    label, _, _ = read(address, 9).partition(b'\0')
    if label not in NAMES:
        raise ValueError('unknown category')
    return NAMES.index(label), slots


def audit(blob):
    from audit_modules_v628 import file_reader, link_tables
    from replay_guarded_v643 import extract
    rows = list(extract(blob))
    ph, file = file_reader(blob)
    details = {}
    link_tables(blob, details=details)
    relative = {}
    occupied = set()
    for slot, info, addend in details['relocations']:
        if slot in occupied:
            raise ValueError('duplicate relocation')
        occupied.add(slot)
        if info == 8:
            relative[slot] = addend

    def read(va, size):
        (seg,) = (p for p in ph if p[0] == 1 and p[3] <= va <= p[3]+p[5]-size)
        return bytes(file(seg[2]+va-seg[3], size))

    def code(va):
        return any(p[0] == 1 and p[1]&1 and p[3] <= va < p[3]+p[5] for p in ph)

    tables = {p: identify(p, relative, code, read) for p in {r[3] for r in rows}}
    if sorted(c for c, _ in tables.values()) != list(range(len(NAMES))):
        raise ValueError('incomplete or ambiguous category set')
    if any(p-16 in occupied or p-8 in occupied for p in tables):
        raise ValueError('relocated header')
    return rows, tables


def main():
    import argparse
    import json
    from pathlib import Path
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot', type=Path)
    a = p.parse_args()
    rows, tables = audit(a.eboot.read_bytes())
    count = Counter(NAMES[tables[point][0]].decode() for _, _, _, point in rows)
    print(json.dumps(dict(publications=count, function_slots=sum(len(s) for _, s in tables.values()),
                          unique_targets=len({f for _, slots in tables.values() for f in slots})),
                     sort_keys=True))


if __name__ == '__main__':
    main()
