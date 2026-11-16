# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline lowering of bounded, straight-line RAX/flags functions."""
REG = {0:'a',1:'c',2:'d',6:'s',7:'i'}
OPS = {0:'ADD',1:'OR',4:'AND',5:'SUB',6:'XOR',7:'CMP'}


def decode(raw):
    p = 4 if raw.startswith(b'\xf3\x0f\x1e\xfa') else 0
    lines = []
    for _ in range(9):
        if raw[p:p+1] == b'\xc3':
            return (raw[:p+1], lines) if lines else None
        w = 64 if raw[p:p+1] == b'\x48' else 32
        p += w == 64
        if p+2 > len(raw):
            return None
        op,m = raw[p:p+2]
        p += 2
        if op==0x8d and m>>6!=3 and (m>>3)&7==0:
            mode,b=m>>6,m&7
            idx,scale=None,1
            if b==4:
                if p==len(raw):
                    return None
                sib=raw[p]
                p+=1
                b,j,scale=sib&7,(sib>>3)&7,1<<(sib>>6)
                if j!=4:
                    if j not in REG:
                        return None
                    idx=REG[j]
            if b not in REG:
                return None
            n=(0,1,4)[mode]
            if p+n>len(raw):
                return None
            v=int.from_bytes(raw[p:p+n],'little',signed=True)%2**64
            p+=n
            src=REG[b]+(f'+{idx}*{scale}u' if idx else '')+f'+UINT64_C({v})'
            k='MOV'
        elif op==0xb8:
            p-=1
            n=w//8
            if p+n>len(raw):
                return None
            src=f"UINT64_C({int.from_bytes(raw[p:p+n],'little')})"
            p+=n
            k='MOV'
        elif op in (0x81,0x83) and m & 0xc7 == 0xc0:
            k, n = OPS.get((m>>3)&7), 1 if op==0x83 else 4
            if p+n > len(raw):
                return None
            v = int.from_bytes(raw[p:p+n],'little',signed=True) % 2**64
            src = f'UINT64_C({v})'
            p += n
        elif op in (0x05,0x0d,0x25,0x2d,0x35,0x3d,0xa9):
            p -= 1
            if p+4 > len(raw):
                return None
            k = 'TEST' if op==0xa9 else OPS[op>>3]
            v = int.from_bytes(raw[p:p+4],'little',signed=True) % 2**64
            src = f'UINT64_C({v})'
            p += 4
        elif m>=0xc0:
            r,b = (m>>3)&7,m&7
            if op in (0x89,0x85) or op&7==1 and op<0x40:
                r,b = b,r
            k = {0x89:'MOV',0x8b:'MOV',0x85:'TEST'}.get(op)
            if op<0x40 and op&7 in (1,3):
                k = OPS.get(op>>3)
            if r or b not in REG:
                return None
            src = REG[b]
        else:
            return None
        if k is None:
            return None
        if k=='MOV':
            lines.append('a='+('(uint32_t)' if w==32 else '')+'('+src+');')
        else:
            dst = 'a=' if k not in ('CMP','TEST') else '(void)'
            lines.append(f'{dst}alu_v488(BB_{k},{w},a,{src},&flags,&mask);')
    return None


def find(im,x,roots,existing):
    _,_,off,base,_,size,_,_ = x
    ids = sorted(set(roots))
    if not ids or not 0<size<=len(im) or not 0<=off<=len(im)-size or not base<=ids[0]<=ids[-1]<base+size:
        raise ValueError('invalid roots')
    for a,b in zip(ids,ids[1:]+[base+size]):
        if a not in existing:
            p=off+a-base
            r=decode(im[p:p+min(64,b-a)])
            if r:
                yield a,*r


def emit(rows,out):
    if not rows or any(a[0]>=b[0] for a,b in zip(rows,rows[1:])):
        raise ValueError('empty or unsorted output')
    p=lambda s:print(s,file=out)
    p('#include "alu_v488.h"')
    sig='uint64_t a,uint64_t c,uint64_t d,uint64_t s,uint64_t i,uint64_t flags'
    for j,(_,_,lines) in enumerate(rows):
        p(f'static struct bb_result_v484 f{j}({sig}){{')
        p('uint64_t mask=0x8d5; (void)c;(void)d;(void)s;(void)i;')
        p(''.join(lines)+'return (struct bb_result_v484){a,flags,mask};}')
    p('static const struct {uint64_t id; struct bb_result_v484 (*fn)('+sig+');} rows[]={')
    for j,(a,*_) in enumerate(rows):
        p(f'{{UINT64_C({a}),f{j}}},')
    p('};')
    p('int bb_alu_call_v488(uint64_t id,'+sig+',struct bb_result_v484 *out){')
    p('size_t lo=0,hi=sizeof rows/sizeof rows[0];if(!out)return 0;')
    p('while(lo<hi){size_t m=lo+(hi-lo)/2;if(rows[m].id<id)lo=m+1;else hi=m;}')
    p('if(lo==sizeof rows/sizeof rows[0]||rows[lo].id!=id)return 0;')
    p('*out=rows[lo].fn(a,c,d,s,i,flags);return 1;}')
