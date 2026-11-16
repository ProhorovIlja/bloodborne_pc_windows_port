# SPDX-License-Identifier: GPL-2.0-or-later
"""Lower exact LEA RAX,[RIP+rel32]; RET to a slid guest data address."""

from collections import defaultdict, deque


def expand_tail_aliases(image, rx, ids, leaves):
    """Walk backwards only from a proven LEA/RET; cycles cannot become roots."""
    _,_,off,base,_,size,_,_=rx
    incoming=defaultdict(list)
    for a,b in zip(ids,ids[1:]+[base+size]):
        if a in leaves:
            continue
        p=off+a-base
        raw=image[p:p+min(9,b-a)]
        skip=4 if raw.startswith(b'\xf3\x0f\x1e\xfa') else 0
        op=raw[skip] if len(raw)>skip else 0
        n={0xe9:5,0xeb:2}.get(op,0)
        if n and len(raw)>=skip+n:
            target=a+skip+n+int.from_bytes(raw[skip+1:skip+n],'little',signed=True)
            incoming[target].append((a,raw[:skip+n]))
    rows=dict(leaves)
    pending=deque(leaves)
    while pending:
        target=pending.popleft()
        for a,raw in incoming.pop(target,()):
            rows[a]=(raw,rows[target][1])
            pending.append(a)
    return rows


def find(image, rx, rw, starts, *, tail_aliases=False):
    _,_,off,base,_,size,_,_=rx
    _,_,_,data,_,_,span,_=rw
    ids=sorted(set(starts))
    if (rx[:2]!=(1,5) or rw[:2]!=(1,6) or not ids or not 0<size<=len(image)-off or
            off<0 or not 0<=base<=ids[0]<=ids[-1]<base+size<=data or
            not 0<span or data+span>2**64):
        raise ValueError('invalid RX/RW source layout')
    leaves={}
    for a,b in zip(ids,ids[1:]+[base+size]):
        p=off+a-base
        raw=image[p:p+min(12,b-a)]
        skip=4 if raw.startswith(b'\xf3\x0f\x1e\xfa') else 0
        r=raw[skip:]
        if len(r)>=8 and r[:3]==b'\x48\x8d\x05' and r[7]==0xc3:
            t=a+skip+7+int.from_bytes(r[3:7],'little',signed=True)
            if data<=t<data+span:
                leaves[a]=(raw[:skip+8],t)
    rows=expand_tail_aliases(image,rx,ids,leaves) if tail_aliases else leaves
    for a in sorted(rows):
        yield a,*rows[a]


def emit(rows,out):
    if not rows or any(a[0]>=b[0] for a,b in zip(rows,rows[1:])):
        raise ValueError('invalid or empty address rows')
    p=lambda s: print(s,file=out)
    p('#include "rip_v496.h"')
    p('static const struct {uint64_t id,target;} rip_rows_v496[]={')
    for a,_,t in rows:
        if not 0<=a<2**64 or not 0<=t<2**64:
            raise ValueError('out-of-range ID or target')
        p(f'{{UINT64_C({a}),UINT64_C({t})}},')
    p('};')
    p('static enum bb_rip_status_v496 rip_row_v496(size_t k,uint64_t slide,uint64_t flags,struct bb_result_v484 *out) {')
    p(' const uint64_t t=rip_rows_v496[k].target;')
    p(' if(!out||slide>UINT64_MAX-t)return BB_RIP_DENIED_V496;')
    p(' *out=(struct bb_result_v484){t+slide,flags,0x8d5};return BB_RIP_OK_V496;}')
    p('enum bb_rip_status_v496 bb_rip_v496(uint64_t id,uint64_t slide,uint64_t flags,struct bb_result_v484 *out) {')
    p(' size_t lo=0,n=sizeof rip_rows_v496/sizeof *rip_rows_v496,hi=n;')
    p(' while(lo<hi){size_t m=lo+(hi-lo)/2;if(rip_rows_v496[m].id<id)lo=m+1;else hi=m;}')
    p(' if(lo==n||rip_rows_v496[lo].id!=id)return BB_RIP_MISS_V496;')
    p(' return rip_row_v496(lo,slide,flags,out);}')


def main():
    import argparse
    import hashlib
    import mmap
    from pathlib import Path
    import struct
    import sys
    from census_v480 import census
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--elf',type=Path,required=True)
    p.add_argument('--sha256',required=True)
    p.add_argument('--first-load-slot',type=lambda s:int(s,0),required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    try:
        dst=a.output.absolute()
        if dst.exists() or any(x.is_symlink() or (x/'.git').exists()
                              for x in (dst,*dst.parents,*dst.resolve().parents)):
            raise ValueError('unsafe destination')
        if a.elf.is_symlink() or not a.elf.is_file() or not 64<=a.elf.stat().st_size<=512<<20:
            raise ValueError('invalid input')
        with a.elf.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as im:
            if hashlib.sha256(im).hexdigest()!=a.sha256:
                raise ValueError('wrong image')
            e={}
            g,_=census(im,a.first_load_slot,evidence=e)
            x=e['rx']
            if any(x[3]-7<=s<x[3]+x[5] for s in e['relocs']):
                raise ValueError('RX relocation')
            rows=list(find(im,x,e['rw'],g['entry']|g['unwind']|g['constructors']))
        if not rows:
            raise ValueError('empty output')
        dst.mkdir(mode=0o700)
        with (dst/'rip.c').open('x',encoding='ascii') as f:
            emit(rows,f)
        print(f'guest_data_address_ids={len(rows)}')
    except (OSError,ValueError,struct.error,KeyError):
        print('V496 refused: image, layout or output error',file=sys.stderr)
        return 2
    return 0


if __name__=='__main__':
    raise SystemExit(main())
