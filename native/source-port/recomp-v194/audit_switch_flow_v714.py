# SPDX-License-Identifier: GPL-2.0-or-later
"""Compare intra-FDE flow with and without V711 switch edges.

Linear decode supplies instruction boundaries. Calls are assumed to return;
other indirect jumps, exceptions and out-of-range edges are not followed.
This is a static reachability estimate, not runtime or donor coverage.
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

from audit_switch_owners_v712 import extents
from audit_switch_v711 import scan
from resume_switch_v697 import SHA

LINE = re.compile(r'^\s*([0-9a-f]+):\s+((?:[0-9a-f]{2}[ \t]+)+)(\S+)([^\n]*)$', re.M)


def decode(text, base):
    return {base+int(addr,16):(len(raw.split()), op, operand.strip())
            for addr,raw,op,operand in LINE.findall(text)
            if op not in ('(bad)', '.byte', '<unknown>')}


def walk(code, start, insns, switches):
    todo, seen, indirect, misses = [start], set(), set(), set()
    while todo:
        pc = todo.pop()
        if not start <= pc < start+len(code) or pc in seen:
            continue
        if pc not in insns:
            misses.add(pc)
            continue
        seen.add(pc)
        size, op, operand = insns[pc]
        nxt = pc+size
        if pc in switches:
            if code[pc-start:nxt-start] != b'\xff\xe0':
                raise ValueError('switch not at expected decoded jump')
            todo.extend(switches[pc])
        elif op.startswith(('ret','iret','lret','ud','int','hlt','sysret')):
            continue
        elif op.startswith(('j','loop')) or op == 'bnd' and operand.startswith('jmp'):
            m = re.match(r'^(?:jmpq?\s+)?0x([0-9a-f]+)(?:\s|$)',operand)
            if m:
                todo.append(start+int(m[1],16))
            else:
                indirect.add(pc)
            if not op.startswith(('jmp','ljmp','bnd')):
                todo.append(nxt)
        else:
            todo.append(nxt)
    return seen, indirect, misses


def audit(path, objdump):
    blob = path.read_bytes()
    if sha256(blob).hexdigest() != SHA:
        raise ValueError('unexpected executable build')
    off, = unpack_from('<Q',blob,32)
    n, = unpack_from('<H',blob,56)
    ph = list(iter_unpack('<II6Q',blob[off:off+56*n]))
    (rx,) = (p for p in ph if p[0]==1 and p[1]&1)
    (eh,) = (p for p in ph if p[0]==0x6474e550)
    base = rx[3]
    code = blob[rx[2]:rx[2]+rx[5]]
    ranges,_ = extents(code,base,eh[3]-base,eh[5])
    starts = [a for a,_ in ranges]
    if any(b>c for (_,b),(c,_) in zip(ranges,ranges[1:])):
        raise ValueError('overlapping FDEs')
    groups = defaultdict(dict)
    for pc,_,cases,default in scan(code,base):
        i = bisect_right(starts,pc)-1
        if i < 0:
            raise ValueError('dispatcher outside FDEs')
        a,b = ranges[i]
        jump = pc+4+(2 if code[pc-base+4]==0x77 else 6)+14
        if not a <= pc < jump < b or any(not a<=d<b for d in (*cases,default)):
            raise ValueError('cross-FDE switch')
        groups[i][jump] = set(cases)
    totals = Counter(fdes=0,tables=0,direct_jumps_reached=0,expanded_jumps_reached=0,
                     case_edges=0,direct_case_targets=0,expanded_case_targets=0,
                     other_indirect_jumps=0,undecoded_targets=0)
    with TemporaryDirectory(prefix='bb714-') as d:
        sample = Path(d)/'code.bin'
        for i,switches in groups.items():
            a,b = ranges[i]
            data = code[a-base:b-base]
            sample.write_bytes(data)
            listing = subprocess.check_output([objdump,'-D','-b','binary','-m','i386:x86-64',
                                               '--insn-width=16',str(sample)],text=True)
            insns = decode(listing,a)
            if a not in insns or any(j not in insns for j in switches):
                raise ValueError('missing entry or switch jump boundary')
            direct,_,_ = walk(data,a,insns,{})
            expanded,unknown,misses = walk(data,a,insns,switches)
            totals.update(fdes=1,tables=len(switches),
                          direct_jumps_reached=len(switches.keys() & direct),
                          expanded_jumps_reached=len(switches.keys() & expanded),
                          case_edges=sum(map(len,switches.values())),
                          direct_case_targets=sum(len(s & direct) for s in switches.values()),
                          expanded_case_targets=sum(len(s & expanded) for s in switches.values()),
                          other_indirect_jumps=len(unknown),undecoded_targets=len(misses))
    return totals


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot',type=Path)
    p.add_argument('--objdump',default='objdump')
    a = p.parse_args()
    print(json.dumps(audit(a.eboot,a.objdump),sort_keys=True))
