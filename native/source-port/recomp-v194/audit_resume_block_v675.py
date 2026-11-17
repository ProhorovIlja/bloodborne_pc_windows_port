# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline partial continuation emitter: XOR reg32,reg32; JMP rel8/rel32."""
import argparse
import json
from pathlib import Path
from struct import iter_unpack, unpack_from
from audit_resume_branch_v674 import audit, decode as decode_branch


def blocks(path, *, resumes=None):
    if resumes is None:
        resumes = []
        audit(path, resumes=resumes)
    blob = path.read_bytes()
    off, = unpack_from('<Q', blob, 32)
    count, = unpack_from('<H', blob, 56)
    (rx,) = [p for p in iter_unpack('<II6Q', blob[off:off+56*count]) if p[0]==1 and p[1]&1]
    bias = rx[2]-rx[3]
    lo, hi = rx[3], rx[3]+rx[5]
    branches = [r for pc, f in resumes if (r := decode_branch(blob, f, pc)) is not None]
    rows = {}
    for pc in {t for branch in branches for t in branch if lo <= t < hi}:
        for prefix, reg in ((b'\x31\xdb', 0), (b'\x45\x31\xf6', 1), (b'\x45\x31\xff', 2)):
            pos = pc+bias
            end = pos+len(prefix)
            if blob[pos:end] != prefix or end >= hi+bias:
                continue
            width = {0xeb: 1, 0xe9: 4}.get(blob[end])
            if not width or end+1+width > hi+bias:
                continue
            after = end+1+width
            target = after-bias+int.from_bytes(blob[end+1:after], 'little', signed=True)
            if lo <= target < hi:
                rows[pc] = (reg, target, blob[pos:after])
    return branches, rows


def emit(rows):
    lines = ['#include <stdint.h>',
             'int bb_resume_block(uint64_t pc, uint64_t regs[3], uint64_t *flags, uint64_t *next) {',
             '    switch (pc) {']
    for pc, (reg, target, _) in sorted(rows.items()):
        # XOR defines CF, PF, ZF, SF and OF. AF is undefined.
        lines.append(f'    case 0x{pc:x}: regs[{reg}]=0; *flags=(*flags & ~UINT64_C(0x8c5)) | 0x44; *next=0x{target:x}; return 1;')
    return '\n'.join(lines+['    default: return 0;', '    }', '}', ''])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot', type=Path)
    p.add_argument('--emit-c', type=Path, help='new local C file; never commit output')
    a = p.parse_args()
    branches, rows = blocks(a.eboot)
    if a.emit_c:
        with a.emit_c.open('x') as out:
            out.write(emit(rows))
    print(json.dumps(dict(blocks=len(rows), zero=sum(z in rows for z, _ in branches),
                          nonzero=sum(n in rows for _, n in branches))))


if __name__ == '__main__':
    main()
