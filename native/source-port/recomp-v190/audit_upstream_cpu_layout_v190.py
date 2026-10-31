#!/usr/bin/env python3
"""V190: source-pin *prefix* of bbrecomp's public CPU ABI, no game input.

Deliberately does NOT claim full BbCpu compatibility. Only the fields used by
our six simple leaves are checked, including SSE 32-byte register placement.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re

PIN='8f31ec7c41f252730c6325d52647046baef7549f'
FIELDS=('uint64_t r[16];','uint64_t rip;','uint64_t flags;','BbVec v[16];')
VEC=('uint8_t b[32];','float f[8];')

class LayoutMismatch(ValueError):pass

def normalize(src:str):
    src=re.sub(r'/\*.*?\*/','',src,flags=re.S)
    src=re.sub(r'//[^\n]*','',src)
    return re.sub(r'\s+',' ',src)

def audit(src:str):
    text=normalize(src)
    if not re.search(r'typedef\s+struct\s+BbCpu\s*\{',text):
        raise LayoutMismatch('missing original BbCpu declaration')
    after=text.split('typedef struct BbCpu {',1)[1]
    offset=0
    for field in FIELDS:
        at=after.find(field,offset)
        if at<0:
            raise LayoutMismatch('CPU prefix field missing or reordered')
        intervening=after[offset:at].strip()
        # Exact first four fields, no silently introduced preceding ABI member.
        if intervening:
            raise LayoutMismatch('unexpected BbCpu prefix fields')
        offset=at+len(field)
    vec_start=text.find('typedef union {')
    if vec_start<0:raise LayoutMismatch('missing 32-byte upstream vector union')
    vec=text[vec_start:text.find('} BbVec;',vec_start)]
    if any(x not in vec for x in VEC):
        raise LayoutMismatch('upstream vector register fields drifted')
    return {'upstream_public_pin':PIN[:12],'prefix_register_qwords':16,
            'rip_offset_bytes':128,'flags_offset_bytes':136,
            'vector_registers_offset_bytes':144,'vector_lane_bytes':32,
            'exact_complete_BbCpu_verified':False,
            'actual_game_code_in_CI':False}

def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument('--upstream-root',type=Path,required=True)
    args=p.parse_args(argv)
    path=args.upstream_root/'src/cpu/cpu_internal.h'
    if path.is_symlink() or not path.is_file() or path.stat().st_size>150000:
        raise SystemExit('source-pinned public CPU header missing or exceeds cap')
    result=audit(path.read_text(encoding='utf-8'))
    print(json.dumps(result,separators=(',',':')))

if __name__=='__main__':main()
