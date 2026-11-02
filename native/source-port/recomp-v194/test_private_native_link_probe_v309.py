#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V309: synthetic-only private Windows PE linker response validation."""
from pathlib import Path
import os
import struct
import tempfile
from unittest.mock import patch

import private_native_link_probe_v309 as probe
from test_private_coff_validation_v281 import synthetic_amd64_coff

def rejects(callback):
    try:
        callback()
    except ValueError:
        return
    raise AssertionError('unsafe private Windows link plan accepted')

def main():
    with tempfile.TemporaryDirectory() as temporary:
        root=Path(temporary)
        names=['recomp.c','recomp_00000.c','recomp_00001.c']
        for name in names:
            (root/(Path(name).stem+'.obj')).write_bytes(
                synthetic_amd64_coff())
        rsp=probe.object_response_v309(root,names)
        assert '/MACHINE:X64' in rsp
        assert '/DLL' in rsp and '/NOENTRY' in rsp
        assert '/OPT:NOREF' in rsp and '/NODEFAULTLIB' in rsp
        assert 'private-native-link-probe-v309.dll' in rsp
        assert rsp.count('.obj')==3
        assert rsp.count('"')==8  # one DLL path, three objects
        assert rsp.endswith('\n') and len(rsp.splitlines())==10
        plan=root/'private-native-link-probe-v309.rsp'
        probe.save_exclusive_v309(plan,rsp)
        assert plan.read_text()==rsp
        rejects(lambda:probe.save_exclusive_v309(plan,rsp))
        rejects(lambda:probe.object_response_v309(root,names[1:]))
        rejects(lambda:probe.object_response_v309(root,[*names,names[0]]))
        rejects(lambda:probe.object_response_v309(root,['recomp.c']))
        # V312: a linker exit code 0 without a real AMD64 PE DLL
        # is never a successful symbol-closure probe.
        pefile=root/'private-native-link-probe-v309.dll'
        assert probe.guard_private_link_target_v315(root)==pefile
        assert not probe.verify_private_pe_dll_v312(pefile)
        pe=bytearray(1024)
        pe[:2]=b'MZ'
        struct.pack_into('<I',pe,0x3c,0x80)
        pe[0x80:0x84]=b'PE\0\0'
        struct.pack_into('<HHLLLHH',pe,0x84,
                         0x8664,1,0,0,0,0xf0,0x2000)
        struct.pack_into('<H',pe,0x98,0x20b)
        struct.pack_into('<I',pe,0x98+0x20,0x1000)
        struct.pack_into('<I',pe,0x98+0x24,0x200)
        struct.pack_into('<I',pe,0x98+0x38,0x2000)
        struct.pack_into('<I',pe,0x98+0x3c,0x200)
        # One real bounded .text section (image body is synthetic only).
        pe[0x188:0x18d]=b'.text'
        struct.pack_into('<LLLL',pe,0x188+8,
                         0x180,0x1000,0x200,0x200)
        pe[0x200:0x400]=b'\x90'*512
        pefile.write_bytes(pe)
        assert probe.verify_private_pe_dll_v312(pefile)
        rejects(lambda:probe.guard_private_link_target_v315(root))
        # A mere genuine-looking header without backed sections
        # cannot be a successful Windows PE link.
        pefile.write_bytes(pe[:512])
        assert not probe.verify_private_pe_dll_v312(pefile)
        pefile.write_bytes(pe)
        struct.pack_into('<I',pe,0x188+8+12,0x3000)
        pefile.write_bytes(pe)
        assert not probe.verify_private_pe_dll_v312(pefile)
        struct.pack_into('<I',pe,0x188+8+12,0x200)
        pefile.write_bytes(pe)
        assert probe.verify_private_pe_dll_v312(pefile)
        saved=pe[0]
        pe[0]=0
        pefile.write_bytes(pe)
        assert not probe.verify_private_pe_dll_v312(pefile)
        pe[0]=saved
        struct.pack_into('<I',pe,0x98+0x10,0x1000)
        pefile.write_bytes(pe)
        assert not probe.verify_private_pe_dll_v312(pefile)
        struct.pack_into('<I',pe,0x98+0x10,0)
        struct.pack_into('<H',pe,0x84,0x14c)
        pefile.write_bytes(pe)
        assert not probe.verify_private_pe_dll_v312(pefile)
        struct.pack_into('<H',pe,0x84,0x8664)
        struct.pack_into('<H',pe,0x84+18,0x20)
        pefile.write_bytes(pe)
        assert not probe.verify_private_pe_dll_v312(pefile)
        pefile.unlink()
        assert probe.guard_private_link_target_v315(root)==pefile
        if os.name!='nt':
            pefile.symlink_to(plan)
            rejects(lambda:probe.guard_private_link_target_v315(root))
            pefile.unlink()
        # V311: prevent complete synthetic objects and a claimed
        # manifest from becoming a retail game link candidate unless
        # both original preparation AND link inventory verified 1.09.
        with (patch.object(probe.batch,'enumerate_shards',return_value=names),
              patch.object(probe.batch,'verify_original_preparation',
                           return_value=False) as original,
              patch.object(probe.batch,'expected_base',return_value={}),
              patch.object(probe.batch,'manifest_for',return_value={'objects':{}}),
              patch.object(probe.batch,'verify_link_inventory_v275',
                           return_value={
                               'full_coff_set_verified':True,
                               'private_original_109_verified':False,
                           }) as inventory):
            rejects(lambda:probe.prepare_private_link_probe_v309(
                root,root,root,root,0))
            original.return_value=True
            rejects(lambda:probe.prepare_private_link_probe_v309(
                root,root,root,root,0))
            inventory.return_value={
                'full_coff_set_verified':False,
                'private_original_109_verified':True,
            }
            rejects(lambda:probe.prepare_private_link_probe_v309(
                root,root,root,root,0))
            inventory.return_value={
                'full_coff_set_verified':True,
                'private_original_109_verified':True,
            }
            verified,shard_count=probe.prepare_private_link_probe_v309(
                root,root,root,root,0)
            assert verified==rsp and shard_count==len(names)
        # Never claim a full PE link if a genuine generated body object
        # is missing or truncated, even though the registration exists.
        (root/'recomp_00001.obj').unlink()
        rejects(lambda:probe.object_response_v309(root,names))
        (root/'recomp_00001.obj').write_bytes(b'not a COFF object')
        rejects(lambda:probe.object_response_v309(root,names))
    print('SHYT_V309_PRIVATE_NATIVE_LLD_LINK_RESPONSE_SYNTHETIC_PASS')

if __name__=='__main__':
    main()
