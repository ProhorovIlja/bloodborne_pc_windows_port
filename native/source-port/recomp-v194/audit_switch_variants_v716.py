# SPDX-License-Identifier: GPL-2.0-or-later
"""Audit additional adjacent bounded switch candidates at V714 indirect jumps.

Decoded targets and local reachability are evidence, not donor or runtime coverage.
Only same-register compare/index and an adjacent RIP-relative base are accepted.
"""
import argparse
from bisect import bisect_right
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import re
from struct import iter_unpack, unpack_from
import subprocess
from tempfile import TemporaryDirectory

from audit_switch_flow_v714 import SHA, decode, extents, scan, walk

REG = dict(zip('eax ecx edx ebx esp ebp esi edi'.split(),
               'rax rcx rdx rbx rsp rbp rsi rdi'.split()))
REG.update({f'r{i}d': f'r{i}' for i in range(8, 16)})


def candidate(data, start, insns, pcs):
    cmp, ja, lea, mov, add, jump = pcs
    if any(a+insns[a][0] != b for a,b in zip(pcs, pcs[1:])):
        return None
    parts = [(insns[p][1], insns[p][2].split('#', 1)[0].strip().replace(' ', '')) for p in pcs]
    if tuple((o[:-1] if o in ('cmpq','cmpl','leaq','addq','jmpq','movslq') else o) for o, _ in parts) != ('cmp','ja','lea','movsl','add','jmp'):
        return None
    c = re.fullmatch(r'\$(0x[\da-f]+|\d+),%(\w+)', parts[0][1])
    b = re.fullmatch(r'(-?(?:0x[\da-f]+|\d+))?\(%rip\),%(\w+)', parts[2][1])
    m = re.fullmatch(r'\(%(\w+),%(\w+),4\),%(\w+)', parts[3][1])
    if not (c and b and m):
        return None
    index, reg, dst = c[2], b[2], m[3]
    if (m[1], m[2], parts[4][1], parts[5][1]) != (reg, REG.get(index,index), f'%{reg},%{dst}', f'*%{dst}') or reg == dst:
        return None
    # Decode the immediate branch from bytes; never infer a target from a comment.
    j = data[ja-start:ja-start+insns[ja][0]]
    if not (len(j)==2 and j[0]==0x77 or len(j)==6 and j[:2]==b'\x0f\x87'):
        return None
    default = ja+len(j)+int.from_bytes(j[1 if len(j)==2 else 2:], 'little', signed=True)
    n = int(c[1],0)+1
    table = lea+insns[lea][0]+int(b[1] or '0',0)
    off = table-start
    if not 1 <= n <= 128 or not 0 <= off <= len(data)-4*n:
        return None
    targets = {table+d for d, in iter_unpack('<i', data[off:off+4*n])}
    if any(t not in insns or table <= t < table+4*n for t in targets | {default}):
        return None
    return targets


def audit(path, objdump, llvm=False):
    blob = path.read_bytes()
    if sha256(blob).hexdigest() != SHA:
        raise ValueError('unexpected executable build')
    off, = unpack_from('<Q', blob, 32)
    n, = unpack_from('<H', blob, 56)
    ph = list(iter_unpack('<II6Q', blob[off:off+56*n]))
    (rx,) = (p for p in ph if p[0]==1 and p[1]&1)
    (eh,) = (p for p in ph if p[0]==0x6474e550)
    base = rx[3]
    code = blob[rx[2]:rx[2]+rx[5]]
    spans, _ = extents(code, base, eh[3]-base, eh[5])
    starts = [a for a,_ in spans]
    groups = defaultdict(dict)
    for pc, _, cases, default in scan(code, base):
        i = bisect_right(starts, pc)-1
        if i < 0:
            raise ValueError('missing FDE')
        a,b = spans[i]
        j = pc+4+(2 if code[pc-base+4]==0x77 else 6)+14
        if not a <= pc < j < b or any(not a <= t < b for t in (*cases,default)):
            raise ValueError('cross-FDE switch')
        groups[a,b][j] = set(cases)
    totals = Counter(unresolved=0, adjacent_candidates=0, candidate_case_edges=0)
    with TemporaryDirectory() as tmp:
        sample, obj = Path(tmp)/'rx', Path(tmp)/'rx.o'
        for (a,b), switches in groups.items():
            data = code[a-base:b-base]
            sample.write_bytes(data)
            if llvm:
                subprocess.run(['objcopy','-I','binary','-O','elf64-x86-64','-B','i386:x86-64',
                                '--rename-section','.data=.text,alloc,load,readonly,code,contents',
                                str(sample),str(obj)],check=True)
                cmd = [objdump,'-d',str(obj)]
            else:
                cmd = [objdump,'-D','-b','binary','-m','i386:x86-64','--insn-width=16',str(sample)]
            insns = decode(subprocess.check_output(cmd,text=True),a)
            seen, unknown, _ = walk(data,a,insns,switches)
            pcs = sorted(insns)
            totals['unresolved'] += len(unknown)
            for pc in unknown:
                i = bisect_right(pcs,pc)-1
                if i < 5 or any(p not in seen for p in pcs[i-5:i]):
                    continue
                targets = candidate(data,a,insns,pcs[i-5:i+1])
                if targets:
                    totals.update(adjacent_candidates=1,candidate_case_edges=len(targets))
    return dict(totals)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot',type=Path)
    p.add_argument('--objdump',default='objdump')
    p.add_argument('--llvm',action='store_true')
    a = p.parse_args()
    print(json.dumps(audit(a.eboot,a.objdump,a.llvm),sort_keys=True))
