#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V377 public synthetic corrupted PE/ELF static preflight, no private bytes."""
import struct
from native_binary_closure_gate_v377 import inspect_bytes,NotNative

def synthetic_pe(name=b'KERNEL32.dll\0'):
    b=bytearray(1024)
    b[:2]=b'MZ'; struct.pack_into('<I',b,0x3c,0x80)
    b[0x80:0x84]=b'PE\0\0'
    struct.pack_into('<HHLLLHH',b,0x84,0x8664,1,0,0,0,240,2)
    o=0x98
    struct.pack_into('<H',b,o,0x20b)
    struct.pack_into('<I',b,o+0x10,0x1000)
    struct.pack_into('<I',b,o+0x38,0x2000)
    struct.pack_into('<I',b,o+0x3c,0x200)
    struct.pack_into('<I',b,o+0x6c,16)
    struct.pack_into('<II',b,o+0x78,0x1100,40)
    s=0x188
    b[s:s+8]=b'.text\0\0\0'
    struct.pack_into('<IIII',b,s+8,0x200,0x1000,0x200,0x200)
    struct.pack_into('<I',b,s+36,0x60000020)
    b[0x200]=0xC3
    struct.pack_into('<IIIII',b,0x300,0,0,0,0x1130,0)
    b[0x330:0x330+len(name)]=name
    return bytes(b)

def synthetic_elf(name=b'libc.so.6\0'):
    b=bytearray(1024)
    b[:7]=b'\x7fELF\x02\x01\x01'
    struct.pack_into('<HHI',b,16,3,62,1)
    struct.pack_into('<QQ',b,24,0x400100,64)
    struct.pack_into('<HHH',b,52,64,56,2)
    struct.pack_into('<IIQQQQQQ',b,64,1,5,0,0x400000,0x400000,len(b),len(b),4096)
    struct.pack_into('<IIQQQQQQ',b,120,2,6,0x180,0x400180,0x400180,64,64,8)
    struct.pack_into('<qQ',b,0x180,1,1)
    struct.pack_into('<qQ',b,0x190,5,0x400230)
    struct.pack_into('<qQ',b,0x1a0,10,len(name)+1)
    struct.pack_into('<qQ',b,0x1b0,0,0)
    b[0x230]=0
    b[0x231:0x231+len(name)]=name
    return bytes(b)

def rejected(data,target):
    try:inspect_bytes(data,target)
    except NotNative:return
    raise AssertionError('malformed or unapproved binary promoted')

def main():
    win=synthetic_pe()
    assert inspect_bytes(win,'windows')['imports_reviewed']==1
    assert not inspect_bytes(win,'windows')['runtime_no_guest_proven']
    for invalid in [b'MZ'+win[2:200],synthetic_pe(b'shadps4.dll\0'),
                    synthetic_pe(b'unknown.dll\0'),synthetic_pe(b'libc.so.6/../x\0')]:
        rejected(invalid,'windows')
    w=bytearray(win)
    struct.pack_into('<I',w,0x98+0x10,0x5000)
    rejected(bytes(w),'windows')
    w=bytearray(win)
    struct.pack_into('<I',w,0x300+12,0xffffffff)
    rejected(bytes(w),'windows')
    linux=synthetic_elf()
    assert inspect_bytes(linux,'linux')['imports_reviewed']==1
    assert not inspect_bytes(linux,'linux')['whole_game_boot_proven']
    rejected(synthetic_elf(b'libshadps4.so\0'),'linux')
    rejected(synthetic_elf(b'libunreviewed.so\0'),'linux')
    rejected(synthetic_elf(b'libc.so.6/../../evil\0'),'linux')
    e=bytearray(linux)
    struct.pack_into('<H',e,18,0x28)
    rejected(bytes(e),'linux')
    e=bytearray(linux)
    struct.pack_into('<qQ',e,0x1a0,10,1)
    rejected(bytes(e),'linux')
    e=bytearray(linux)
    struct.pack_into('<qQ',e,0x1b0,29,2) # rpath is not an attested native dependency
    rejected(bytes(e),'linux')
    print('NATIVE_V377_SYNTHETIC_PE_ELF_IMPORT_FAIL_CLOSED_TESTS_PASS')
if __name__=='__main__':main()
