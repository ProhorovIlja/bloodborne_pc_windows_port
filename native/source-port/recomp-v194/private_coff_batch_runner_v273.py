#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V273: bounded resumable private original-game Windows COFF batch runner.

Only the owner runs this LOCALLY next to a generated original 1.09 AOT
source tree. No retail bytes/addresses/object names in public CI/output.
This orchestrates the existing V217 checked SHA + Win64 COFF compiler,
NOT a PS4 runtime, an EBOOT launcher, or a playable native Bloodborne.

Each call limits work by both number of batches and a wall-clock budget.
Every object cache hit is revalidated by V217 against source, compiler,
full public headers and the private portable Win64 SDK provenance.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import time

import compile_private_win64_coff_v217 as coff

MAX_SHARDS=512
MAX_BATCHES=16
MAX_MANIFEST=2*1024*1024

def enumerate_shards(generated:Path)->list[str]:
    path=coff.private(generated)
    if not path.is_dir() or path.is_symlink():
        raise ValueError("unsafe private generated source tree")
    names=[]
    # Nonrecursive by design: only produced flat recomp_XXXXX.c objects
    # may be used by the pinned V217 compiler; never search arbitrary dirs.
    for child in path.iterdir():
        if child.is_symlink():
            raise ValueError("linked private source files are forbidden")
        if child.is_file() and coff.VALID.fullmatch(child.name):
            if not (1<=child.stat().st_size<=coff.MAX_SOURCE_BYTES):
                raise ValueError("invalid private generated source size")
            names.append(child.name)
    if not 1<=len(names)<=MAX_SHARDS:
        raise ValueError("unexpected original-game C shard count")
    return sorted(names)

def manifest_for(output:Path)->dict:
    path=coff.private(output)/'private_coff_manifest_v217.json'
    if not path.exists():
        return {'format':'SHYT_PRIVATE_ORIGINAL_COFF_V217','objects':{}}
    if path.is_symlink() or path.stat().st_size>MAX_MANIFEST:
        raise ValueError("unsafe private COFF checkpoint")
    manifest=json.loads(path.read_text(encoding='utf-8'))
    if manifest.get('format')!='SHYT_PRIVATE_ORIGINAL_COFF_V217' or not isinstance(
            manifest.get('objects'),dict):
        raise ValueError("corrupt private COFF checkpoint")
    return manifest

def fingerprint_matches(source:Path,dest:Path,old:dict|None,
                        expected:dict)->bool:
    # V273 does not trust checkpoint object names/paths, and accepts a
    # prior object only after V217 verifies the full input fingerprint.
    return bool(
        isinstance(old,dict) and old.get('spec')==expected and
        coff.coff_ok(dest) and coff.digest(dest)==old.get('object_sha256')
    )

def expected_base(generated:Path,upstream:Path,sdk:Path,output:Path,opt:int)->dict:
    import subprocess
    import verify_coff_dependencies_v219 as deps
    header,sdk_hash,compiler=coff.prerequisites(
        generated,upstream,sdk,output)
    del header
    return {
        'upstream':coff.PIN,
        'sdk_manifest_sha256':sdk_hash,
        'rc_header_sha256':coff.digest(upstream/'src/recomp/rc.h'),
        'opt':opt,'target':'x86_64-w64-windows-gnu',
        'clang_version':subprocess.check_output(
            [compiler,'--version'],text=True,timeout=10).splitlines()[0],
        **deps.input_fingerprint(upstream,sdk,compiler),
    }

def pending_shards(generated:Path,output:Path,names:list[str],
                   manifest:dict,base:dict)->list[str]:
    objects=manifest['objects']
    remaining=[]
    for name in names:
        # The scan is bounded by MAX_SHARDS, source files by 64MiB each,
        # and validates stale cached objects against *every* toolchain input.
        source=generated/name
        dest=output/(source.stem+'.obj')
        expected={**base,'source_sha256':coff.digest(source)}
        if not fingerprint_matches(source,dest,objects.get(name),expected):
            remaining.append(name)
    return remaining

def run(args:argparse.Namespace)->dict:
    if not 0<=args.opt<=2 or not 1<=args.max_batches<=MAX_BATCHES or not (
            45<=args.budget_seconds<=3600):
        raise ValueError("unbounded COFF scheduling request")
    generated=coff.private(args.generated_dir)
    output=coff.private(args.output_dir)
    upstream=args.upstream.resolve(strict=True)
    sdk=args.sdk.resolve(strict=True)
    if not output.parent.is_dir():
        raise ValueError("missing private output parent")
    names=enumerate_shards(generated)
    # Preserve the exact provenance of the current private build. If any
    # include, compiler binary, SDK metadata or original shard changed,
    # V217 will rebuild the affected object instead of reusing stale COFF.
    base=expected_base(generated,upstream,sdk,output,args.opt)
    manifest=manifest_for(output)
    pending=pending_shards(generated,output,names,manifest,base)
    result={
        'total_original_generated_shards':len(names),
        'verified_cached_shards':len(names)-len(pending),
        'pending_before':len(pending),
        'newly_compiled':0,'batches_completed':0,
        'still_pending':len(pending),
        'private_game_boot_proven':False,
        'native_runtime_guest_free_proven':False,
    }
    if args.preview or not pending:
        return result
    started=time.monotonic()
    for i in range(0,len(pending),4):
        if result['batches_completed']>=args.max_batches:
            break
        remaining=args.budget_seconds-(time.monotonic()-started)
        if remaining<45:
            break
        batch=pending[i:i+4]
        report=coff.compile_sources(
            generated,upstream,sdk,output,batch,
            args.opt,min(600,max(45,int(remaining))))
        result['batches_completed']+=1
        result['newly_compiled']+=report['new_coff_objects']
        if report['deferred_files']:
            # No false progress: V217 preserves all completed checkpoints,
            # next run will re-evaluate this unfinished batch from source.
            break
    # Do not count objects merely because a prior compiler exited 0.
    # Verify all private SHA-256 checkpoints, including those in this run.
    check=pending_shards(generated,output,names,manifest_for(output),base)
    result['still_pending']=len(check)
    result['verified_cached_shards']=len(names)-len(check)
    return result

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument('--generated-dir',type=Path,required=True)
    p.add_argument('--upstream',type=Path,required=True)
    p.add_argument('--sdk',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True)
    p.add_argument('--opt',type=int,choices=(0,1,2),default=0)
    p.add_argument('--max-batches',type=int,default=8)
    p.add_argument('--budget-seconds',type=int,default=180)
    p.add_argument('--preview',action='store_true')
    args=p.parse_args()
    try:
        report=run(args)
        # Aggregate only, never private names, addresses, hashes or paths.
        print('SHYT_V273_BOUNDED_PRIVATE_COFF_BATCH_STATUS')
        print(json.dumps(report,sort_keys=True,separators=(',',':')))
    except (OSError,ValueError,RuntimeError,TimeoutError,
            json.JSONDecodeError) as exc:
        print('SHYT_V273_PRIVATE_COFF_BLOCKED:'+type(exc).__name__,
              file=sys.stderr)
        raise SystemExit(2)

if __name__=='__main__':
    main()
