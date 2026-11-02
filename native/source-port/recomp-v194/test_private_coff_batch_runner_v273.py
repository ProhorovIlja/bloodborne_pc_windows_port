#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V273: synthetic ONLY, no original CUSA03173 code or COFF objects."""
from __future__ import annotations
import argparse
from pathlib import Path
import json
import struct
import tempfile

import private_coff_batch_runner_v273 as batch
import compile_private_win64_coff_v217 as coff
from test_private_coff_validation_v281 import synthetic_amd64_coff

def rejected(fn):
    try: fn()
    except ValueError: return
    raise AssertionError("unsafe private batch input was accepted")

def run()->None:
    with tempfile.TemporaryDirectory() as work:
        root=Path(work)
        source=root/'source'
        dest=root/'coff'
        source.mkdir()
        dest.mkdir()
        # An owner may have 384 actual recomp shards; the test only
        # emits FOUR harmless synthetic filenames and a fake object.
        for i in range(4):
            (source/f'recomp_{i:05x}.c').write_bytes(
                b'/* synthetic never derived from game */\n')
        names=batch.enumerate_shards(source)
        # V274: a filename alone is not proof that its C came from a
        # complete original-game scan. Only a matching pinned V204
        # manifest and exact scanner index unlock private scheduling.
        rejected(lambda:batch.verify_original_preparation(source,names))
        scanner=root/'scan'
        scanner.mkdir()
        (scanner/'functions.tsv').write_text('synthetic-only\\n')
        provenance={
            'format':'SHYT_PRIVATE_FULL_IMAGE_V204',
            'upstream':coff.PIN,
            'functions_scanned':4,
            'version_109_verified':False,
            'scanner_index_sha256':coff.digest(scanner/'functions.tsv'),
            'c_hashes':{name:coff.digest(source/name) for name in names}
        }
        provenance_file=root/'full-original-preparation.json'
        provenance_file.write_text(json.dumps(provenance),encoding='utf-8')
        assert not batch.verify_original_preparation(source,names)
        (source/names[0]).write_text('changed synthetic source')
        rejected(lambda:batch.verify_original_preparation(source,names))
        (source/names[0]).write_bytes(b'/* synthetic never derived from game */\n')
        assert not batch.verify_original_preparation(source,names)
        (scanner/'functions.tsv').write_text('changed scanner')
        rejected(lambda:batch.verify_original_preparation(source,names))
        (scanner/'functions.tsv').write_text('synthetic-only\\n')
        assert not batch.verify_original_preparation(source,names)
        assert len(names)==4
        assert names==sorted(names)
        (source/'unrelated.txt').write_text('safe')
        assert batch.enumerate_shards(source)==names
        expected={'upstream':'synthetic','opt':0}
        first=source/names[0]
        obj=dest/(first.stem+'.obj')
        obj.write_bytes(synthetic_amd64_coff())
        spec={**expected,'source_sha256':coff.digest(first)}
        manifest={'format':'SHYT_PRIVATE_ORIGINAL_COFF_V217',
                  'objects':{names[0]:{
                      'spec':spec,'object_sha256':coff.digest(obj)}}}
        state=dest/'private_coff_manifest_v217.json'
        state.write_text(json.dumps(manifest),encoding='utf-8')
        assert batch.manifest_for(dest)==manifest
        pending=batch.pending_shards(source,dest,names,manifest,expected)
        assert pending==names[1:]
        assert batch.fingerprint_matches(first,obj,manifest['objects'][names[0]],spec)
        # Any changed source, object or changed SDK/compiler provenance
        # invalidates the cached COFF, even if its filename is unchanged.
        first.write_text('/* NEW synthetic source */\n',encoding='utf-8')
        assert len(batch.pending_shards(source,dest,names,manifest,expected))==4
        first.write_bytes(b'/* synthetic never derived from game */\n')
        obj.write_bytes(struct.pack('<HH',0x14c,2)+bytes(16))
        assert len(batch.pending_shards(source,dest,names,manifest,expected))==4
        obj.write_bytes(synthetic_amd64_coff())
        assert len(batch.pending_shards(source,dest,names,manifest,
                                        {**expected,'opt':1}))==4
        state.write_text('{"format":"WRONG","objects":{}}',encoding='utf-8')
        rejected(lambda:batch.manifest_for(dest))
        state.unlink()
        assert not batch.manifest_for(dest)['objects']
        # V275: do not claim a link-ready private game when even ONE
        # Win64 COFF object is missing or stale. All test source and
        # object bytes below are synthetic and disposable.
        incomplete=batch.verify_link_inventory_v275(
            source,dest,names,manifest,expected)
        assert incomplete['expected_original_shards']==4
        assert incomplete['verified_private_win64_coff']==1
        assert incomplete['missing_or_stale_coff']==3
        assert not incomplete['full_coff_set_verified']
        assert not incomplete['native_pe_linked']
        assert not incomplete['game_boot_proven']
        for name in names[1:]:
            origin=source/name
            obj_file=dest/(origin.stem+'.obj')
            obj_file.write_bytes(synthetic_amd64_coff())
            manifest['objects'][name]={
                'spec':{**expected,'source_sha256':coff.digest(origin)},
                'object_sha256':coff.digest(obj_file)}
        complete=batch.verify_link_inventory_v275(
            source,dest,names,manifest,expected)
        assert complete['verified_private_win64_coff']==4
        assert complete['missing_or_stale_coff']==0
        assert complete['full_coff_set_verified']
        assert not complete['private_original_109_verified']
        assert not complete['native_pe_linked']
        assert not complete['runtime_guest_callbacks_eliminated']
        assert not complete['game_boot_proven']
        # V287: the optional prelink stage must inspect ONLY a complete,
        # unchanged, SHA-verified owner COFF set; it exposes aggregate
        # symbol counts, never private exported function names.
        opts=argparse.Namespace(verify_link_inventory=False,
                                verify_symbol_closure=True)
        aggregate={}
        batch.attach_link_preflight_v287(
            aggregate,opts,source,dest,names,manifest,expected)
        assert aggregate['link_inventory']['full_coff_set_verified']
        report=aggregate['symbol_closure']
        assert report['external_definitions']==1
        assert report['duplicate_external_names_across_objects']==3
        assert report['external_references_unresolved_in_game_objects']==0
        assert not report['native_pe_link_complete']
        changed_obj=dest/(Path(names[-1]).stem+'.obj')
        changed_obj.write_bytes(b'changed invalid COFF')
        drift=batch.verify_link_inventory_v275(
            source,dest,names,manifest,expected)
        assert drift['missing_or_stale_coff']==1
        assert not drift['full_coff_set_verified']
        partial={}
        batch.attach_link_preflight_v287(
            partial,opts,source,dest,names,manifest,expected)
        assert partial['symbol_closure']['status']=='blocked_incomplete_coff_set'
        # Do not permit private game metadata to be silently relabelled
        # as verified retail 1.09 without real owner-produced evidence.
        # This synthetic fixture has the original V204 false flag.
        # No unsafe out-of-tree C shard or potential path traversal.
        (source/'recomp_abcde.c').write_bytes(b'')
        rejected(lambda:batch.enumerate_shards(source))
        (source/'recomp_abcde.c').unlink()
        (source/'recomp_fffff.c').mkdir()
        assert len(batch.enumerate_shards(source))==4
        # A matching symlink must not be silently followed.
        linked=source/'recomp_fffaa.c'
        try:
            linked.symlink_to(first)
        except (OSError,NotImplementedError):
            pass
        else:
            rejected(lambda:batch.enumerate_shards(source))
            linked.unlink()
        # Refuse putting owner-only code under a checkout.
        (source/'.git').mkdir()
        rejected(lambda:batch.enumerate_shards(source))
    print('SHYT_V273_PRIVATE_BOUNDED_COFF_PLANNING_SECURITY_PASS')

if __name__=='__main__':
    run()
