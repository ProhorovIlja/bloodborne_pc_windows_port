# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline classifier for exactly one RDI-relative store followed by RET."""


def decode(raw):
    i=4 if raw.startswith(b'\xf3\x0f\x1e\xfa') else 0
    prefix=raw[i:i+1]
    width={b'\x66':2,b'\x48':8}.get(prefix,4)
    i+=width!=4
    if len(raw)<i+3:
        return None
    op,modrm=raw[i:i+2]
    i+=2
    n={7:0,0x47:1,0x87:4}.get(modrm&0xc7)
    if n is None or i+n>=len(raw):
        return None
    reg=(modrm>>3)&7
    disp=int.from_bytes(raw[i:i+n],'little',signed=True)
    i+=n
    value=0
    if op in (0xc6,0xc7) and reg==0:
        if op==0xc6:
            if width!=4:
                return None
            width=1
        k=min(width,4)
        if i+k>=len(raw):
            return None
        value=int.from_bytes(raw[i:i+k],'little',signed=width==8)%2**64
        i+=k
        reg=0
    elif op in (0x88,0x89) and reg in (1,2,6,7):
        if op==0x88:
            if width!=4 or reg not in (1,2):
                return None
            width=1
    else:
        return None
    return (raw[:i+1],disp,width,reg,value) if raw[i]==0xc3 else None


def find(image,x,roots):
    _,_,off,base,_,size,_,_=x
    starts=sorted(set(roots))
    if not starts or not 0<size<=len(image)-off or off<0 or not base<=starts[0]<=starts[-1]<base+size:
        raise ValueError('invalid executable span')
    for a,b in zip(starts,starts[1:]+[base+size]):
        p=off+a-base
        r=decode(image[p:p+min(16,b-a)])
        if r:
            yield a,*r


def emit(rows,out):
    if not rows or any(a[0]>=b[0] for a,b in zip(rows,rows[1:])):
        raise ValueError('empty or unordered table')
    print('#include "store_v491.h"',file=out)
    print('static const struct store_v491 stores[]={',file=out)
    for a,_,d,w,r,v in rows:
        print(f'{{UINT64_C({a}),UINT64_C({d%2**64}),UINT64_C({v}),{w},{r}}},',file=out)
    print('};',file=out)
    print('int bb_store_v491(uint64_t id,const struct bb_store_input_v491 *in,',file=out)
    print('    unsigned char *mem,uint64_t base,size_t size) {',file=out)
    print('    return store_dispatch_v491(stores,sizeof stores/sizeof *stores,id,in,mem,base,size);',file=out)
    print('}',file=out)


def main():
    import argparse
    import hashlib
    import json
    import mmap
    from pathlib import Path
    import struct
    import sys
    from census_v480 import census
    from progress_v490 import ratio
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--elf',required=True,type=Path)
    p.add_argument('--sha256',required=True)
    p.add_argument('--first-load-slot',required=True,type=lambda s:int(s,0))
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args()
    try:
        dst=a.output.absolute()
        if dst.exists() or any(v.is_symlink() or (v/'.git').exists() for v in (dst,*dst.parents,*dst.resolve().parents)):
            raise ValueError('unsafe output')
        if a.elf.is_symlink() or not a.elf.is_file() or not 64<=a.elf.stat().st_size<=512<<20:
            raise ValueError('unsafe input')
        with a.elf.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as im:
            if hashlib.sha256(im).hexdigest()!=a.sha256:
                raise ValueError('image digest mismatch')
            evidence={}
            g,_=census(im,a.first_load_slot,evidence=evidence)
            x=evidence['rx']
            if any(x[3]-7<=s<x[3]+x[5] for s in evidence['relocs']):
                raise ValueError('overlapping RX relocation')
            roots=g['entry']|g['unwind']|g['constructors']
            rows=list(find(im,x,roots))
        if not rows:
            raise ValueError('no stores')
        dst.mkdir(mode=0o700)
        with (dst/'stores.c').open('x',encoding='ascii') as f:
            emit(rows,f)
        print(json.dumps(dict(store_ids=ratio(len(rows),len(roots)),
                              constructor_ids=len(g['constructors']&{a for a,*_ in rows}),
                              full_game_link_proven=False),sort_keys=True))
    except (OSError,ValueError,KeyError,struct.error):
        print('V491 refused: input, output or provenance error',file=sys.stderr)
        return 2
    return 0


if __name__=='__main__':
    raise SystemExit(main())
