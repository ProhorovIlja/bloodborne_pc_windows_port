# SPDX-License-Identifier: GPL-2.0-or-later
"""Split validated relocation slots into internal addresses and unresolved imports."""
LIMIT = 1 << 64


def partition(loads, rw, relocs, bias=0):
    """Inputs are prevalidated V480 metadata. Addresses are not host pointers."""
    if type(bias) is not int or not 0 <= bias < LIMIT:
        raise ValueError('invalid guest bias')
    spans = sorted((p[3], p[3]+p[6]) for p in loads)
    base, end = rw[3], rw[3]+rw[6]
    if (not spans or any(not 0 <= lo < hi <= LIMIT-bias for lo, hi in spans)
            or any(a[1] > b[0] for a, b in zip(spans, spans[1:]))
            or (base, end) not in spans or rw[:2] != (1, 6)):
        raise ValueError('invalid LOAD layout')
    internal, imports = [], []
    previous = base
    for slot, (info, addend) in sorted(relocs.items()):
        if not previous <= slot <= end-8 or not 0 <= info < LIMIT:
            raise ValueError('invalid relocation slot')
        previous = slot+8
        symbol, kind = info >> 32, info & 0xffffffff
        if kind == 8 and symbol == 0:
            if not any(lo <= addend < hi for lo, hi in spans):
                raise ValueError('relative relocation points outside LOADs')
            internal.append((slot-base, addend+bias))
        elif kind in (1, 6, 7) and symbol:
            if kind in (6, 7) and addend:
                raise ValueError('unexpected import addend')
            imports.append((slot-base, symbol, kind, addend))
        else:
            raise ValueError('unsupported relocation')
    return internal, imports
