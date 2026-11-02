#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V281 synthetic COFF structure tests. Does NOT use private game bytes."""
from __future__ import annotations
from pathlib import Path
import struct
import tempfile
import compile_private_win64_coff_v217 as build

def synthetic_amd64_coff()->bytes:
    # Exactly one section, one formally valid COFF external symbol,
    # and a four-byte empty string table. No real game instructions.
    header=struct.pack('<HHLLLHH',0x8664,1,0,60,1,0,0)
    section=struct.pack('<8sLLLLLLHHL',
        b'.text\0\0\0',0,0,0,0,0,0,0,0,0)
    symbol=struct.pack('<8sLhHBB',b'fixture\0',0,1,0x20,2,0)
    strings=struct.pack('<L',4)
    synthetic=header+section+symbol+strings
    assert len(synthetic)==82
    return synthetic

def main()->None:
    original=synthetic_amd64_coff()
    with tempfile.TemporaryDirectory() as folder:
        file=Path(folder)/'synthetic.obj'
        def check(data:bytes,accepted:bool):
            file.write_bytes(data)
            assert build.coff_ok(file)==accepted
        check(original,True)
        # Old V217 accepted ANY 20-byte prefix with machine and sections.
        check(original[:20],False)
        check(original[:60],False)
        check(original[:-1],False)
        def changed(offset:int,payload:bytes)->bytes:
            return original[:offset]+payload+original[offset+len(payload):]
        check(changed(0,struct.pack('<H',0x14c)),False) # x86 32-bit
        check(changed(0,b'MZ'),False)                 # not a linked PE
        check(changed(2,struct.pack('<H',32767)),False)
        check(changed(16,struct.pack('<H',24)),False)  # PE optional header
        check(changed(8,struct.pack('<L',0)),False)    # no COFF symbol table
        check(changed(8,struct.pack('<L',0xffffffff)),False)
        check(changed(12,struct.pack('<L',0xffffffff)),False)
        check(changed(20+16,struct.pack('<L',32)),False) # raw size without pointer
        check(changed(20+20,struct.pack('<L',25)),True) # zero raw size: pointer unused
        check(changed(20+16,struct.pack('<L',5)),False) # unbacked section data
        # Data or relocations must not overlap the symbol table at 60.
        overlapping=changed(20+16,struct.pack('<L',5))
        overlapping=overlapping[:20+20]+struct.pack('<L',58)+overlapping[20+24:]
        check(overlapping,False)
        check(changed(20+24,struct.pack('<L',1000)),True) # no relocs => pointer ignored
        check(changed(20+24,struct.pack('<L',1000))[:20+32]+
              struct.pack('<H',1)+original[20+34:],False)
        check(changed(78,struct.pack('<L',0)),False)
        check(changed(78,struct.pack('<L',0xffffffff)),False)
        # V293: exact native AMD64 COFF relocation structure.
        # The old checker counted bytes but did not validate the COFF
        # relocation's symbol ordinal. Broken objects looked cached.
        def relocated(rows:bytes,nreloc:int,overflow:bool=False)->bytes:
            head=bytearray(original[:60])
            struct.pack_into('<L',head,8,60+len(rows)) # symbol table moved
            struct.pack_into('<L',head,20+24,60)       # relocation pointer
            struct.pack_into('<H',head,20+32,nreloc)
            struct.pack_into('<L',head,20+36,0x01000000 if overflow else 0)
            return bytes(head)+rows+original[60:]
        valid=struct.pack('<LLH',0,0,4) # REL32 to first external
        check(relocated(valid,1),True)
        check(relocated(struct.pack('<LLH',0,1,4),1),False)
        check(relocated(struct.pack('<LLH',0,0,17),1),False)
        check(relocated(valid[:9],1),False)
        check(relocated(valid,1,True),False) # contradictory overflow flag
        check(relocated(valid,0xffff,False),False)
        # Legitimate huge AOT modules may exceed 65535 relocations.
        # First overflow record declares the total incl. dummy entry.
        large=struct.pack('<LLH',65536,0,0)+valid*65535
        check(relocated(large,0xffff,True),True)
        invalid=bytearray(large)
        struct.pack_into('<L',invalid,0,65535) # bad dummy overflow count
        check(relocated(bytes(invalid),0xffff,True),False)
        invalid=bytearray(large)
        struct.pack_into('<L',invalid,10+4,1) # bad indexed original symbol
        check(relocated(bytes(invalid),0xffff,True),False)
        check(original+b'extra',True) # padding/alignment allowed
        check(b'',False)
        # Public checkout has no access to private COFF inventory.
        file.write_bytes(original)
        assert build.coff_ok(file)
    print('SHYT_V281_SYNTHETIC_AMD64_COFF_STRUCTURE_SECURITY_PASS')

if __name__=='__main__':
    main()
