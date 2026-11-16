# SPDX-License-Identifier: GPL-2.0-or-later
"""Replay an isolated V468 pack with the V463 host library, no ELF input."""
import ctypes as c
import os
import pathlib
import struct
import sys

import startup_data_v468 as p


def replay(rows, lib):
    fn = c.CDLL(lib).native_guarded_leaf_v463
    fn.argtypes = [c.POINTER(c.c_ubyte), c.c_size_t, c.c_size_t, c.c_uint64]
    fn.restype = c.c_int
    cold = 0
    state = {}
    for _, obj, table, initial in rows:
        a = state.get(obj)
        if a is None:
            a = state[obj] = (c.c_ubyte*18).from_buffer_copy(b'\xa5'+initial+b'\x5a')
        before = bytes(a)[1:17]
        active = before[8] == 0
        cold += active
        want = b'\xa5'+(struct.pack('<QQ', table, 1) if active else before)+b'\x5a'
        if fn(a, 18, 1, table) != int(active) or bytes(a) != want:
            raise ValueError('native mutation mismatch')
        if fn(a, 18, 1, table) != 0 or bytes(a) != want:
            raise ValueError('native reentry mismatch')
    return len(rows), len(state), cold, 2*len(rows)


def main():
    if len(sys.argv) != 4:
        raise SystemExit('usage: replay_startup_v468.py PACK PINNED_DIGEST_FILE HOST_LIBRARY')
    name, digest, lib = (os.path.realpath(x) for x in sys.argv[1:])
    allowed = {name, digest, lib}

    def audit(event, args):
        # Extra test guard; use OS isolation if the original must be inaccessible.
        if event in ('open', 'ctypes.dlopen') and (
            not isinstance(args[0], (str, bytes)) or os.fsdecode(os.path.realpath(args[0])) not in allowed
        ):
            raise PermissionError('input outside test allowlist')

    sys.addaudithook(audit)
    with pathlib.Path(name).open('rb') as f:
        data = f.read(p.HEADER.size+p.MAX_ROWS*p.ROW.size+1)
    with pathlib.Path(digest).open('r', encoding='ascii') as f:
        pin = f.read(66).strip()
    print('NATIVE_V468_REPLAY_PASS', *replay(p.unpack(data, pin), lib))


if __name__ == '__main__':
    main()
