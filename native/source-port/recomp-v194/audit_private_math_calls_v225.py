#!/usr/bin/env python3
"""V225 constant-memory original-game AOT direct math callsite parity.

Private original imported function offsets and game code NEVER printed.
Public CI uses fake imports and synthetic generated C only.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import tempfile
from build_private_math_imports_v224 import NAMES

CALL=re.compile(r'/\* ([A-Za-z_][A-Za-z_0-9]*) \*/\s*\{ const uint64_t t = B \+ 0x([0-9a-fA-F]+)ull;')
COMMENT=re.compile(r'/\* ([A-Za-z_][A-Za-z_0-9]*) \*/')
MAX_FILES=1200
MAX_TOTAL=4*1024**3
MAX_LINE=2*1024**2

def inspect(imports:Path,generated:Path)->dict:
    if imports.is_symlink() or not imports.is_file() or imports.stat().st_size>512000:
        raise ValueError('original imports file unsafe')
    if generated.is_symlink() or not generated.is_dir():
        raise ValueError('generated AOT directory unsafe')
    rows=imports.read_text(encoding='utf-8').splitlines()
    if not rows or rows[0]!='stub\tname' or not 0<len(rows)-1<=2000:
        raise ValueError('wrong original imports.tsv')
    names={}
    for row in rows[1:]:
        m=re.fullmatch(r'(0x[0-9a-fA-F]{1,16})\t([^\t\r\n]{1,128})',row)
        if not m:raise ValueError('invalid import slot record')
        if m.group(2) in names:raise ValueError('duplicate import name')
        names[m.group(2)]=int(m.group(1),16)
    if any(n not in names for n in NAMES):
        raise ValueError('target original math import missing')
    files=sorted(generated.glob('recomp*.c'))
    if not 2<=len(files)<=MAX_FILES or not (generated/'recomp.c').is_file():
        raise ValueError('incomplete original AOT sources')
    total=sum(f.stat().st_size for f in files)
    if total>MAX_TOTAL or any(f.is_symlink() or not f.is_file() for f in files):
        raise ValueError('unsafe generated source')
    count=Counter();mismatched=non_direct=mentions=0
    wanted=set(NAMES)
    for f in files:
        with f.open(encoding='utf-8',errors='replace') as stream:
            for line in stream:
                if len(line)>MAX_LINE:raise ValueError('unbounded generated line')
                if 'rc->call(' not in line or '/* ' not in line:continue
                m=COMMENT.search(line)
                if not m or m.group(1) not in wanted:continue
                mentions+=1
                got=CALL.search(line)
                if got is None or got.group(1)!=m.group(1):
                    non_direct+=1
                else:
                    name=got.group(1);count[name]+=1
                    if int(got.group(2),16)!=names[name]:mismatched+=1
    return {
        'format':'SHYT_V225_ORIGINAL_AOT_MATH_CALLSITE_PARITY',
        'generated_source_files':len(files),
        'original_AOT_math_import_call_sites':mentions,
        'direct_image_base_target_calls':sum(count.values()),
        'distinct_math_imports_referenced':len(count),
        'mismatched_private_import_offsets':mismatched,
        'unexpected_non_direct_math_calls':non_direct,
        'exact_mapping_verified':mismatched==0 and non_direct==0 and len(count)==len(NAMES),
        'real_guest_execution_proven':False,
        'no_proprietary_addresses_or_game_code_emitted':True,
    }

def selftest()->None:
    with tempfile.TemporaryDirectory() as tmp:
        d=Path(tmp);g=d/'generated';g.mkdir()
        i=d/'imports.tsv'
        i.write_text('stub\tname\n'+''.join(
            f'0x{256+n*16:x}\t{name}\n' for n,name in enumerate(NAMES)))
        f=g/'recomp_00000.c'
        f.write_text(''.join(
            f'/* {name} */ {{ const uint64_t t = B + 0x{256+n*16:x}ull; rc->call(c,t,0x123); }}\n'
            for n,name in enumerate(NAMES)))
        (g/'recomp.c').write_text('/* fictional registration table */\n')
        good=inspect(i,g)
        assert good['original_AOT_math_import_call_sites']==23
        assert good['exact_mapping_verified'] and not good['real_guest_execution_proven']
        assert '0x100' not in json.dumps(good)
        f.write_text(f.read_text().replace('0x100ull','0x200ull',1))
        bad=inspect(i,g)
        assert bad['mismatched_private_import_offsets']==1
        assert not bad['exact_mapping_verified']
    print('SHYT_V225_PRIVATE_AOT_MATH_TARGET_STREAM_SELFTEST_PASS')

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--original-imports',type=Path)
    ap.add_argument('--generated-dir',type=Path)
    ap.add_argument('--self-test',action='store_true')
    args=ap.parse_args()
    if args.self_test:selftest()
    elif args.original_imports and args.generated_dir:
        try:print(json.dumps(inspect(args.original_imports,args.generated_dir),separators=(',',':')))
        except (ValueError,OSError) as exc:ap.error(str(exc))
    else:ap.error('provide --self-test or both private inputs')
