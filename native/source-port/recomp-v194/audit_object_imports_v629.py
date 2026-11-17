#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline data-import ABI audit. Emits counts, never symbol bytes or addresses."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from audit_modules_v628 import PINS, file_reader, link_tables


def location(loads, start, size):
    matches = [p for p in loads if p[3] <= start and start+size <= p[3]+p[6]]
    if len(matches)!=1 or size<=0:
        raise ValueError('object lacks a unique nonempty load range')
    _,flags,_,base,_,filesz,_,_ = matches[0]
    if start>=base+filesz:
        return 'zero_fill'
    if start+size>base+filesz:
        return 'mixed'
    return 'rx_file' if flags&1 else 'rw_file' if flags&2 else 'ro_file'


def inventory(eboot, libc, loads):
    bindings, backing, sizes, overlap = Counter(), Counter(), Counter(), Counter()
    addends, targets = Counter(), Counter()
    count = 0
    for key,sites in eboot.get('imports',{}).items():
        definitions = libc.get('exports',{}).get(key,set())
        if not any(kind==1 for kind,_,_ in definitions):
            continue
        (_,addr,size), = definitions
        count += 1
        backing[location(loads,addr,size)]+=1
        sizes[size]+=1
        for _,kind,addend in sites:
            bindings[kind]+=1
            addends['nonzero' if addend else 'zero']+=1
        for slot,info,addend in libc.get('relocations',[]):
            if addr<=slot<addr+size:
                kind = info&0xffffffff
                overlap[kind]+=1
                if kind==8:
                    targets[location(loads,addend,1)]+=1
    return dict(objects=count, object_sizes=dict(sizes), backing=dict(backing),
                import_sites=dict(bindings), import_addends=dict(addends),
                object_relocations=dict(overlap), relative_targets=dict(targets))


def audit(eboot, libc):
    if tuple(sha256(b).hexdigest() for b in (eboot,libc))!=PINS[:2]:
        raise ValueError('unsupported eboot/libc hash or order')
    a,b = {},{}
    link_tables(eboot,details=a)
    link_tables(libc,details=b)
    return inventory(a,b,[p for p in file_reader(libc)[0] if p[0]==1])


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot',type=Path)
    p.add_argument('libc',type=Path)
    a=p.parse_args()
    print(json.dumps(audit(a.eboot.read_bytes(),a.libc.read_bytes()),sort_keys=True))
