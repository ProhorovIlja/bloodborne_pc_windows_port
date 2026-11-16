#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Census of one exact guard + address-point publication startup family."""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct
from ps4_ctor_order_v567 import inspect


def decode(code, rva):
    if (len(code)!=41 or code[:3]!=b'\x48\x8d\x05'
        or code[7:15]!=b'\x80\x38\x00\x75\x1c\x48\x8d\x0d'
        or code[19:26]!=b'\x48\x83\xc1\x10\x48\x8d\x15'
        or code[30:]!=b'\x48\x89\x0a\x48\xc7\x00\x01\0\0\0\xc3'):
        return None
    disp = lambda i: struct.unpack_from('<i',code,i)[0]
    guard, dst, target = rva+7+disp(3), rva+30+disp(26), rva+35+disp(15)
    if guard-dst!=8 or (guard|dst|target)&7:
        return None
    return guard,dst,target


def inspect_family(blob):
    order,_ = inspect(blob)
    p = struct.unpack_from('<Q',blob,32)[0]
    n = struct.unpack_from('<H',blob,56)[0]
    loads = [(f,o,v,fs,ms) for typ,f,o,v,_,fs,ms,_ in
             struct.iter_unpack('<II6Q',blob[p:p+56*n]) if typ==1]
    counts = Counter()
    ordinals = []
    for i,rva in enumerate(order,1):
        offsets = [o+rva-v for f,o,v,fs,ms in loads if f&1 and v<=rva<=v+fs-41]
        if len(offsets)!=1:
            continue
        o = offsets[0]
        row = decode(blob[o:o+41],rva)
        if row is None:
            continue
        guard,dst,target = row
        if not any(f&2 and v<=dst and guard<=v+ms-8 for f,o,v,fs,ms in loads):
            raise ValueError('publication outside writable data')
        if not any(v<=target<=v+fs-8 for f,o,v,fs,ms in loads):
            raise ValueError('address point outside file-backed data')
        counts[row]+=1
        ordinals.append(i)
    return dict(entries=len(ordinals), unique_plans=len(counts),
                unique_guards=len({g for g,d,t in counts}),
                before_90=sum(i<90 for i in ordinals),
                first=min(ordinals,default=None),last=max(ordinals,default=None))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dump',type=Path)
    print(json.dumps(inspect_family(p.parse_args().dump.read_bytes()),sort_keys=True))
