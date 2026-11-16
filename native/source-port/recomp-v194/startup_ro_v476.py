# SPDX-License-Identifier: GPL-2.0-or-later
"""Pack only caller-attested read-only operands, never a complete segment."""
from bisect import bisect_left

MAX_BYTES = 4 << 20
MAX_ROWS = 65536


def prepare(image, source, requests, code, relocations):
    """source=(guest base, file offset, file extent) of verified source window.

    requests=(guest address, length), code=half-open decoded instruction
    ranges, relocations=8-byte destination slots. Callers must independently
    prove requests are data; a hole in the instruction index is not proof.
    """
    base, off, size = source
    if not (0 <= base < 1 << 64 and 0 < size < (1 << 64)-base
            and 0 <= off <= len(image)-size):
        raise ValueError('invalid source window')
    requests = sorted(set(requests))
    if not 0 < len(requests) <= MAX_ROWS:
        raise ValueError('invalid request count')
    deny = sorted([*code, *((a, a+8) for a in relocations)])
    starts, ends = [], []
    for a, b in deny:
        if not 0 <= a < b <= 1 << 64:
            raise ValueError('invalid excluded span')
        starts.append(a)
        ends.append(max(b, ends[-1] if ends else 0))
    spans = []
    for a, n in requests:
        b = a+n
        if not (base <= a < b <= base+size and n <= MAX_BYTES):
            raise ValueError('invalid request span')
        i = bisect_left(starts, b)-1
        if i >= 0 and ends[i] > a:
            raise ValueError('request intersects code or relocation')
        if spans and a <= spans[-1][1]:
            spans[-1] = spans[-1][0], max(b, spans[-1][1])
        else:
            spans.append((a, b))
    if sum(b-a for a, b in spans) > MAX_BYTES:
        raise ValueError('pool exceeds budget')
    rows, pool = [], bytearray()
    for a, b in spans:
        rows.append((a, len(pool), b-a))
        pool.extend(image[off+a-base:off+b-base])
    return rows, bytes(pool)
