# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline census of one bounded signed-offset switch encoding.

Byte-pattern candidates are not proof of reachability or AOT coverage.
Other register assignments and nonadjacent bounds are out of scope.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
from struct import iter_unpack, unpack_from

from audit_scan_v710 import seeds
from resume_switch_v697 import SHA

TAIL = rb'\x48\x8d\x0d.{4}\x48\x63\x04\x81\x48\x01\xc8\xff\xe0'
BOUND = re.compile(rb'\x48\x83\xf8([\x00-\x7f])(?:\x77(.)|\x0f\x87(.{4}))'+TAIL,re.S)


def scan(rx, base):
    end = base+len(rx)
    for m in BOUND.finditer(rx):
        a, short, near = m.groups()
        n = a[0]+1
        lea = m.end()-16
        table = base+lea+7+unpack_from('<i',rx,lea+3)[0]
        default = base+lea+int.from_bytes(short or near,'little',signed=True)
        if not base <= default < end or not base <= table <= end-n*4:
            continue
        data = rx[table-base:table-base+n*4]
        targets = tuple(table+d for d, in iter_unpack('<i',data))
        if all(base <= t < end and not table <= t < table+n*4 for t in (*targets,default)):
            yield base+m.start(),table,targets,default


def audit(path):
    (lo,hi), groups = seeds(path)
    blob = path.read_bytes()
    if sha256(blob).hexdigest() != SHA:
        raise ValueError('unexpected build')
    off, = unpack_from('<Q',blob,32)
    n, = unpack_from('<H',blob,56)
    (rx,) = (p for p in iter_unpack('<II6Q',blob[off:off+56*n]) if p[0]==1 and p[1]&1)
    code = blob[rx[2]:rx[2]+hi-lo]
    rows = list(scan(code,lo))
    targets = {t for _,_,cases,default in rows for t in (*cases,default)}
    known = groups['unwind'] | groups['relocation_only_rx']
    novel = targets-known
    return dict(bounded_matches=len(list(BOUND.finditer(code))), tables=len(rows),
                unique_targets=len(targets), outside_unwind_and_relative=len(novel)), novel


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot',type=Path)
    p.add_argument('--private-entries',type=Path,help='write candidate RVAs to a new local file')
    a = p.parse_args()
    counts, targets = audit(a.eboot)
    if a.private_entries:
        with a.private_entries.open('x') as f:
            f.writelines(f'{t:#x}\n' for t in sorted(targets))
    print(json.dumps(counts,sort_keys=True))
