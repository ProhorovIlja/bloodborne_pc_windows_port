# SPDX-License-Identifier: GPL-2.0-or-later
"""Compile both cleanup stages and test the combined no-fallback contract."""
import ctypes as c
from pathlib import Path
from random import Random
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory

from audit_cleanup_resume_v688 import emit, scan
from cleanup_tail_v689 import decode, emit as emit_tail

U = c.c_uint64
P = c.c_void_p
CALL = c.CFUNCTYPE(None, P)
RESOLVE = c.CFUNCTYPE(P, P, U, c.c_size_t)


class State(c.Structure):
    _fields_ = [('pc', U), ('nv', U*6), ('used', c.c_size_t), ('al', c.c_uint8)]


def run(path, cc):
    blob, rows = scan(path)
    tails = [(dst, r14, decode(blob, dst, emb, r14)) for _, dst, emb, r14, *_ in rows]
    if not rows:
        raise ValueError('no cleanup paths')
    trace = []

    @CALL
    def callback(ptr):
        trace.append(c.string_at(ptr, 40))
        c.memset(ptr+0x24, 255, 4)

    @RESOLVE
    def resolve(ctx, token, slot):
        return c.cast(callback, P).value if (token, slot) == (17, 0x50) else None

    bridge = '''#include "cleanup_chain_v690.h"
int replay(struct bb_cleanup_state_v690 *s, uint32_t v, void *p, size_t size,
           bb_cleanup_resolve_v687 r, uint64_t guard, const uint64_t *f,
           size_t words, size_t bp) {
    return bb_cleanup_chain_v690(s,v,p,size,0,r,guard,f,words,bp);
}
'''
    with TemporaryDirectory(prefix='bb690-') as d:
        tmp = Path(d)
        paths = [tmp / name for name in ('prefix.c', 'tail.c', 'bridge.c')]
        for f, source in zip(paths, (emit(rows), emit_tail(tails), bridge)):
            f.write_text(source)
        so = tmp/'fixture.so'
        subprocess.run([cc, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror', '-shared',
                        '-fPIC', '-I', str(Path(__file__).resolve().parent), *paths,
                        '-o', so], check=True)
        replay = c.CDLL(str(so)).replay
        replay.argtypes = (c.POINTER(State), c.c_uint32, P, c.c_size_t, RESOLVE, U,
                           c.POINTER(U), c.c_size_t, c.c_size_t)
        rng = Random(690)
        success = fatal = rejected = 0
        for (pc, _, embedded, _, *_), (_, _, (skip, pops, fail, _)) in zip(rows, tails):
            offset = 8 if embedded else 0
            n = skip+len(pops)+1
            for trial in range(512):
                trace.clear()
                data = bytearray(rng.randbytes(0x411))
                token = 17 if trial & 1 else 0
                struct.pack_into('<Q', data, offset+8, token)
                obj = c.create_string_buffer(bytes(data))
                frame = (U*8)(*(rng.getrandbits(64) for _ in range(8)))
                guard = frame[0] ^ ((trial >> 1) & 1)
                state = State(pc, (U*6)(1,2,3,4,5,6), 99, 97)
                snapshot = bytes(state)
                args = (c.byref(state), 42, obj, len(data), resolve, guard, frame)
                assert replay(*args, n-1, 3) == 0
                assert replay(*args[:3], 0, *args[4:], 8, 3) == 0
                assert replay(args[0], 0, *args[2:], 8, 3) == 0
                rejected += 3
                if fail is not None:
                    assert replay(*args, 8, 2) == 0
                    rejected += 1
                struct.pack_into('<Q', obj, offset+8, 19)
                bad = obj.raw
                assert replay(*args, 8, 3) == 0 and obj.raw == bad
                rejected += 1
                struct.pack_into('<Q', obj, offset+8, token)
                assert bytes(state) == snapshot and obj.raw[:-1] == data and not trace
                status = replay(*args, 8, 3)
                nv = [1,2,3,4,5,6]
                if fail is not None and guard != frame[0]:
                    assert status == 2 and state.pc == fail and state.used == 0
                    fatal += 1
                else:
                    assert status == 1 and state.pc == frame[n-1] and state.used == n
                    for slot, reg in enumerate(pops, skip):
                        nv[reg] = frame[slot]
                    success += 1
                assert list(state.nv) == nv and state.al == 0
                assert trace == ([bytes(data[offset:offset+40])] if token else [])
                data[offset+8:offset+16] = bytes(8)
                data[offset+0x24:offset+0x28] = bytes(4)
                if embedded:
                    data[0x410] = (data[0x410] & 0xfc) | 2
                assert obj.raw[:-1] == data
    print(f'{cc}: {success} returns, {fatal} fatal edges, {rejected} rejected inputs')


if __name__ == '__main__':
    run(Path(sys.argv[1]), sys.argv[2])
