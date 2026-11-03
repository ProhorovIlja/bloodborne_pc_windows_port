#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V317: real clang + lld-link PE32+ smoke test using synthetic-only COFF.

This tests the exact V309 response-file linker invocation on both Windows
and Linux runners. No original Bloodborne assets, symbols or file paths
are used; a linked synthetic DLL is not the native Bloodborne game.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile

import private_native_link_probe_v309 as probe

def run(argv:list[str])->None:
    outcome=subprocess.run(argv,stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT,timeout=45,
                           text=True,errors='replace')
    if outcome.returncode:
        # Both commands only receive fixed synthetic fixture names.
        raise AssertionError(
            'fixture linker/compiler failed: '+
            outcome.stdout[-1500:])

def main()->None:
    compiler=shutil.which('clang')
    linker=shutil.which('lld-link')
    if not compiler or not linker:
        raise AssertionError('V317 requires real clang and lld-link')
    with tempfile.TemporaryDirectory(prefix='shyt-private-pe-fixture-') as folder:
        root=Path(folder)
        names=['recomp.c','recomp_00000.c']
        for file,body in [
            ('recomp.c','int bb_recomp_body(void); '
             'int bb_recomp_init(void) {return bb_recomp_body()+17;}\n'),
            ('recomp_00000.c','int bb_recomp_body(void) {return 29;}\n'),
        ]:
            source=root/file
            source.write_text(body,encoding='ascii')
            run([compiler,'--target=x86_64-pc-windows-msvc',
                 '-O0','-ffreestanding','-fno-stack-protector',
                 '-c',str(source),'-o',
                 str(root/(source.stem+'.obj'))])
        # V319: force the synthetic generated registry to import
        # a function defined ONLY in the separate gameplay object.
        # This catches linker false passes from empty no-entry DLLs.
        response=probe.object_response_v309(root,names)
        response+='/INCLUDE:bb_recomp_init\n'
        target=probe.guard_private_link_target_v315(root)
        rsp=root/'synthetic_link.rsp'
        probe.save_exclusive_v309(rsp,response)
        run([linker,'@'+str(rsp)])
        assert target.is_file()
        assert probe.verify_private_pe_dll_v312(target)
        # V322: the private symbol accountant must agree with the
        # REAL successful LLVM linker: no unresolved original externs.
        full=probe.private_aggregate_import_audit_v322(root,names)
        assert full['objects']==2 and full['unresolved']==0
        assert full['dependency_edges']>=1
        # With the second COFF genuinely missing, lld-link MUST
        # report unresolved bb_recomp_body, not "success".
        negative=root/'negative-link.rsp'
        bad_output=root/'negative-link.dll'
        # V319: Windows TempDirectory paths may be canonicalized
        # differently by Path.resolve() inside the response builder.
        # Identify only the expected exact source stem, never by
        # reconstructing a platform-dependent absolute path.
        original_lines=response.splitlines()
        body_lines=[line for line in original_lines if
                    line.startswith('"') and
                    line.lower().endswith('recomp_00000.obj"')]
        assert len(body_lines)==1
        missing_body='\n'.join(
            '/OUT:"'+str(bad_output)+'"' if line.startswith('/OUT:')
            else line for line in original_lines
            if line not in body_lines)+'\n'
        assert 'recomp_00000.obj' not in missing_body
        probe.save_exclusive_v309(negative,missing_body)
        bad=subprocess.run([linker,'@'+str(negative)],
                           stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                           timeout=45,text=True,errors='replace')
        assert bad.returncode!=0, 'missing dependency linked successfully'
        assert not probe.verify_private_pe_dll_v312(bad_output)
        # The same incomplete dependency is detectable BEFORE invoking
        # lld-link, without printing any private original symbol names.
        source=root/'recomp_00000.c'
        original_object=(root/'recomp_00000.obj').read_bytes()
        source.write_text('int unrelated_synthetic(void){return 3;}\n',
                          encoding='ascii')
        run([compiler,'--target=x86_64-pc-windows-msvc',
             '-O0','-ffreestanding','-fno-stack-protector',
             '-c',str(source),'-o',str(root/'recomp_00000.obj')])
        incomplete=probe.private_aggregate_import_audit_v322(root,names)
        assert incomplete['unresolved']>=1
        (root/'recomp_00000.obj').write_bytes(original_object)
        assert probe.private_aggregate_import_audit_v322(root,names)['unresolved']==0
        rejects=False
        try:
            probe.guard_private_link_target_v315(root)
        except ValueError:
            rejects=True
        assert rejects, 'stale PE output allowed'
    print('SHYT_V319_REAL_SYNTHETIC_CROSS_COFF_LINK_AND_UNRESOLVED_IMPORT_DENIAL_PASS')

if __name__=='__main__':
    main()
