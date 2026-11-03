#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V287 synthetic-only AMD64 COFF external symbols and link closure."""
from __future__ import annotations
from pathlib import Path
import struct
import tempfile

from private_coff_symbol_closure_v287 import (
    symbols_in_object,verify_external_symbol_closure
)

def object_blob(symbols:list[tuple[bytes,int,int,int,int]])->bytes:
    # COFF: machine AMD64, one .text section, raw data absent,
    # string table after 18-byte symbol entries. No executable game bytes.
    strings=bytearray(b'\0\0\0\0')
    table=bytearray()
    for name,value,section,storage,aux in symbols:
        if len(name)<=8:
            ref=name.ljust(8,b'\0')
        else:
            ref=b'\0'*4+struct.pack('<I',len(strings))
            strings.extend(name+b'\0')
        table.extend(struct.pack('<8sLhHBB',
                                 ref,value,section,0x20,storage,aux))
    struct.pack_into('<I',strings,0,len(strings))
    header=struct.pack('<HHLLLHH',0x8664,1,0,60,len(symbols),0,0)
    section_blob=struct.pack('<8sLLLLLLHHL',
                             b'.text\0\0\0',0,0,0,0,0,0,0,0,0)
    return header+section_blob+table+strings

def refused(work):
    try:work()
    except ValueError:return
    raise AssertionError('invalid original-game COFF accepted')

def main()->None:
    with tempfile.TemporaryDirectory() as t:
        root=Path(t)
        a=root/'a.obj';b=root/'b.obj'
        a.write_bytes(object_blob([
            (b'function',0,1,2,0),
            (b'long_name_external',0,0,2,0),
            (b'crt_call',0,0,2,0),
            (b'local',0,1,3,0),
        ]))
        b.write_bytes(object_blob([
            (b'long_name_external',0,1,2,0),
            (b'function',0,0,2,0),
        ]))
        defs,needs,total,weak=symbols_in_object(a)
        assert defs=={b'function'}
        assert needs=={b'long_name_external',b'crt_call'}
        assert total==4 and weak==0
        closed=verify_external_symbol_closure([a,b])
        assert closed['verified_amd64_coff_objects']==2
        assert closed['external_definitions']==2
        assert closed['external_references']==3
        assert closed['external_references_unresolved_in_game_objects']==1
        assert closed['duplicate_external_names_across_objects']==0
        # V328: the missing CRT import blocks only object A; B's
        # externally referenced symbol is resolved by object A.
        assert closed['unresolved_reference_sites_across_objects']==1
        assert closed['object_modules_blocked_by_host_imports']==1
        assert closed['object_modules_self_contained_against_external_imports']==1
        assert closed['max_unresolved_imports_in_one_object']==1
        assert closed['unresolved_symbols_needed_by_exactly_one_object']==1
        # V290: A -> B and B -> A form one strongly connected
        # native link component; CRT remains an unresolved external.
        assert closed['direct_object_dependency_edges']==2
        assert closed['strongly_connected_object_components']==1
        assert closed['cyclic_object_components']==1
        assert closed['largest_cyclic_or_single_component']==2
        assert not closed['native_pe_link_complete']
        assert not closed['guest_runtime_removed']
        assert not closed['windows_crt_import_resolution_done']
        refused(lambda:verify_external_symbol_closure([]))
        refused(lambda:verify_external_symbol_closure([a]*513))
        original=a.read_bytes()
        a.write_bytes(original[:50])
        refused(lambda:symbols_in_object(a))
        a.write_bytes(original)
        # Replace the first external name with a bad offset to a
        # different string table. Never follow unbounded pointers.
        corrupt=bytearray(original)
        corrupt[60:64]=b'\0'*4
        struct.pack_into('<I',corrupt,64,0xffffffff)
        a.write_bytes(corrupt)
        refused(lambda:symbols_in_object(a))
        a.write_bytes(original)
        # Auxiliary symbol count may not consume past the table end.
        corrupt=bytearray(original)
        corrupt[60+18*3+17]=1
        a.write_bytes(corrupt)
        refused(lambda:symbols_in_object(a))
        a.write_bytes(original)
        assert verify_external_symbol_closure([a,b])['coff_symbols_inspected']==6
        # A third independent object forms its own SCC, while the two
        # mutually dependent modules remain one group.
        c=root/'c.obj'
        c.write_bytes(object_blob([(b'solo',0,1,2,0)]))
        report=verify_external_symbol_closure([a,b,c])
        assert report['strongly_connected_object_components']==2
        assert report['cyclic_object_components']==1
        assert report['largest_cyclic_or_single_component']==2
        assert report['direct_object_dependency_edges']==2
        assert report['object_modules_blocked_by_host_imports']==1
        # A fourth module needs the same CRT symbol PLUS a new
        # unrelated host import: count unique names vs reference sites.
        d=root/'d.obj'
        d.write_bytes(object_blob([
            (b'crt_call',0,0,2,0),
            (b'gpu_shim',0,0,2,0),
        ]))
        wider=verify_external_symbol_closure([a,b,c,d])
        assert wider['external_references_unresolved_in_game_objects']==2
        assert wider['unresolved_reference_sites_across_objects']==3
        assert wider['object_modules_blocked_by_host_imports']==2
        assert wider['object_modules_self_contained_against_external_imports']==2
        assert wider['max_unresolved_imports_in_one_object']==2
        assert wider['unresolved_symbols_needed_by_exactly_one_object']==1
    print('SHYT_V287_V290_SYNTHETIC_WIN64_COFF_SYMBOL_DEPENDENCY_SCC_PASS')

if __name__=='__main__':
    main()
