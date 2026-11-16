# SPDX-License-Identifier: GPL-2.0-or-later
"""Relocation-backed edge identities, not native implementations or routing permission."""
from collections import Counter, defaultdict
import struct
from plan_symbol_reloc_v467 import extract


def rip_slot(pc, raw, kind):
    if len(raw)==7 and raw[0] in (0x48,0xf2,0x3e):
        raw=raw[1:]
        pc+=1
    op={'indirect_call':b'\xff\x15','indirect_jump':b'\xff\x25'}.get(kind)
    if len(raw)!=6 or raw[:2]!=op:
        return None
    return pc+6+struct.unpack_from('<i',raw,2)[0]


def import_index(im, evidence):
    tags, sce = evidence['tags'], evidence['dynlib']
    def table(a,b):
        off, size = tags[a], tags[b]
        if not 0 < size <= 32<<20 or not 0 <= off <= sce[5]-size:
            raise ValueError('invalid symbol metadata span')
        return im[sce[2]+off:sce[2]+off+size]
    reloc, w = evidence['relocs'], evidence['rw']
    end=w[3]
    for slot in sorted(reloc):
        if not end<=slot<=w[3]+w[6]-8:
            raise ValueError('overlapping or invalid relocation')
        end=slot+8
    entries=extract(((s,*row) for s,row in reloc.items()),
                    table(0x61000039,0x6100003f),table(0x61000035,0x61000037))
    return {s:(k,a,key) for s,k,a,key in entries}


class Edges:
    def __init__(self, image, evidence, imports):
        self.image=image
        self.rx=evidence['rx']
        self.rw=evidence['rw']
        self.rel=evidence['relocs']
        self.order=evidence['plt_order']
        self.imports=imports
        self.count=Counter()
        self.keys=defaultdict(set)
        self.thunks=set()
        self.resolvers=set()
        self.cache={}

    def span(self, a, n):
        _,_,off,base,_,size,_,_=self.rx
        return self.image[off+a-base:off+a-base+n] if base<=a<=base+size-n else b''

    def got_backlink(self, slot, pc):
        _,_,off,base,_,size,_,_=self.rw
        return (base<=slot<=base+size-8 and
                struct.unpack_from('<Q',self.image,off+slot-base)[0]==pc+6)

    def thunk(self, pc):
        if pc in self.cache:
            return self.cache[pc]
        c=self.span(pc,16)
        s=rip_slot(pc,c[:6],'indirect_jump')
        row=self.imports.get(s)
        key=None
        if (len(c)==16 and row and row[0]==7 and row[2][3]==2 and s in self.order
                and self.got_backlink(s,pc) and c[6]==0x68 and c[11]==0xe9 and struct.unpack_from('<I',c,7)[0]==self.order[s]):
            resolver=pc+16+struct.unpack_from('<i',c,12)[0]
            head=self.span(resolver,16)
            if head[:2]==b'\xff\x35' and head[6:8]==b'\xff\x25' and head[12:]==b'\x90'*4:
                self.resolvers.add(resolver)
                self.thunks.add(pc)
                key=row[2]
        self.cache[pc]=key
        return key

    def observe(self, pc, raw, kind, target):
        if target is not None:
            key=self.thunk(target)
            if key is not None:
                self.count['plt_'+kind]+=1
                self.keys['plt_'+kind].add(key)
            return
        if kind not in ('indirect_call','indirect_jump'):
            return
        slot=rip_slot(pc,raw,kind)
        label='other_operand'
        if slot is not None:
            row=self.imports.get(slot)
            if row:
                k,a,key=row
                label='function_import' if key[3]==2 and (k!=1 or a==0) else 'other_symbol'
                self.keys[kind+'_'+label].add(key)
            elif slot in self.rel:
                k,a=self.rel[slot]
                label='relative_rx_candidate' if k==8 and self.span(a,1) else 'other_relocation'
            else:
                label='no_relocation'
        self.count[kind+'_'+label]+=1

    def summary(self):
        return dict(sites=dict(self.count), scoped_keys={k:len(v) for k,v in self.keys.items()},
                    distinct_plt_thunks=len(self.thunks), plt_resolver_shapes=len(self.resolvers),
                    distinct_import_keys=len(set().union(*self.keys.values())),
                    native_bindings_proven=False)
