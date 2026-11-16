# SPDX-License-Identifier: GPL-2.0-or-later
"""Recognize one bounded x86-64 rel32 dispatch form offline; no semantic lifting."""
import struct


def recover(image, base, entry, blocks):
    # cmp rax, imm8; ja default; lea rdx, [rip+disp32];
    # movsxd rcx, [rdx+rax*4]; add rcx, rdx; jmp rcx.
    n = 22
    off = entry - base
    if not 0 <= base < (1 << 64) or len(image) > (1 << 64) - base or not 0 <= off <= len(image) - n:
        raise ValueError('dispatch outside image')
    code = image[off:off+n]
    if (code[:3] != b'\x48\x83\xf8' or code[3] > 127 or code[4] != 0x77
            or code[6:9] != b'\x48\x8d\x15' or code[13:] != b'\x48\x63\x0c\x82\x48\x01\xd1\xff\xe1'):
        raise ValueError('unsupported dispatch')
    default = entry + 6 + int.from_bytes(code[5:6], 'little', signed=True)
    table = entry + 13 + struct.unpack_from('<i', code, 9)[0]
    start = table - base
    end = start + (code[3]+1)*4
    if not 0 <= start < end <= len(image) or (start < off+n and off < end):
        raise ValueError('invalid table extent')
    targets = tuple(table+d for (d,) in struct.iter_unpack('<i', image[start:end]))
    for addr in (*targets, default):
        pos = addr-base
        if not 0 <= pos < len(image) or addr not in blocks or off <= pos < off+n or start <= pos < end:
            raise ValueError('unproven block destination')
    return table, default, targets
