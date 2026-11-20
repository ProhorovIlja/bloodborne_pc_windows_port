#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Compare evidence for AOT entry points in the pinned 1.09 dump, offline."""
import argparse
import json
from pathlib import Path
import struct

from ps4_ctor_order_v567 import inspect


def audit(blob):
    order, unwind = inspect(blob)  # pinned image and legacy DT_INIT order
    p, n = struct.unpack_from('<Q', blob, 32)[0], struct.unpack_from('<H', blob, 56)[0]
    ph = list(struct.iter_unpack('<II6Q', blob[p:p+56*n]))
    dyn, size = next((o, fs) for t, _, o, _, _, fs, _, _ in ph if t == 2)
    dynlib = next(o for t, _, o, *_ in ph if t == 0x61000000)
    tags = {}
    for k, v in struct.iter_unpack('<QQ', blob[dyn:dyn+size]):
        if not k:
            break
        tags.setdefault(k, v)
    r = dynlib + tags[0x6100002f]
    loads = [(v, v+fs) for t, f, _, v, _, fs, _, _ in ph if t == 1 and f&1]
    targets = {a for _, kind, a in struct.iter_unpack('<QQq', memoryview(blob)[r:r+tags[0x61000031]])
               if kind & 0xffffffff == 8}
    rx = {a for a in targets if any(lo<=a<hi for lo, hi in loads)}
    if unwind is None:  # older V567 local profile omits this secondary table
        eh, va = next((o, v) for t, _, o, v, *_ in ph if t == 0x6474e550)
        count = struct.unpack_from('<I', blob, eh+8)[0]
        unwind = {va+struct.unpack_from('<i', blob, eh+12+i*8)[0] for i in range(count)}
    init = set(order)
    return dict(relative_targets=len(targets), executable_targets=len(rx),
                executable_targets_outside_unwind=len(rx-unwind),
                init_outside_unwind=len(init-unwind), init_outside_relations=len(init-rx),
                union_candidates=len(init | rx | unwind))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump', type=Path)
    print(json.dumps(audit(p.parse_args().dump.read_bytes()),sort_keys=True))
