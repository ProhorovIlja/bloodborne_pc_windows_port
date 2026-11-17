#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline import/link evidence for the pinned CUSA03173 1.09 ELF.

Inspired by bloodborne-recomp tools/recomp/imports.py (join on GOT slot).
This independent scanner verifies the indexed PS4 PLT encoding as well.
The CLI emits counts only; identities and addresses stay local to the audit.
"""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
import struct

from ps4_ctor_order_v567 import SHA


SCE = 0x61000000
RELA = struct.Struct('<QQq')
STUB = struct.Struct('<2siBiBi')


def span(data, start, size):
    if start < 0 or size < 0 or start + size > len(data):
        raise ValueError('invalid file span')
    return data[start:start+size]


def indexed_plt(rx, va, plt):
    """Return verified stub RVAs in relocation order; no heuristic fallback."""
    heads = set()
    for m in re.finditer(rb'\xff\x25....\x68\x00\x00\x00\x00\xe9', rx, re.S):
        a = m.start()
        if a + 16*len(plt) > len(rx):
            continue
        if all((jmp, push, idx, tail, va+p+6+disp, p+16+back) ==
               (b'\xff\x25', 0x68, i, 0xe9, slot, a-16)
               for i, (slot, _, _) in enumerate(plt)
               for p in (a+16*i,)
               for jmp, disp, push, idx, tail, back in (STUB.unpack_from(rx,p),)):
            heads.add(a)
    if len(heads) != 1:
        raise ValueError('expected one indexed PLT')
    start = heads.pop()
    if start < 16 or rx[start-16:start-14] != b'\xff\x35' or rx[start-10:start-8] != b'\xff\x25':
        raise ValueError('invalid PLT resolver')
    return [va+start+16*i for i in range(len(plt))]


def audit(data):
    if sha256(data).hexdigest() != SHA:
        raise ValueError('unsupported executable hash')
    view = memoryview(data)
    phoff = struct.unpack_from('<Q', view, 32)[0]
    nph = struct.unpack_from('<H', view, 56)[0]
    ph = list(struct.iter_unpack('<II6Q', span(view,phoff,nph*56)))
    dyn = next(p for p in ph if p[0]==2)
    dynlib = next(p for p in ph if p[0]==SCE)
    tags = {}
    for k,v in struct.iter_unpack('<QQ', span(view,dyn[2],dyn[5])):
        if not k:
            break
        tags.setdefault(k,[]).append(v)
    blob = span(view,dynlib[2],dynlib[5])
    def section(off,size):
        a, = tags[SCE+off]
        n, = tags[SCE+size]
        return span(blob,a,n)
    plt = list(RELA.iter_unpack(section(0x29,0x2d)))
    rela = list(RELA.iter_unpack(section(0x2f,0x31)))
    symbols = list(struct.iter_unpack('<IBBHQQ',section(0x39,0x3f)))
    strings = bytes(section(0x35,0x37))
    def name(o):
        return strings[o:strings.index(b'\0',o)].decode('ascii')
    def ids(tag):
        rows = {}
        for v in tags.get(SCE+tag,[]):
            key, value = v>>48,(name(v&0xffffffff),(v>>32)&0xffff)
            if key in rows and rows[key]!=value:
                raise ValueError('conflicting import namespace ID')
            rows[key]=value
        return rows
    modules,libraries = ids(0x0f),ids(0x15)
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+-'
    def decode(key):
        v = 0
        for c in key:
            v = (v<<6)|alphabet.index(c)
        return v
    if not plt or any((info&0xffffffff)!=7 or a for _,info,a in plt):
        raise ValueError('unexpected PLT relocation')
    rx = next(p for p in ph if p[0]==1 and p[1]&1)
    stubs = indexed_plt(bytes(span(view,rx[2],rx[5])),rx[3],plt)
    counts = Counter()
    namespaces = set()
    identities = set()
    seen = set()
    imports = Counter()
    by_kind = {}
    weak = set()
    for slot,info,_ in plt+rela:
        typ,sym = info&0xffffffff,info>>32
        counts[typ]+=1
        if slot in seen:
            raise ValueError('duplicate relocation slot')
        seen.add(slot)
        if not sym:
            continue
        offset,info_byte,_,defined,_,_ = symbols[sym]
        if defined:
            continue
        nid,lib,mod = name(offset).split('#')
        module,library = modules[decode(mod)],libraries[decode(lib)]
        namespaces.add((module,library))
        identity = nid,module,library
        identities.add(identity)
        by_kind.setdefault(typ,set()).add(identity)
        if info_byte>>4 == 2:
            weak.add(identity)
        imports[typ]+=1
    return dict(verified_plt=len(stubs), relocation_counts=dict(counts),
                external_relocations=dict(imports), external_identities=len(identities),
                module_library_pairs=len(namespaces), weak_identities=len(weak),
                identities_by_kind={k:len(v) for k,v in by_kind.items()},
                identities_not_in_plt=len(identities-by_kind[7]),
                repeated_nid_namespaces=len(identities)-len({nid for nid,_,_ in identities}),
                bundled_module_identities=sum(m[0] in ('libc','libSceFios2') for _,m,_ in identities),
                unique_module_names=len({m[0] for _,m,_ in identities}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump',type=Path)
    print(json.dumps(audit(p.parse_args().dump.read_bytes()),sort_keys=True))
