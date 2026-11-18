# SPDX-License-Identifier: GPL-2.0-or-later
"""Check switch target alignment by linear decoding within each FDE.

A hit does not prove reachability. Embedded data can desynchronize a sweep,
so a miss is a candidate for CFG review, not an AOT coverage failure.
"""
import argparse
from bisect import bisect_right
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

INSN = re.compile(r'^\s*([0-9a-f]+):\s+(?:[0-9a-f]{2}\s+)+\s*(\S+)', re.M)


def audit(path, objdump):
    blob = path.read_bytes()
    if sha256(blob).hexdigest() != SHA:
        raise ValueError('unexpected executable build')
    off, = unpack_from('<Q', blob, 32)
    n, = unpack_from('<H', blob, 56)
    ph = list(iter_unpack('<II6Q', blob[off:off+56*n]))
    (rx,) = (p for p in ph if p[0] == 1 and p[1]&1)
    (eh,) = (p for p in ph if p[0] == 0x6474e550)
    base = rx[3]
    code = blob[rx[2]:rx[2]+rx[5]]
    spans, _ = extents(code,base,eh[3]-base,eh[5])
    starts = [lo for lo,_ in spans]
    if any(hi > lo for (_,hi),(lo,_) in zip(spans,spans[1:])):
        raise ValueError('overlapping FDEs')
    total = dict(tables=0, dispatcher_misses=0, edges=0, target_misses=0, external_edges=0)
    with TemporaryDirectory(prefix='bb713-') as d:
        sample = Path(d)/'code.bin'
        for pc,_,cases,default in scan(code,base):
            i = bisect_right(starts,pc)-1
            if i < 0 or pc >= spans[i][1]:
                raise ValueError('dispatcher outside FDE')
            lo,hi = spans[i]
            sample.write_bytes(code[lo-base:hi-base])
            out = subprocess.check_output([objdump,'-D','-b','binary','-m','i386:x86-64',
                                           '--insn-width=16',str(sample)],text=True)
            decoded = {lo+int(addr,16) for addr,op in INSN.findall(out)
                       if op not in ('(bad)','.byte')}
            if lo not in decoded:
                raise ValueError('no valid FDE entry in disassembly')
            total['tables'] += 1
            total['dispatcher_misses'] += pc not in decoded
            for dst in set((*cases,default)):
                total['edges'] += 1
                if not lo <= dst < hi:
                    total['external_edges'] += 1
                else:
                    total['target_misses'] += dst not in decoded
    return total


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot',type=Path)
    p.add_argument('--objdump',default='objdump')
    a = p.parse_args()
    print(json.dumps(audit(a.eboot,a.objdump),sort_keys=True))
