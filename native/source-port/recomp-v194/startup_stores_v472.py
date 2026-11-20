# SPDX-License-Identifier: GPL-2.0-or-later
"""Offline exact forms: vector copies plus scalar stores or RAX materialization."""
import struct


def decode(entry, code, readable, writable, relocated):
    def rip(p, disp, length):
        return entry + p + length + struct.unpack_from('<i', code, p+disp)[0]

    def vector(p):
        if len(code) < p+8 or code[p:p+4] != b'\xc5\xf8\x28\x05':
            raise ValueError
        return rip(p, 4, 8)

    def lea(p):
        if len(code) < p+7 or code[p:p+3] != b'\x48\x8d\x05':
            raise ValueError
        return rip(p, 3, 7)

    def scalar(p):
        if code[p:p+3] == b'\x66\xc7\x05' and len(code) >= p+9:
            return (rip(p,3,9), 2, int.from_bytes(code[p+7:p+9],'little')), p+9
        if code[p:p+2] == b'\xc7\x05' and len(code) >= p+10:
            return (rip(p,2,10), 4, int.from_bytes(code[p+6:p+10],'little')), p+10
        raise ValueError

    try:
        rax = None
        first = vector(0)
        if code[15:20] == b'\xc5\xf8\x29\x00\xc3':
            rax = lea(8)
            ops, end = [(rax,16,first)], 19
        else:
            ops = []
            for p in (0,16,32):
                s = vector(p)
                if len(code)<p+16 or code[p+8:p+12]!=b'\xc5\xf8\x29\x05':
                    return None
                ops.append((rip(p+8,4,8),16,s))
            if code[48:52] == b'\xc5\xf8\x28\x05':
                s = vector(48)
                for p in (56,67):
                    d = lea(p)
                    if code[p+7:p+11] != b'\xc5\xf8\x29\x00':
                        return None
                    ops.append((d,16,s))
                rax = lea(78)
                if len(code)<92 or code[85:87]!=b'\xc7\x00':
                    return None
                ops.append((rax,4,int.from_bytes(code[87:91],'little')))
                end = 91
            else:
                tail, end = scalar(48)
                ops.append(tail)
        if code[end:end+1]!=b'\xc3':
            return None
        for d,w,x in ops:
            if not 0 <= d <= 2**64-w or (w==16 and d%16) or not writable(d,w) or relocated(d,w):
                return None
            if w==16 and (not 0<=x<=2**64-16 or x%16 or not readable(x,16)
                          or relocated(x,16) or x<entry+end+1 and entry<x+16):
                return None
        return end+1, tuple(ops), rax
    except (ValueError, struct.error):
        return None


def self_test():
    a = 0x1000
    code = bytes.fromhex('c5f82805')+struct.pack('<i',0x2000-a-8)
    code += bytes.fromhex('488d05')+struct.pack('<i',0x3000-a-15)+bytes.fromhex('c5f82900c3')
    rd = lambda p,n: (p,n)==(0x2000,16)
    wr = lambda p,n: (p,n)==(0x3000,16)
    no = lambda p,n: False
    assert decode(a,code,rd,wr,no)==(20,((0x3000,16,0x2000),),0x3000)
    assert decode(a,code[:-1],rd,wr,no) is None
    assert decode(a,code,rd,wr,lambda p,n: p==0x3000) is None
    assert decode(a,code,no,wr,no) is None
    assert decode(a,code[:15]+b'\x90'+code[16:],rd,wr,no) is None
    print('V472_OFFLINE_DECODER_PASS')


if __name__ == '__main__':
    self_test()
