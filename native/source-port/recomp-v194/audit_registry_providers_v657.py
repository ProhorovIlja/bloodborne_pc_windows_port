# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline full-body census of the variable call following registry insertion."""
from collections import Counter
from hashlib import sha256
from struct import unpack_from

from audit_registry_slots_v655 import resolve

COMMON = (472, 'e9a1480d47ea935b2336dec56e93218162fb93307fec42977fe433225c0f1e3d',
          (18,32,47,58,63,73,81,86,92,102,122,138,160,183,191,206,
           217,222,233,238,245,261,290,304,346,360,408,441,468))
SPECIAL = (176, '42d8c846f91bfe2ddd3699d70a2ee40c41593b0954a90adf9cbedbe527498bd6',
           (14,31,46,61,74,79,90,95,102,124,131))


def ref(body, va, offset, extra=0):
    return va + offset + 4 + extra + unpack_from('<i', body, offset)[0]


def profile(read, va):
    for kind, (size, digest, offsets) in enumerate((COMMON, SPECIAL)):
        body = read(va, size)
        masked = bytearray(body)
        for off in offsets:
            masked[off:off+4] = bytes(4)
        if sha256(masked).hexdigest() != digest:
            continue
        if not kind:
            cell = ref(body, va, 32)
            if ref(body, va, 191) != cell or ref(body, va, 441) != cell:
                raise ValueError('common load and store disagree')
            return kind, cell, ref(body, va, 18), ref(body, va, 47), ref(body, va, 304)
        return kind, ref(body, va, 14), None, ref(body, va, 61), ref(body, va, 31)
    raise ValueError('unknown provider body')


def census(read, order, reloc, code, data):
    counts = Counter()
    for ordinal, _, _ in resolve(read, order, reloc, code, data):
        va = order[ordinal-1]
        fn = ref(read(va, 894), va, 890)
        if not code(fn, COMMON[0]):
            raise ValueError('provider outside executable extent')
        counts[fn] += 1
    profiles = {va: profile(read, va) for va in counts}
    if any(cell % 8 or not data(cell, 8) for _, cell, _, _, _ in profiles.values()):
        raise ValueError('invalid publication cell')
    if len({p[1] for p in profiles.values()}) != len(profiles):
        raise ValueError('publication cells alias')
    if any(len({p[i] for p in profiles.values() if p[0] == 0}) != 1 for i in (2,3,4)):
        raise ValueError('common runtime dependencies differ')
    return profiles, counts


def main():
    import argparse
    import json
    from pathlib import Path
    from audit_modules_v628 import file_reader, link_tables
    from ps4_ctor_order_v567 import inspect

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot', type=Path)
    b = p.parse_args().eboot.read_bytes()
    order, _ = inspect(b)
    ph, file = file_reader(b)
    details = {}
    link_tables(b, details=details)

    def read(va, n):
        (s,) = (s for s in ph if s[0] == 1 and s[3] <= va <= s[3]+s[5]-n)
        return bytes(file(s[2]+va-s[3], n))

    def code(va, n):
        return any(s[0] == 1 and s[1]&1 and s[3] <= va <= s[3]+s[5]-n for s in ph)

    def data(va, n):
        return any(s[0] == 1 and s[3] <= va <= s[3]+s[6]-n for s in ph)

    reloc = {s: (k, v) for s, k, v in details['relocations']}
    profiles, counts = census(read, order, reloc, code, data)
    print(json.dumps(dict(providers=Counter(p[0] for p in profiles.values()),
                          constructors=Counter({i: sum(counts[v] for v,p in profiles.items() if p[0]==i)
                                                for i in (0,1)})), sort_keys=True))


if __name__ == '__main__':
    main()
