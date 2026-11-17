# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline census of four registry callbacks in the V649 constructor family."""
from collections import Counter
from hashlib import sha256
from struct import unpack_from

from audit_ctor_family_v649 import DIGEST, EXTENT, mask
from audit_ctor90_v648 import SIZE, VARY, refs, shape

REGISTRY = 0x20b80c0
CALLS = 'f4d0b55732f0164213c51a5f8d62942818891d3bf003de832181d797e39a941d'


def resolve(read, order, reloc, code, data):
    if sha256(read(REGISTRY, 0x44)).hexdigest() != CALLS:
        raise ValueError('unexpected registration call sequence')
    seed = read(order[89], EXTENT)
    if sha256(seed).hexdigest() != DIGEST:
        raise ValueError('unexpected constructor 90 body')
    form, prefix = mask(seed), shape(seed[:SIZE])
    reference = refs(order[89], seed[:SIZE])
    result = []
    for ordinal, va in enumerate(order, 1):
        if read(va, 11) != seed[:11]:
            continue
        body = read(va, EXTENT)
        if mask(body) != form or shape(body[:SIZE]) != prefix or any(
                a != b for i, (a, b) in enumerate(zip(reference, refs(va, body[:SIZE])))
                if i not in VARY):
            continue
        table = va + 411 + unpack_from('<i', body, 407)[0]
        if table != va + 856 + unpack_from('<i', body, 852)[0]:
            raise ValueError('cold and warm table disagree')
        if va + 471 + unpack_from('<i', body, 467)[0] != 0x20b7b10:
            raise ValueError('unexpected registration entry')
        if table % 8 or not data(table, 64):
            raise ValueError('invalid table extent')
        slots = []
        for offset in (32, 40, 48, 56):
            kind, fn = reloc.get(table + offset, (0, 0))
            if kind != 8 or not code(fn, 8):
                raise ValueError('unresolved registry callback')
            leaf = read(fn, 8)
            if leaf[:3] != b'\x48\x8d\x05' or leaf[7:] != b'\xc3':
                raise ValueError('callback not a constant address return')
            target = fn + 7 + unpack_from('<i', leaf, 3)[0]
            if not data(target, 1):
                raise ValueError('callback target outside data')
            slots.append((fn, target))
        result.append((ordinal, table, tuple(slots)))
    if len(result) != 30:
        raise ValueError('unexpected complete family count')
    return result


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
    ph, read_file = file_reader(blob)
    details = {}
    link_tables(blob, details=details)

    def read(va, n):
        (s,) = (s for s in ph if s[0] == 1 and s[3] <= va <= s[3]+s[5]-n)
        return bytes(read_file(s[2]+va-s[3], n))

    def extent(va, n, executable):
        return any(s[0] == 1 and bool(s[1]&1) == executable and s[3] <= va <= s[3]+s[5]-n
                   for s in ph)

    def data(va, n):
        # PS4 stores immutable data in its RX load; the target need not be RW.
        return any(s[0] == 1 and s[3] <= va <= s[3]+s[6]-n for s in ph)

    reloc = {slot: (kind, value) for slot, kind, value in details['relocations']}
    rows = resolve(read, order, reloc, lambda v, n: extent(v, n, True), data)
    hist = Counter(len({a for _, a in slots}) for _, _, slots in rows)
    print(json.dumps(dict(constructors=len(rows), tables=len({t for _, t, _ in rows}),
                          callback_slots=4*len(rows),
                          callback_functions=len({f for _, _, slots in rows for f, _ in slots}),
                          target_count_histogram=hist,
                          unique_targets=len({a for _, _, slots in rows for _, a in slots})), sort_keys=True))


if __name__ == '__main__':
    main()
