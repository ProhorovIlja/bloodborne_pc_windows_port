# SPDX-License-Identifier: GPL-2.0-or-later
"""Exact little-endian MOV/MOVZX/MOVSX leaves using [RDI+disp]."""
FORMS = {bytes.fromhex(h): (width, bits, signed) for h,width,bits,signed in (
    ('8b',4,32,False),('488b',8,64,False),('4863',4,64,True),
    ('0fb6',1,32,False),('0fb7',2,32,False),('480fb6',1,64,False),('480fb7',2,64,False),
    ('0fbe',1,32,True),('0fbf',2,32,True),('480fbe',1,64,True),('480fbf',2,64,True))}


def decode(raw):
    skip=4 if raw.startswith(b'\xf3\x0f\x1e\xfa') else 0
    for op, form in FORMS.items():
        i=skip+len(op)
        if len(raw)<=i or raw[skip:i]!=op:
            continue
        n={7:0,0x47:1,0x87:4}.get(raw[i])
        if n is None or raw[i+1+n:i+2+n]!=b'\xc3':
            continue
        return raw[:i+2+n],int.from_bytes(raw[i+1:i+1+n],'little',signed=True),*form
    return None


def find(image, x, roots):
    _,_,off,base,_,size,_,_=x
    ids=sorted(set(roots))
    if not ids or not 0<size<=len(image) or not 0<=off<=len(image)-size or not base<=ids[0]<=ids[-1]<base+size:
        raise ValueError('invalid source extent')
    for a,b in zip(ids,ids[1:]+[base+size]):
        p=off+a-base
        r=decode(image[p:p+min(15,b-a)])
        if r:
            yield (a,*r)


def emit(rows,out):
    if not rows or any(a[0]>=b[0] for a,b in zip(rows,rows[1:])):
        raise ValueError('expected sorted nonempty entries')
    p=lambda s:print(s,file=out)
    p('#include "load_v486.h"')
    p('static const struct {uint64_t id, disp; unsigned width,bits,sign;} rows[]={')
    for a,_,d,w,b,s in rows:
        p(f'{{UINT64_C({a}),UINT64_C({d % 2**64}),{w},{b},{int(s)}}},')
    p('};')
    p('int bb_load_v486(uint64_t id,uint64_t rdi,const struct bb_region_v478 *r,uint64_t *out) {')
    p(' size_t lo=0,hi=sizeof rows/sizeof rows[0]; if(!out||!r||r->size>UINT64_MAX-r->base)return 0;')
    p(' while(lo<hi){size_t m=lo+(hi-lo)/2;if(rows[m].id<id)lo=m+1;else hi=m;}')
    p(' if(lo==sizeof rows/sizeof rows[0]||rows[lo].id!=id)return 0;')
    p(' unsigned n=rows[lo].width; const unsigned char *b=bb_memory_at_v478(r,rdi+rows[lo].disp,n);')
    p(' if(!b)return 0;')
    p(' uint64_t x=0;')
    p(' for(unsigned i=0;i<n;++i)x|=(uint64_t)b[i]<<(8*i);')
    p(' if(rows[lo].sign){uint64_t s=UINT64_C(1)<<(n*8-1);x=(x^s)-s;}')
    p(' *out=rows[lo].bits==32?(uint32_t)x:x;return 1;}')


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
        if dst.exists() or any(x.is_symlink() or (x/'.git').exists() for x in (dst,*dst.parents,*dst.resolve().parents)):
            raise ValueError
        if a.elf.is_symlink() or not a.elf.is_file() or not 64<=a.elf.stat().st_size<=512<<20:
            raise ValueError
        with a.elf.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as im:
            if hashlib.sha256(im).hexdigest()!=a.sha256:
                raise ValueError
            e={}
            g,_=census(im,a.first_load_slot,evidence=e)
            x=e['rx']
            if any(x[3]-7<=s<x[3]+x[5] for s in e['relocs']):
                raise ValueError
            rows=list(find(im,x,g['entry']|g['unwind']|g['constructors']))
        if not rows:
            raise ValueError
        dst.mkdir(mode=0o700)
        with (dst/'native_loads.c').open('x',encoding='ascii') as f:
            emit(rows,f)
        print(f'emitted_memory_leaf_ids={len(rows)}')
    except (OSError,ValueError,struct.error,KeyError):
        print('V486 refused: input, output or provenance error',file=sys.stderr)
        return 2
    return 0


if __name__=='__main__':
    raise SystemExit(main())
