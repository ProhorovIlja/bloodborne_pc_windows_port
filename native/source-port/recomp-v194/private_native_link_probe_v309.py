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
import struct
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
    if any('"' in str(p) or '\n' in str(p) or '\r' in str(p)
           for p in [dll,*paths]):
        raise ValueError('unsafe linker response file quoting')
    # /OPT:NOREF prevents a no-entry DLL from dead-stripping original
    # functions and falsely reporting a "successful" empty PE link.
    lines=['/MACHINE:X64','/DLL','/NOENTRY','/NODEFAULTLIB',
           '/OPT:NOREF','/OPT:NOICF',f'/OUT:"{dll}"']
    lines.extend(f'"{p}"' for p in paths)
    text='\n'.join(lines)+'\n'
    if len(text.encode('utf-8'))>MAX_RESPONSE_BYTES:
        raise ValueError('unsafe linker response size')
    return text

def prepare_private_link_probe_v309(
    generated:Path,upstream:Path,sdk:Path,output:Path,opt:int)->tuple[str,int]:
    generated=coff.private(generated)
    output=coff.private(output)
    names=batch.enumerate_shards(generated)
    # No link plan is emitted on incomplete, stale or corrupted COFF.
    # V311: complete != authentic. A V204 manifest explicitly
    # declaring version_109_verified=False must never be elevated into
    # a link candidate, even with perfectly hashed synthetic objects.
    if batch.verify_original_preparation(generated,names) is not True:
        raise ValueError('original retail 1.09 image not verified')
    base=batch.expected_base(generated,upstream,sdk,output,opt)
    manifest=batch.manifest_for(output)
    check=batch.verify_link_inventory_v275(
        generated,output,names,manifest,base)
    if not check['full_coff_set_verified'] or not (
            check['private_original_109_verified'] is True):
        raise ValueError('incomplete or unauthenticated original game COFF')
    response=object_response_v309(output,names)
    return response,len(names)

def verify_private_pe_dll_v312(path:Path)->bool:
    """Validate linker-produced real AMD64 PE DLL, not just exit code.

    A successful fake/no-op linker could otherwise report "PE linked"
    without emitting ANY file. This is only a structural PE inspection;
    it does NOT establish original-game boot or working native imports.
    """
    file=coff.private(path)
    if (file.is_symlink() or not file.is_file() or
            not 512<=file.stat().st_size<=8*1024**3):
        return False
    size=file.stat().st_size
    try:
        with file.open('rb') as stream:
            dos=stream.read(64)
            if len(dos)!=64 or dos[:2]!=b'MZ':
                return False
            at=struct.unpack_from('<I',dos,0x3c)[0]
            if at<64 or at>4096 or at+24+2>size:
                return False
            stream.seek(at)
            header=stream.read(24)
            if len(header)!=24 or header[:4]!=b'PE\\0\\0':
                return False
            machine,sections,_,_,_,optional,flags=struct.unpack_from(
                '<HHLLLHH',header,4)
            if (machine!=0x8664 or not 1<=sections<=96 or
                    optional<0x70 or optional>4096 or
                    not flags & 0x2000 or
                    at+24+optional+sections*40>size):
                return False
            option=stream.read(optional)
            if len(option)!=optional or struct.unpack_from(
                    '<H',option,0)[0]!=0x20b:
                return False
            # Explicit /NOENTRY must have AddressOfEntryPoint=0.
            entry=struct.unpack_from('<I',option,0x10)[0]
            image_size=struct.unpack_from('<I',option,0x38)[0]
            return entry==0 and image_size>0
    except (OSError,ValueError,struct.error,OverflowError):
        return False

def save_exclusive_v309(path:Path,content:str)->None:
    target=coff.private(path)
    if target.is_symlink() or target.exists() or not target.parent.is_dir():
        raise ValueError('link probe response already exists or unsafe')
    fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as f:
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
            # V312: a zero linker return code is NOT proof of PE.
            # Verify the file's executable format and architecture.
            if not verify_private_pe_dll_v312(
                    output/'private-native-link-probe-v309.dll'):
                raise ValueError('linker claimed success without genuine AMD64 PE DLL')
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
