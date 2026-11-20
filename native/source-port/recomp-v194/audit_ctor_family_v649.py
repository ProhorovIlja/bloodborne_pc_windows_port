# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline comparison of constructor 90 beyond the shared V648 prefix."""
from hashlib import sha256
from struct import unpack_from

from audit_ctor90_v648 import DISP, SIZE, VARY, refs, shape

EXTENT = 0x3d9  # through the stack-check failure call; excludes padding
DIGEST = '687a086c98eda3f506d57e213a54d93f1331a0046be85c77aaa046348a337820'
TAIL = ((345,349),(359,363),(407,411),(440,444),(447,451),(458,462),
        (467,471),(474,478),(489,493),(500,504),(505,509),(515,520),
        (523,527),(528,532),(534,539),(544,548),(564,568),(580,584),
        (602,606),(625,630),(633,637),(648,652),(659,663),(664,668),
        (675,679),(680,684),(687,691),(703,707),(732,736),(746,750),
        (790,794),(804,808),(852,856),(885,889),(890,894),(931,935),
        (938,942),(950,954),(981,985))


def mask(body):
    if len(body) != EXTENT:
        raise ValueError('truncated constructor')
    out = bytearray(body)
    for off, _ in DISP + TAIL:
        out[off:off+4] = bytes(4)
    return out


def census(read, order, executable):
    first = order[89]
    original = read(first, EXTENT)
    if sha256(original).hexdigest() != DIGEST:
        raise ValueError('unexpected constructor 90 body')
    prefix = original[:SIZE]
    pr = refs(first, prefix)
    body = mask(original)
    calls = [(o, end) for o, end in DISP + TAIL if end == o+4 and original[o-1] == 0xe8]
    if len(calls) != 20:
        raise ValueError('unexpected direct call inventory')
    destinations = {o: set() for o, _ in calls}
    hits = []
    prefixes = 0
    for i, va in enumerate(order, 1):
        if read(va, 11) != prefix[:11]:
            continue
        candidate = read(va, SIZE)
        if shape(candidate) != shape(prefix) or any(
                x != y for j, (x, y) in enumerate(zip(pr, refs(va, candidate))) if j not in VARY):
            continue
        prefixes += 1
        full = read(va, EXTENT)
        if mask(full) != body:
            continue
        for o, end in calls:
            dst = va + end + unpack_from('<i', full, o)[0]
            if not executable(dst):
                raise ValueError('direct call leaves executable extent')
            destinations[o].add(dst)
        hits.append(i)
    return dict(prefixes=prefixes, same_body=len(hits), other_bodies=prefixes-len(hits),
                direct_sites=len(calls), varying_direct_sites=sum(len(s)>1 for s in destinations.values()),
                tail_provider_targets=len(destinations[890]), first=hits[0], last=hits[-1])


def main():
    import argparse
    import json
    from pathlib import Path
    from ps4_ctor_order_v567 import inspect
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot', type=Path)
    b = p.parse_args().eboot.read_bytes()
    order, _ = inspect(b)
    off = unpack_from('<Q', b, 32)[0]
    count = unpack_from('<H', b, 56)[0]
    ph = [unpack_from('<II6Q', b, off+56*i) for i in range(count)]
    rx = [(o,v,n) for t,f,o,v,_,n,_,_ in ph if t==1 and f&1]

    def read(va, size):
        ((o,v,n),) = (s for s in rx if s[1]<=va<=s[1]+s[2]-size)
        return b[o+va-v:o+va-v+size]

    print(json.dumps(census(read, order, lambda a: any(v<=a<v+n for _,v,n in rx)), sort_keys=True))


if __name__ == '__main__':
    main()
