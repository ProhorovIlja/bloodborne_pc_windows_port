# SPDX-License-Identifier: GPL-2.0-or-later
"""Data-only pack for independently verified V463 leaves, not an ELF loader."""
import hashlib
import struct

HEADER = struct.Struct('<8sI')
ROW = struct.Struct('<IQQ16s')  # ordinal, object ID, vtable ID, initial object/guard
MAGIC = b'BBL468\x00\x01'
MAX_ROWS = 4096


def check(rows):
    if not 1 <= len(rows) <= MAX_ROWS:
        raise ValueError('invalid row count')
    last = 0
    objects = {}
    for ordinal, obj, table, initial in rows:
        if not last < ordinal <= 65536 or len(initial) != 16:
            raise ValueError('invalid ordinal or state')
        if not 0 < obj <= 2**64-16 or obj % 8 or not 0 < table <= 2**64-8 or table % 8:
            raise ValueError('invalid guest address')
        if objects.setdefault(obj, (table, initial)) != (table, initial):
            raise ValueError('conflicting alias')
        last = ordinal
    spans = sorted(objects)
    if any(a+16 > b for a, b in zip(spans, spans[1:])):
        raise ValueError('overlapping objects')


def pack(rows):
    check(rows)
    return HEADER.pack(MAGIC, len(rows)) + b''.join(ROW.pack(*row) for row in rows)


def unpack(data, expected_sha256):
    # Pin the digest from the offline build; do not trust a digest in the pack.
    if not HEADER.size <= len(data) <= HEADER.size+MAX_ROWS*ROW.size:
        raise ValueError('invalid pack size')
    magic, count = HEADER.unpack_from(data)
    if magic != MAGIC or len(data) != HEADER.size+count*ROW.size:
        raise ValueError('invalid pack header')
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise ValueError('wrong pack identity')
    rows = list(ROW.iter_unpack(memoryview(data)[HEADER.size:]))
    check(rows)
    return rows


def self_test():
    rows = [(1, 32, 128, bytes(16)), (3, 48, 128, bytes([255])*16), (4, 32, 128, bytes(16))]
    data = pack(rows)
    digest = hashlib.sha256(data).hexdigest()
    assert unpack(data, digest) == rows
    for bad, sha in [(data[:-1], digest), (data+b'x', digest), (data, '0'*64),
                     (b'\x7fELF'+data[4:], digest), (data[:-1]+b'\x01', digest)]:
        try:
            unpack(bad, sha)
        except ValueError:
            continue
        raise AssertionError('bad pack accepted')
    for bad in [[], rows[::-1], rows[:1]*2, rows[:1]+[(2, 40, 128, bytes(16))],
                rows+[(5, 32, 136, bytes(16))], [(1, 32, 129, bytes(16))], [(1, 2**64-8, 128, bytes(16))]]:
        try:
            pack(bad)
        except ValueError:
            continue
        raise AssertionError('bad rows accepted')
    print('NATIVE_V468_DATA_PACK_PASS')


if __name__ == '__main__':
    self_test()
