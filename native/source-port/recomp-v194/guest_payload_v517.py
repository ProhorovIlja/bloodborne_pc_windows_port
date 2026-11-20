# SPDX-License-Identifier: GPL-2.0-or-later
"""Private reference windows for detecting unmodified chunks of guest RX."""
import mmap
import stat
import struct

EH = struct.Struct('<16sHHIQQQIHHHHHH')
PH = struct.Struct('<II6Q')
WINDOW = 4096


def anchors(path):
    if not stat.S_ISREG(path.lstat().st_mode):
        raise ValueError('reference must be a regular PS4 ELF')
    with path.open('rb') as f:
        h = EH.unpack(f.read(EH.size))
        f.seek(0, 2)
        n = f.tell()
        if (h[0][:7] != b'\x7fELF\x02\x01\x01' or h[1] not in (0xfe00,0xfe01,0xfe04,0xfe10,0xfe18)
                or h[2] != 62 or h[9] != PH.size or not 1 <= h[10] <= 256
                or not EH.size <= h[5] <= n-PH.size*h[10]):
            raise ValueError('invalid PS4 ELF reference')
        f.seek(h[5])
        rx = [p for p in (PH.unpack(f.read(PH.size)) for _ in range(h[10])) if p[:2] == (1,5)]
        if len(rx) != 1 or not 3*WINDOW <= rx[0][5] <= rx[0][6] or rx[0][2] > n-rx[0][5]:
            raise ValueError('unsupported reference RX extent')
        start, size = rx[0][2], rx[0][5]
        result = set()
        for delta in (size//8, size//2, 7*size//8):
            f.seek(start+min(delta,size-WINDOW))
            chunk = f.read(WINDOW)
            if len(chunk) != WINDOW or len(set(chunk)) < 32:
                raise ValueError('unsuitable reference window')
            result.add(chunk)
        if len(result) != 3:
            raise ValueError('duplicate reference windows')
        return tuple(sorted(result))


def contains(stream, signatures):
    if not signatures or stream.seek(0, 2) < WINDOW:
        return False
    with mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as view:
        return any(view.find(window) >= 0 for window in signatures)
