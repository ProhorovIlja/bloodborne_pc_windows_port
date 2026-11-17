#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline audit of exact final-call tails, without exporting any game bytes."""
import argparse
from collections import defaultdict
from pathlib import Path
import re
import struct

from ps4_ctor_order_v567 import inspect

# (constructor, reference table, entry, verified terminal slice, count stub size)
PROFILES = (
    (98, 0x5365290, 0x236f1f0, 0x236f529, 0x236f54f, 3),
    (125, 0x53651f0, 0x235f140, 0x235f56c, 0x235f5c4, 6),
    (157, 0x53650b0, 0x2352870, 0x2352c8c, 0x2352cd7, 6),
)


def scan(blob):
    inspect(blob)  # Reject images outside the pinned 1.09 profile.
    rel = {s: v for s, t, v in struct.iter_unpack('<QQq', memoryview(blob)[0x53f4d30:0x5951e78])
           if t == 8}
    slots = defaultdict(list)
    for slot, target in rel.items():
        slots[target].append(slot)
    text = blob[0x4000:0x4000+0x2bbe4a8]
    for kind, table, entry, begin, end, width in PROFILES:
        count = rel[table+0x18]
        stub = text[count:count+width]
        exact = 0
        sites = []
        for match in re.finditer(re.escape(text[begin:end]), text):
            exact += 1
            candidate = match.start() - (begin-entry)
            for slot in slots[candidate]:
                if not all(0 < rel.get(slot+d, 0) < len(text) for d in (8, 16, 24, 32, 40)):
                    continue
                if text.startswith(stub, rel[slot+24]):
                    sites.append((slot, candidate, match.start()))
        if (table, entry, begin) not in sites:
            raise ValueError(f'missing reference table for {kind}')
        yield kind, exact, sites


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump', type=Path)
    for kind, exact, sites in scan(p.parse_args().dump.read_bytes()):
        print(f'{kind}: {exact} exact tails; {len(sites)} corroborated table slots; '
              f'{len({entry for _, entry, _ in sites})} distinct candidate entries')
