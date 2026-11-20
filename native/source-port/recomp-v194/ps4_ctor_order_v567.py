#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Read the legacy DT_INIT constructor order of one attested Bloodborne dump."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import struct

SHA = '941f887a562aae054fac35af8cc8f27cf075f3d4cc2e029fb5ae2a663aaa5ae7'
MASK = (1 << 64) - 1


def walk(first, lowest, raw, rel, executable):
    """The startup walker calls relocated pointers in descending slot order."""
    order = []
    for slot in range(first, lowest-1, -8):
        word = raw(slot)
        row = rel.get(slot)
        if row is None:
            if word == MASK:
                return order
            if word == 0:
                continue
        elif row[0] == 8 and executable(row[1]):
            order.append(row[1])
            continue
        raise ValueError('unexpected constructor slot')
    raise ValueError('constructor terminator missing')


def inspect(b):
    # The legacy walker addresses were independently read from the DT_INIT
    # disassembly. Do not apply this profile to another build.
    if sha256(b).hexdigest() != SHA:
        raise ValueError('unsupported executable hash')
    phoff = struct.unpack_from('<Q',b,32)[0]
    nph = struct.unpack_from('<H',b,56)[0]
    ph = list(struct.iter_unpack('<II6Q',b[phoff:phoff+56*nph]))

    def segment(typ):
        return next((o,v,n) for t,f,o,v,p,n,m,a in ph if t == typ)

    def read_word(a):
        off = next(o+a-v for t,f,o,v,p,n,m,al in ph if t==1 and v<=a<=v+n-8)
        return struct.unpack_from('<Q',b,off)[0]

    def executable(a):
        return any(t==1 and f&1 and v<=a<v+n for t,f,o,v,p,n,m,al in ph)

    do,_,ds = segment(2)
    tags = {}
    for k,v in struct.iter_unpack('<QQ',b[do:do+ds]):
        if not k:
            break
        tags[k] = v
    db,_,_ = segment(0x61000000)
    off,n = tags[0x6100002f],tags[0x61000031]
    rel = {slot:(info,value) for slot,info,value in
           struct.iter_unpack('<QQq',b[db+off:db+off+n])}
    first, lowest, forward_slot, forward = 0x53e3bb8, 0x50dc000, 0x53e3bd8, 0x53e5b38
    if (tags.get(12) != 0x20 or any(tags.get(k)!=0 for k in (0x1b,0x1c,0x21))
            or rel.get(forward_slot)!=(8,forward)):
        raise ValueError('unexpected startup metadata')
    order = walk(first,lowest,read_word,rel,executable)
    eh,ev,_ = segment(0x6474e550)
    ne = struct.unpack_from('<I',b,eh+8)[0]
    starts = {ev+struct.unpack_from('<i',b,eh+12+8*i)[0] for i in range(ne)}
    return order, starts


def self_test():
    raw = {32:0,24:0,16:0,8:MASK}
    rel = {32:(8,77),16:(8,77)}
    assert walk(32,8,raw.__getitem__,rel,lambda a:a==77)==[77,77]
    for bad, rows in (({**raw,8:0},rel), ({**raw,24:1},rel),
                      (raw,{**rel,16:(7,77)}), (raw,{**rel,16:(8,99)})):
        try:
            walk(32,8,bad.__getitem__,rows,lambda a:a==77)
        except ValueError:
            continue
        raise AssertionError('invalid constructor table accepted')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('elf',type=Path,nargs='?')
    p.add_argument('--self-test',action='store_true')
    a = p.parse_args()
    if a.self_test:
        self_test()
    if a.elf is not None:
        order, starts = inspect(a.elf.read_bytes())
        print(json.dumps(dict(entries=len(order), unique=len(set(order)),
                              unwind=sum(v in starts for v in order),
                              outside_unwind=sum(v not in starts for v in order))))
    elif not a.self_test:
        p.error('supply a decrypted dump or --self-test')


if __name__=='__main__':
    main()
