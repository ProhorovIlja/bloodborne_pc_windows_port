# SPDX-License-Identifier: GPL-2.0-or-later
"""Find direct returns-twice call sites for an offline AOT migration.

No claim about indirect callers. Linear decoding from the closest preceding
unwind start is a cross-check, not a proof of ownership or reachability.
"""
import argparse
from bisect import bisect_right
import json
from pathlib import Path
import re
from struct import iter_unpack, unpack_from
import subprocess
from tempfile import TemporaryDirectory

from ps4_ctor_order_v567 import inspect

# libkernel setjmp NID, also identified by the Android Rebuild Tool.
NID = b'gNQ1V2vfXDE'


def audit(path, objdump='objdump', *, resumes=None):
    blob = path.read_bytes()
    order, unwind = inspect(blob)
    phoff, = unpack_from('<Q', blob, 32)
    count, = unpack_from('<H', blob, 56)
    ph = list(iter_unpack('<II6Q', blob[phoff:phoff+56*count]))
    def segment(kind):
        (p,) = (p for p in ph if p[0] == kind)
        return blob[p[2]:p[2]+p[5]]
    tags = dict(iter_unpack('<QQ', segment(2)))
    link = segment(0x61000000)
    def table(a,b):
        off,n = tags[0x61000000+a],tags[0x61000000+b]
        if off+n > len(link):
            raise ValueError('invalid dynamic table span')
        return link[off:off+n]
    strings,symbols = table(0x35,0x37),table(0x39,0x3f)
    slots = set()
    for slot,info,addend in iter_unpack('<QQq',table(0x29,0x2d)):
        name,_,_,section = unpack_from('<IBBH',symbols,(info>>32)*24)
        if info&0xffffffff==7 and not addend and not section and strings.startswith(NID+b'#',name):
            slots.add(slot)
    if len(slots)!=1:
        raise ValueError('expected one setjmp PLT relocation')
    (rx,) = (p for p in ph if p[0]==1 and p[1]&1)
    offset,base,span = rx[2],rx[3],rx[5]
    code = blob[offset:offset+span]
    (slot,) = slots
    rip = lambda i,n: base+i+n+unpack_from('<i',code,i+n-4)[0]
    stubs = {base+m.start() for m in re.finditer(rb'\xff\x25',code)
             if m.start()+6<=span and rip(m.start(),6)==slot}
    if len(stubs)!=1:
        raise ValueError('expected one setjmp PLT stub')
    checks = {}
    starts = sorted(unwind | set(order) | {0x20,0xa0})
    roots = set(order) | {0x20,0xa0}
    for m in re.finditer(rb'[\xe8\xe9]|\xff\x15',code):
        i = m.start()
        n = 5 if len(m[0])==1 else 6
        if i+n>span or rip(i,n) not in (stubs if n==5 else slots):
            continue
        va=base+i
        j=bisect_right(starts,va)-1
        if j<0:
            checks[va] = (None,False,False,False)
            continue
        start=starts[j]
        # Disassemble only the bounded slice, not the complete ELF on each call.
        with TemporaryDirectory(prefix='bb-setjmp-') as tmp:
            sample = Path(tmp) / 'code.bin'
            sample.write_bytes(code[start-base:i+n])
            out = subprocess.check_output([objdump, '-D', '-b', 'binary', '-m',
                     'i386:x86-64', '--insn-width=16', str(sample)], text=True)
        op = 'call' if code[i] != 0xe9 else 'jmp'
        matched = bool(re.search(rf'^\s*{va-start:x}:\s+(?:[0-9a-f]{{2}}\s+){{{n}}}{op}\b', out, re.M))
        checks[va]=(start,matched,start in roots,op=="call")
        if resumes is not None and matched and op == 'call':
            resumes.append((va+n, i+offset+n))
    return dict(plt_slots=len(slots),plt_stubs=len(stubs), candidates=len(checks),
                decoded_calls=sum(v[1] and v[3] for v in checks.values()),
                decoded_tail_jumps=sum(v[1] and not v[3] for v in checks.values()),
                nearest_entries=len({v[0] for v in checks.values() if v[1]}),
                nearest_startup_entries=len({v[0] for v in checks.values() if v[1] and v[2]}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('eboot',type=Path)
    parser.add_argument('--objdump',default='objdump')
    args=parser.parse_args()
    print(json.dumps(audit(args.eboot,args.objdump),sort_keys=True))
