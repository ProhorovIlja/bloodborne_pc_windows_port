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
        check(changed(60+16,struct.pack('<L',32)),False) # corrupt .text raw-size
        check(changed(60+20,struct.pack('<L',25)),False) # offset without bytes not meaningful
        check(changed(20+16,struct.pack('<L',5)),False) # nonempty raw section missing pointer
        check(changed(20+16,struct.pack('<L',4))[:20+20]+b'',False) if False else None
        check(changed(20+16,struct.pack('<L',5)),False)
        check(changed(20+24,struct.pack('<L',1000)),True) # no relocs => pointer ignored
        check(changed(20+24,struct.pack('<L',1000))[:20+32]+
              struct.pack('<H',1)+original[20+34:],False)
        check(changed(78,struct.pack('<L',0)),False)
        check(changed(78,struct.pack('<L',0xffffffff)),False)
        check(original+b'extra',True) # padding/alignment allowed
        check(b'',False)
        # Public checkout has no access to private COFF inventory.
        file.write_bytes(original)
        assert build.coff_ok(file)
    print('SHYT_V281_SYNTHETIC_AMD64_COFF_STRUCTURE_SECURITY_PASS')

if __name__=='__main__':
    main()
