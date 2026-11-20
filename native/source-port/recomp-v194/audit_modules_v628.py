#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline, aggregate link census of eboot and its two bundled startup PRXs.

The blocked SELF segment layout follows bloodborne-recomp tools/recomp/ps4elf.py
(bbport prepare.py lineage, GPL-2.0+). Never writes a reconstructed image.
"""
import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import struct

from audit_imports_v627 import RELA, SCE, span
from ps4_ctor_order_v567 import SHA

PINS = (SHA,
        '4378b47f46f1d856824a6f971db1a0c3f41833b77f49d2fba9538f667a139166',
        '3b8eb4d5a5c5a7b381d8d0610077e6cd404c29695a686274802f6b2737f6bf22')
PH = struct.Struct('<II6Q')
SYM = struct.Struct('<IBBHQQ')
ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+-'


def file_reader(data):
    base, blocks = 0, []
    if data[:4] == b'O\x15=\x1d':
        n, = struct.unpack('<H', span(data,24,2))
        base = 32+32*n
        blocks = list(struct.iter_unpack('<QQQQ', span(data,32,32*n)))
    h = struct.unpack('<16sHHIQQQIHHHHHH', span(data,base,64))
    if h[0][:7]!=b'\x7fELF\x02\x01\x01' or h[2]!=62 or h[9]!=56 or not 0<h[10]<256:
        raise ValueError('unsupported embedded ELF header')
    ph = list(PH.iter_unpack(span(data,base+h[5],56*h[10])))
    segments = []
    for f,o,n,m in blocks:
        if not f&0x800:
            continue
        i = (f>>20)&4095
        if f&10 or i>=len(ph) or n!=m or n!=ph[i][5]:
            raise ValueError('unsupported SELF block')
        v = ph[i][2]
        segments.append((v,v+n,span(data,o,n)))
    def read(off,size):
        if not base:
            return span(data,off,size)
        matches = [(lo,p) for lo,hi,p in segments if lo<=off and off+size<=hi]
        if len(matches)!=1:
            raise ValueError('SELF span does not have a unique file backing')
        lo, backing = matches[0]
        return span(backing,off-lo,size)
    return ph,read


def link_tables(data, *, details=None):
    ph,read = file_reader(memoryview(data))
    dynamic, = (p for p in ph if p[0]==2)
    dynlib, = (p for p in ph if p[0]==SCE)
    tags = defaultdict(list)
    for t,v in struct.iter_unpack('<QQ',read(dynamic[2],dynamic[5])):
        if not t:
            break
        tags[t].append(v)
    else:
        raise ValueError('unterminated dynamic table')
    blob = read(dynlib[2],dynlib[5])
    def section(o,s):
        off, = tags[SCE+o]
        size, = tags[SCE+s]
        return span(blob,off,size)
    strings = bytes(section(0x35,0x37))
    def name(o):
        return strings[o:strings.index(b'\0',o)].decode('ascii')
    def ids(t):
        r = {}
        for v in tags[SCE+t]:
            k, identity = v>>48,(name(v&0xffffffff),(v>>32)&0xffff)
            if r.setdefault(k,identity)!=identity:
                raise ValueError('conflicting namespace')
        return r
    ns = {False:(ids(0x0f),ids(0x15)),True:(ids(0x0d),ids(0x13))}
    def decode(s):
        v = 0
        for c in s:
            v = v*64+ALPHABET.index(c)
        return v
    symbols = list(SYM.iter_unpack(section(0x39,0x3f)))
    def identity(row):
        parts = name(row[0]).split('#')
        if len(parts)!=3:
            return None
        nid,lib,mod = parts
        mods,libs = ns[bool(row[3])]
        return nid,mods[decode(mod)],libs[decode(lib)]
    exports = defaultdict(set)
    for row in symbols:
        if row[3] and row[1]>>4 in (1,2):
            key = identity(row)
            if key:
                exports[key].add((row[1]&15,row[4]))
                if details is not None:
                    details.setdefault('exports', {}).setdefault(key,set()).add((row[1]&15,row[4],row[5]))
    imports = defaultdict(set)
    relocations, special = Counter(), Counter()
    for a,b in ((0x29,0x2d),(0x2f,0x31)):
        for slot,info,addend in RELA.iter_unpack(section(a,b)):
            if details is not None:
                details.setdefault('relocations', []).append((slot,info,addend))
            index, kind = info>>32, info&0xffffffff
            if index and not symbols[index][3]:
                key = identity(symbols[index])
                if key is None:
                    row = symbols[index]
                    if kind==16 and row==(0,3,0,0,0,0):
                        special['local_tls_module']+=1
                    elif kind==7 and row[1]>>4==2 and name(row[0]) in ('module_start','module_stop'):
                        special['weak_lifecycle']+=1
                    else:
                        raise ValueError('unknown unqualified relocation')
                    continue
                if details is not None:
                    details.setdefault('imports', {}).setdefault(key,[]).append((slot,kind,addend))
                imports[key].add(kind)
                relocations[kind]+=1
    return imports,exports,relocations,special


def census(blobs):
    if tuple(sha256(b).hexdigest() for b in blobs)!=PINS:
        raise ValueError('unsupported eboot/PRX hash or module order')
    names = ('eboot','libc','libSceFios2')
    tables = dict(zip(names,map(link_tables,blobs)))
    providers = defaultdict(set)
    for mod in names[1:]:
        for key,definitions in tables[mod][1].items():
            providers[key].update((mod,*definition) for definition in definitions)
    missing = set()
    result = {}
    for mod,(imports,exports,relocs,special) in tables.items():
        c = Counter()
        for key in imports:
            matches = providers[key]
            if len(matches)>1:
                raise ValueError('ambiguous bundled symbol')
            if matches:
                provider,kind,_ = next(iter(matches))
                c[f'{provider}:type{kind}']+=1
            else:
                missing.add(key)
                c['external']+=1
                if key[1][0] in names[1:]:
                    c['missing_bundled_namespace']+=1
        result[mod] = dict(imports=len(imports), exports=len(exports),
                           bindings=dict(c), external_relocations=dict(relocs), special=dict(special))
    return dict(images=result, unresolved_unique=len(missing),
                unresolved_modules=dict(Counter(k[1][0] for k in missing)))


if __name__=='__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('eboot','libc','fios2'):
        p.add_argument(key,type=Path)
    a = p.parse_args()
    print(json.dumps(census([f.read_bytes() for f in (a.eboot,a.libc,a.fios2)]),sort_keys=True))
