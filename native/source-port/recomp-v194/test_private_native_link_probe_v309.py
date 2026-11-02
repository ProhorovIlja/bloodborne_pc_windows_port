#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V309: synthetic-only private Windows PE linker response validation."""
from pathlib import Path
import tempfile

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
        # Never claim a full PE link if a genuine generated body object
        # is missing or truncated, even though the registration exists.
        (root/'recomp_00001.obj').unlink()
        rejects(lambda:probe.object_response_v309(root,names))
        (root/'recomp_00001.obj').write_bytes(b'not a COFF object')
        rejects(lambda:probe.object_response_v309(root,names))
    print('SHYT_V309_PRIVATE_NATIVE_LLD_LINK_RESPONSE_SYNTHETIC_PASS')

if __name__=='__main__':
    main()
