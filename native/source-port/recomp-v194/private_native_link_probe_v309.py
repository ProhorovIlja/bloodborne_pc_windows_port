#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V309: actual PRIVATE, bounded Windows PE linker diagnostic for full AOT COFF.

No original-game source, symbols, objects or linker logs go to GitHub.
Requires the complete original registry + all recomp_XXXXX.c objects,
pinned V204 source hashes and V217 compiler/SDK/object SHA-256. It uses
lld-link to probe the current native Win64 symbol closure as a DLL with
NOENTRY. This is NOT Bloodborne.exe or a game/runtime implementation.
Unresolved original imports are an expected *failure*, never success.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import sys

import private_coff_batch_runner_v273 as batch
import compile_private_win64_coff_v217 as coff
from bounded_private_subprocess_v210 import run_stage

MAX_LINK_BUDGET=1800
MAX_RESPONSE_BYTES=128*1024

def object_response_v309(output:Path,names:list[str])->str:
    """Generate only expected full source names; never use manifest paths."""
    if (not 2<=len(names)<=batch.MAX_SHARDS or
            'recomp.c' not in names or len(set(names))!=len(names) or
            any(not coff.VALID.fullmatch(n) for n in names)):
        raise ValueError('incomplete or unsafe native AOT registration')
    root=coff.private(output).resolve(strict=True)
    if not root.is_dir() or root.is_symlink():
        raise ValueError('missing private Win64 COFF directory')
    dll=root/'private-native-link-probe-v309.dll'
    paths=[root/(Path(n).stem+'.obj') for n in sorted(names)]
    if any(not p.is_file() or p.is_symlink() or not coff.coff_ok(p)
           for p in paths):
        raise ValueError('missing or malformed full original COFF')
    if any('"' in str(p) or '\\n' in str(p) or '\\r' in str(p)
           for p in [dll,*paths]):
        raise ValueError('unsafe linker response file quoting')
    # /OPT:NOREF prevents a no-entry DLL from dead-stripping original
    # functions and falsely reporting a "successful" empty PE link.
    lines=['/MACHINE:X64','/DLL','/NOENTRY','/NODEFAULTLIB',
           '/OPT:NOREF','/OPT:NOICF',f'/OUT:"{dll}"']
    lines.extend(f'"{p}"' for p in paths)
    text='\\n'.join(lines)+'\\n'
    if len(text.encode('utf-8'))>MAX_RESPONSE_BYTES:
        raise ValueError('unsafe linker response size')
    return text

def prepare_private_link_probe_v309(
    generated:Path,upstream:Path,sdk:Path,output:Path,opt:int)->tuple[str,int]:
    generated=coff.private(generated)
    output=coff.private(output)
    names=batch.enumerate_shards(generated)
    # No link plan is emitted on incomplete, stale or corrupted COFF.
    batch.verify_original_preparation(generated,names)
    base=batch.expected_base(generated,upstream,sdk,output,opt)
    manifest=batch.manifest_for(output)
    check=batch.verify_link_inventory_v275(
        generated,output,names,manifest,base)
    if not check['full_coff_set_verified']:
        raise ValueError('private original AOT COFF set is incomplete')
    response=object_response_v309(output,names)
    return response,len(names)

def save_exclusive_v309(path:Path,content:str)->None:
    target=coff.private(path)
    if target.is_symlink() or target.exists() or not target.parent.is_dir():
        raise ValueError('link probe response already exists or unsafe')
    fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w',encoding='utf-8',newline='\\n') as f:
        f.write(content)

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument('--generated-dir',required=True,type=Path)
    p.add_argument('--upstream',required=True,type=Path)
    p.add_argument('--sdk',required=True,type=Path)
    p.add_argument('--output-dir',required=True,type=Path)
    p.add_argument('--opt',type=int,choices=(0,1,2),default=0)
    p.add_argument('--budget-seconds',type=int,default=180)
    p.add_argument('--attempt',action='store_true',
                   help='run bounded original COFF lld-link /DLL /NOENTRY probe')
    args=p.parse_args()
    try:
        if not 10<=args.budget_seconds<=MAX_LINK_BUDGET:
            raise ValueError('invalid bounded link time')
        response,count=prepare_private_link_probe_v309(
            args.generated_dir,args.upstream,args.sdk,args.output_dir,args.opt)
        output=coff.private(args.output_dir).resolve(strict=True)
        target=output/'private-native-link-probe-v309.rsp'
        save_exclusive_v309(target,response)
        print('SHYT_V309_VERIFIED_PRIVATE_FULL_COFF_LINK_PLAN objects='+str(count))
        if args.attempt:
            linker=shutil.which('lld-link')
            if not linker:
                raise ValueError('lld-link missing on owner machine')
            try:
                run_stage([linker,'@'+str(target)],'link_probe_v309',
                          output/'link_probe_logs',timeout=args.budget_seconds)
            except RuntimeError:
                print('SHYT_V309_PRIVATE_LINK_UNRESOLVED_OR_FAILED '
                      'inspect PRIVATE bounded logs')
                return 2
            # A PE DLL symbol closure probe is NOT native game boot.
            print('SHYT_V309_PRIVATE_PE_DLL_PROBE_LINKED '
                  'native_game_executable=false game_boot=false')
        else:
            print('SHYT_V309_PLAN_ONLY private_PE_link_complete=false')
    except (OSError,ValueError,RuntimeError,TimeoutError) as e:
        print('SHYT_V309_LINK_BLOCKED:'+type(e).__name__,file=sys.stderr)
        return 2
    return 0

if __name__=='__main__':
    raise SystemExit(main())
