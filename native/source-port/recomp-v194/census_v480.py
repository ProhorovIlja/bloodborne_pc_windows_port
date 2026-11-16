# SPDX-License-Identifier: GPL-2.0-or-later
"""Whole-image metadata census and private AOT reconciliation, not a function scanner."""
import argparse
from collections import Counter
import hashlib
import json
import mmap
from pathlib import Path
import struct
import sys

EH = struct.Struct('<16sHHIQQQIHHHHHH')
PH = struct.Struct('<II6Q')
Q = struct.Struct('<Q')
LIMIT = 1 << 64


def require(ok, message):
    if not ok:
        raise ValueError(message)


def census(im, first_slot):
    h = EH.unpack_from(im)
    require(h[0][:7] == b'\x7fELF\x02\x01\x01' and h[1] in (0xfe00,0xfe01,0xfe04,0xfe10,0xfe18)
            and h[2:4] == (62,1) and h[8:10] == (EH.size, PH.size) and 0 < h[10] <= 256
            and EH.size <= h[5] <= len(im)-PH.size*h[10], 'invalid ELF')
    parts = [PH.unpack_from(im,h[5]+i*PH.size) for i in range(h[10])]
    for p in parts:
        require(p[2] <= len(im)-p[5] and p[3] <= LIMIT-p[6], 'invalid program span')
    loads = sorted((p for p in parts if p[0] == 1), key=lambda p:p[3])
    require(all(0 < p[6] and p[5] <= p[6] for p in loads)
            and all(a[3]+a[6] <= b[3] for a,b in zip(loads,loads[1:])), 'invalid LOAD layout')
    rx = [p for p in loads if p[1] == 5 and p[5]]
    rw = [p for p in loads if p[1] == 6 and p[5]]
    require(len(rx) == len(rw) == 1, 'unsupported LOAD profile')
    x, w = rx[0], rw[0]
    def in_x(a, n=1):
        return x[3] <= a and 0 < n <= x[3]+x[5]-a
    def xoff(a, n):
        require(in_x(a,n), 'invalid RX span')
        return x[2]+a-x[3]
    def one(t):
        rows = [p for p in parts if p[0] == t]
        require(len(rows) == 1, 'missing or duplicate metadata segment')
        return rows[0]
    eh = one(0x6474e550)
    d = xoff(eh[3],eh[5])
    require(d == eh[2] and eh[5]>=12 and im[d:d+4] == b'\x01\x1b\x03\x3b', 'unsupported EH header')
    ptr, n = struct.unpack_from('<iI',im,d+4)
    start = eh[3]+4+ptr
    xoff(start,8)
    require(0<n<=1_000_000 and 12+8*n<=eh[5], 'invalid EH count')
    unwind = set()
    prev = -1
    for loc, rel in struct.iter_unpack('<ii',im[d+12:d+12+8*n]):
        pc, fde = eh[3]+loc, eh[3]+rel
        length, back, disp = struct.unpack_from('<IIi',im,xoff(fde,12))
        require(prev<pc and start<=fde and 8<=length<=65536 and pc==fde+8+disp
                and 0<back and start<=fde+4-back<fde and in_x(fde,4+length) and in_x(pc), 'invalid FDE index')
        unwind.add(pc)
        prev=pc
    dyn, sce = one(2), one(0x61000000)
    require(0<dyn[5]<=262144 and not dyn[5]%16, 'invalid dynamic size')
    tags = {}
    keys = {12,13,0x61000029,0x6100002d,0x6100002f,0x61000031}
    for pos in range(dyn[2],dyn[2]+dyn[5],16):
        k,v = struct.unpack_from('<QQ',im,pos)
        if not k:
            break
        if k in keys:
            require(k not in tags, 'duplicate dynamic tag')
            tags[k]=v
    else:
        raise ValueError('missing dynamic terminator')
    relocs = {}
    ranges = []
    for a,z in ((0x61000029,0x6100002d),(0x6100002f,0x61000031)):
        if a not in tags and z not in tags:
            continue
        off, size = tags.get(a,-1),tags.get(z,-1)
        require(0<=off<=sce[5]-size and 0<=size<=48_000_000 and not size%24
                and all(off+size<=b or e<=off for b,e in ranges), 'invalid RELA span')
        ranges.append((off,off+size))
        for pos in range(sce[2]+off,sce[2]+off+size,24):
            slot,info,value=struct.unpack_from('<QQq',im,pos)
            require(slot not in relocs, 'duplicate RELA slot')
            relocs[slot]=info,value
    entry = {h[4], *(tags[t] for t in (12,13) if t in tags)}
    require(all(map(in_x,entry)), 'invalid entry points')
    # Check first-load provenance, not merely the presence of a sentinel.
    require(12 in tags, 'missing DT_INIT')
    init = tags[12]
    p = xoff(init,0x57)
    require(im[p+10:p+13]==b'\x48\x8d\x1d' and im[p+0x54:p+0x57]==b'\x48\x8b\x03'
            and init+17+struct.unpack_from('<i',im,p+13)[0]==first_slot, 'first-slot provenance mismatch')
    ctors=[]
    require(first_slot%8==0 and w[3]<=first_slot<=w[3]+w[5]-8, 'invalid first slot')
    for slot in range(first_slot,max(w[3]-1,first_slot-8*65536),-8):
        raw=Q.unpack_from(im,w[2]+slot-w[3])[0]
        if slot in relocs:
            info,value=relocs[slot]
            require(info==8 and in_x(value), 'invalid constructor relocation')
            ctors.append(value)
        elif raw==LIMIT-1:
            break
        else:
            require(raw==0, 'invalid constructor slot')
    else:
        raise ValueError('missing constructor sentinel')
    require(ctors, 'empty constructor list')
    pointers={v for info,v in relocs.values() if info==8 and in_x(v)}
    return dict(unwind=unwind, rx_relative=pointers, constructors=set(ctors), entry=entry), len(ctors)


def summarize(groups, ctors, scanner=None, emitted=None):
    union=set().union(*groups.values())
    membership=Counter('+'.join(sorted(k for k,v in groups.items() if a in v)) for a in union)
    out=dict(constructor_slots=ctors, metadata_candidate_ids=len(union),
             groups={k:len(v) for k,v in groups.items()}, membership=dict(sorted(membership.items())),
             scanner_comparison=None, emitted_comparison=None, full_native_coverage_attested=False)
    if scanner is not None:
        out['scanner_comparison']=dict(scanner_ids=len(scanner), scanner_only=len(scanner-union),
            metadata_only=len(union-scanner), missing_by_group={k:len(v-scanner) for k,v in groups.items()})
    if emitted is not None:
        require(scanner is not None and emitted<=scanner,'emitted IDs inconsistent with scanner')
        out['emitted_comparison']=dict(emitted_ids=len(emitted), scan_not_emitted=len(scanner-emitted),
            missing_by_group={k:len(v-emitted) for k,v in groups.items()})
    return out


def compare_v204(im, work):
    # V410 verifies the manifest, pinned generator, index hash and table hash.
    from audit_private_ctor_closure_v410 import generated_ids
    from verify_generated_coverage_v207 import scan_index
    index = work/'scan/functions.tsv'
    emitted = generated_ids(im,work)
    scanner = set(scan_index(index))
    # Recheck in case a second read saw a different work tree.
    require(generated_ids(im,work)==emitted, 'V204 provenance changed')
    return scanner, emitted


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--elf',required=True,type=Path)
    p.add_argument('--sha256',required=True)
    p.add_argument('--first-load-slot',required=True,type=lambda s:int(s,0))
    p.add_argument('--v204-work',type=Path)
    a=p.parse_args()
    try:
        require(not a.elf.is_symlink() and a.elf.is_file() and EH.size<=a.elf.stat().st_size<=512<<20,'unsafe ELF input')
        with a.elf.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as im:
            require(hashlib.sha256(im).hexdigest()==a.sha256,'image identity mismatch')
            groups, ctors=census(im,a.first_load_slot)
            comparison=compare_v204(im,a.v204_work) if a.v204_work else (None,None)
            report=summarize(groups,ctors,*comparison)
    except (ValueError,OSError,struct.error,KeyError,TypeError):
        print('V480 refused: malformed inputs or provenance mismatch',file=sys.stderr)
        return 2
    print(json.dumps(report,sort_keys=True))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
