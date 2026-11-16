#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline constructor atlas; derives bounds from unwind metadata, never runs code.

Only emits aggregate counts and selected ordinal ranges. Missing FDEs are not guessed.
Supports the GNU EH header and zR/pcrel-sdata4 CIE encoding used by the target.
"""
import argparse
import bisect
from collections import Counter
import json
import mmap
from pathlib import Path
import struct
import sys

PT_LOAD, EH_FRAME = 1, 0x6474e550


def unwind_index(image, parts):
    loads = sorted((p[3], p[3]+p[5], p[2], p[1]) for p in parts if p[0] == PT_LOAD and p[5])
    starts = [p[0] for p in loads]
    if any(not 0 <= f <= len(image) or end-start > len(image)-f
           for start, end, f, _ in loads) or any(a[1] > b[0] for a,b in zip(loads,loads[1:])):
        raise ValueError('invalid load spans')

    def locate(va, size, executable=False):
        i = bisect.bisect_right(starts, va)-1
        if i < 0 or size <= 0:
            raise ValueError('unmapped span')
        start,end,offset,flags = loads[i]
        if va+size > end or (executable and not flags & 1):
            raise ValueError('unmapped span')
        return offset+va-start

    headers = [p for p in parts if p[0] == EH_FRAME]
    if len(headers) != 1:
        raise ValueError('expected one unwind header')
    _,_,off,va,_,size,_,_ = headers[0]
    if size < 12 or off != locate(va,size) or image[off:off+4] != b'\x01\x1b\x03\x3b':
        raise ValueError('unsupported unwind header')
    ptr,count = struct.unpack_from('<iI',image,off+4)
    first = va+4+ptr
    locate(first,8)
    if not 0 < count <= 1_000_000 or 12+8*count > size:
        raise ValueError('unwind count outside header')
    index, cies = {}, {}
    previous = -1
    for loc,rel in struct.iter_unpack('<ii',image[off+12:off+12+8*count]):
        address,fde = va+loc,va+rel
        if address <= previous or fde < first:
            raise ValueError('unordered or invalid FDE index')
        previous = address
        file = locate(fde,16)
        length,back,pc,extent = struct.unpack_from('<IIii',image,file)
        if not 12 <= length <= 65536 or not back or address != fde+8+pc:
            raise ValueError('invalid FDE record')
        locate(fde,4+length)
        cie = fde+4-back
        if not first <= cie < fde:
            raise ValueError('invalid CIE reference')
        if cie not in cies:
            cf = locate(cie,8)
            clen,tag = struct.unpack_from('<II',image,cf)
            if tag or not 8 <= clen <= 4096 or cie+4+clen > fde:
                raise ValueError('invalid CIE record')
            locate(cie,4+clen)
            # Exact, narrow variant: v1, zR, code align 1, data align -8,
            # return register 16, one augmentation byte: pcrel sdata4.
            cies[cie] = image[cf+8:cf+17] == b'\x01zR\x00\x01\x78\x10\x01\x1b'
        if cies[cie]:
            locate(address,extent,True)
            index[address] = extent
    return index, count


def summarize(targets, index, lo, hi):
    if not 1 <= lo <= hi <= len(targets):
        raise ValueError('ordinal range outside table')
    counts = Counter(index[t] for t in targets[lo-1:hi] if t in index)
    return dict(first=lo,last=hi,with_unwind=sum(counts.values()),
                without_unwind=hi-lo+1-sum(counts.values()),
                covered_byte_sum=sum(n*k for n,k in counts.items()),
                retail_execution_proven=False)


def self_test():
    im = bytearray(512)
    parts = [(1,5,0,0,0,512,512,1),(EH_FRAME,4,256,256,0,20,20,1)]
    struct.pack_into('<I4s',im,64,16,b'\0'*4)
    im[72:81] = b'\x01zR\x00\x01\x78\x10\x01\x1b'
    struct.pack_into('<IIii',im,84,12,24,16-92,8)
    struct.pack_into('<4sii2i',im,256,b'\x01\x1b\x03\x3b',64-260,1,16-256,84-256)
    assert unwind_index(im,parts)==({16:8},1)
    assert summarize([16,32],{16:8},1,2)['without_unwind']==1
    for pos in (256,264,272,92,99):
        bad=bytearray(im);bad[pos]^=0xff
        try:
            unwind_index(bad,parts)
        except ValueError:
            continue
        raise AssertionError('accepted damaged record')
    print('NATIVE_STARTUP_ATLAS_PASS')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--self-test',action='store_true')
    p.add_argument('--elf',type=Path)
    p.add_argument('--first-load-slot',type=lambda x:int(x,0))
    p.add_argument('--range',nargs=2,type=int,metavar=('FIRST','LAST'))
    a=p.parse_args()
    if a.self_test and a.elf is None and a.first_load_slot is None and a.range is None:
        self_test();return 0
    if a.self_test or a.elf is None or a.first_load_slot is None:
        p.error('specify --self-test or a private ELF and first-load slot')
    from audit_first_load_v440 import from_first_load
    from audit_private_ctor_closure_v410 import EH, PH
    try:
        if a.elf.is_symlink() or not a.elf.is_file() or not 64 <= a.elf.stat().st_size <= 512<<20:
            raise ValueError('unsafe ELF')
        with a.elf.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as im:
            targets,_=from_first_load(im,a.first_load_slot)
            h=EH.unpack_from(im)
            parts=[PH.unpack_from(im,h[5]+i*PH.size) for i in range(h[10])]
            idx,n=unwind_index(im,parts)
            report=summarize(targets,idx,*(a.range or [1,len(targets)]))
            print(json.dumps(dict(unwind_rows=n,supported_fdes=len(idx),**report),sort_keys=True))
    except (ValueError,OSError,struct.error):
        print('private startup atlas refused',file=sys.stderr);return 2
    return 0


if __name__=='__main__':
    raise SystemExit(main())
