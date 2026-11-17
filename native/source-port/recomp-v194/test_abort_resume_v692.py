# SPDX-License-Identifier: GPL-2.0-or-later
"""Lift and test nonzero returns-twice edges that directly call PS4 abort."""
import argparse
import resource
from pathlib import Path
import signal
from struct import iter_unpack, unpack_from
import subprocess
from tempfile import TemporaryDirectory

from audit_setjmp_v673 import audit

ABORT = b'L1SBTkC+Cvw#'


def scan(path):
    sites = []
    audit(path, resumes=sites)  # validates build hash and instruction boundaries
    blob = path.read_bytes()
    off, = unpack_from('<Q', blob, 32)
    count, = unpack_from('<H', blob, 56)
    ph = list(iter_unpack('<II6Q', blob[off:off+56*count]))

    def segment(kind):
        p, = (p for p in ph if p[0] == kind)
        return blob[p[2]:p[2]+p[5]]

    rx, = (p for p in ph if p[0] == 1 and p[1] & 1)

    def code(pc, n):
        if not rx[3] <= pc <= rx[3]+rx[5]-n:
            return b''
        i = pc+rx[2]-rx[3]
        return blob[i:i+n]

    tags = dict(iter_unpack('<QQ', segment(2)))
    link = segment(0x61000000)

    def table(a, b):
        i, n = tags[0x61000000+a], tags[0x61000000+b]
        if i+n > len(link):
            raise ValueError('dynamic table outside segment')
        return link[i:i+n]

    strings, syms = table(0x35, 0x37), table(0x39, 0x3f)
    slots = set()
    for slot, info, addend in iter_unpack('<QQq', table(0x29, 0x2d)):
        name, _, _, section = unpack_from('<IBBH', syms, (info>>32)*24)
        if info & 0xffffffff == 7 and not addend and not section and strings.startswith(ABORT, name):
            slots.add(slot)
    rows = []
    for pc, _ in sorted(set(sites)):
        insn = code(pc, 8)
        if not insn.startswith(b'\x85\xc0\x0f\x85'):
            continue
        target = pc+8+unpack_from('<i', insn, 4)[0]
        call = code(target, 5)
        if not call.startswith(b'\xe8'):
            continue
        plt = target+5+unpack_from('<i', call, 1)[0]
        stub = code(plt, 6)
        if stub.startswith(b'\xff\x25') and plt+6+unpack_from('<i', stub, 2)[0] in slots:
            rows.append(pc)
    return rows


def emit(rows):
    lines = ['#include <stdint.h>', '#include <stdlib.h>',
             '/* Nonzero result at an attested site terminates; all else misses. */',
             'int bb_abort_resume(uint64_t pc, uint32_t eax) {',
             '    if (!eax) return 0;', '    switch (pc) {']
    lines += [f'    case {pc:#x}: abort();' for pc in rows]
    return '\n'.join(lines+['    default: return 0;', '    }', '}', ''])


def check(rows, cc):
    if len(rows) != 2 or len(set(rows)) != 2:
        raise ValueError('unexpected number of abort sites')
    harness = '''#include <stdint.h>
#include <stdlib.h>
int bb_abort_resume(uint64_t, uint32_t);
int main(int argc, char **argv) {
    if (argc != 3) return 9;
    return bb_abort_resume(strtoull(argv[1],0,0), (uint32_t)strtoull(argv[2],0,0));
}
'''
    _, hard = resource.getrlimit(resource.RLIMIT_CORE)
    resource.setrlimit(resource.RLIMIT_CORE, (0, hard))
    with TemporaryDirectory(prefix='bb692-') as d:
        tmp = Path(d)
        (tmp/'abort.c').write_text(emit(rows))
        (tmp/'main.c').write_text(harness)
        subprocess.run([cc, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                        'abort.c', 'main.c', '-o', 'test'], cwd=tmp, check=True)
        def run(pc, eax):
            return subprocess.run([tmp/'test', hex(pc), hex(eax)], cwd=tmp, timeout=5).returncode
        for pc in rows:
            for eax in (1, 42, 0x80000000, 0xffffffff):
                if run(pc, eax) != -signal.SIGABRT:
                    raise RuntimeError('verified terminal edge did not abort')
                if run(pc+1, eax) != 0:
                    raise RuntimeError('unknown resume did not miss')
            if run(pc, 0) != 0:
                raise RuntimeError('zero path did not miss')
    print(f'{cc}: 8 SIGABRT exits and 10 negative checks')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('eboot', type=Path)
    p.add_argument('--cc', action='append', default=[])
    p.add_argument('--emit-c', type=Path, help='new private source; never commit output')
    args = p.parse_args()
    rows = scan(args.eboot)
    for cc in args.cc or ['cc']:
        check(rows, cc)
    if args.emit_c:
        with args.emit_c.open('x') as f:
            f.write(emit(rows))
