# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline exact-form decoder: AVX RIP-relative 16-byte copies followed by ret."""
import struct

LOAD = bytes.fromhex('c5f82805')
STORE = bytes.fromhex('c5f82905')
LIMIT = 1 << 64


def decode(entry, code, source_span, destination_span, relocations_overlap):
    """Caller provides a bounded instruction window and attested range checks.

    The span predicates check file-backed immutable source and writable
    destination respectively; the relocation predicate checks interval
    overlap, not merely equality with the relocation's starting address.
    Return None unless every instruction and operand is within the subset.
    """
    if not 0 <= entry <= LIMIT-65:
        return None
    plan = []
    for p in (0, 16, 32, 48, 64):
        if code[p:p+1] == b'\xc3':
            return tuple(plan) if len(plan) in (1, 3, 4) else None
        if p == 64 or len(code) < p+16 or code[p:p+4] != LOAD or code[p+8:p+12] != STORE:
            return None
        s = entry+p+8+struct.unpack_from('<i', code, p+4)[0]
        d = entry+p+16+struct.unpack_from('<i', code, p+12)[0]
        if (not 0 <= s <= LIMIT-16 or not 0 <= d <= LIMIT-16 or s%16 or d%16
                or s < entry+65 and entry < s+16
                or not source_span(s, 16) or not destination_span(d, 16)
                or relocations_overlap(s, 16) or relocations_overlap(d, 16)):
            return None
        plan.append((s, d))
    return None


def self_test():
    entry = 0x2000

    def fixture(n):
        return b''.join(LOAD+struct.pack('<i', 0x1000-entry-8-16*i)
                        +STORE+struct.pack('<i', 0x3000-entry-16)
                        for i in range(n))+b'\xc3'

    src = lambda a, w: a == 0x1000 and w == 16
    dst = lambda a, w: 0x3000 <= a and a+w <= 0x3040
    clean = lambda a, w: False
    for n in (1, 3, 4):
        code = fixture(n)
        assert decode(entry,code,src,dst,clean) == tuple((0x1000, 0x3000+16*i) for i in range(n))
        assert decode(entry,code[:-1],src,dst,clean) is None
        assert decode(entry,code,src,dst,lambda a,w: a==0x3000) is None
        assert decode(entry,code[:8]+b'\x00'+code[9:],src,dst,clean) is None
        assert decode(entry,code,src,lambda a,w:False,clean) is None
    for n in (0, 2, 5):
        assert decode(entry,fixture(n),src,dst,clean) is None
    print('NATIVE_V470_COPY_DECODER_PASS')


if __name__ == '__main__':
    self_test()
