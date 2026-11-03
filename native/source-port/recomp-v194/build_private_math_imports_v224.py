#!/usr/bin/env python3
"""V224: original user-owned import offsets -> private C at BUILD TIME.

No original guest addresses, names, ELF bytes or generated C are printed.
Refuses output inside a Git worktree to avoid publishing game offsets.
The generated descriptors do not require EBOOT during game execution.
"""
import argparse
from pathlib import Path
import re

NAMES=('acos','acosf','asin','asinf','atan','atan2','atan2f','atanf',
       'exp','exp2','exp2f','expf','fmod','fmodf','frexp','frexpf',
       'ldexp','ldexpf','pow','powf','tan','tanf','tanhf')

def make(input_file:Path,output_file:Path)->int:
    if input_file.is_symlink() or not input_file.is_file() or input_file.stat().st_size>512000:
        raise ValueError('unsafe original import index')
    if output_file.is_symlink() or any((x/'.git').exists() for x in
                                       (output_file,*output_file.parents)):
        raise ValueError('derived code must not enter a public Git worktree')
    rows=input_file.read_text(encoding='utf-8').splitlines()
    if not rows or rows[0]!='stub\tname' or len(rows)>2001:
        raise ValueError('wrong original V213 imports.tsv')
    mapping={}
    for row in rows[1:]:
        match=re.fullmatch(r'(0x[0-9a-fA-F]{1,16})\t([^\t\r\n]{1,128})',row)
        if not match: raise ValueError('invalid original import row')
        offset=int(match.group(1),16)
        name=match.group(2)
        if name in mapping or offset==0: raise ValueError('duplicate or zero import')
        mapping[name]=offset
    if any(n not in mapping for n in NAMES):
        raise ValueError('one or more of the 23 expected math imports missing')
    if len({mapping[n] for n in NAMES})!=23:
        raise ValueError('duplicate imported math slot')
    output=[
        '/* PRIVATE generated from owner original imports. DO NOT PUBLISH. */',
        '#include "native_math_import_dispatch_v224.h"',
        'const ShytMathImportDesc shyt_private_math_descs[23] = {']
    output.extend(f'    {{UINT64_C(0x{mapping[n]:x}), "{n}"}},' for n in NAMES)
    output.extend(['};','const size_t shyt_private_math_count = 23;',''])
    if not output_file.parent.is_dir(): raise ValueError('private output parent missing')
    output_file.write_text('\n'.join(output),encoding='utf-8')
    return 23

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--original-imports',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    try: n=make(args.original_imports,args.output)
    except (ValueError,OSError) as e: p.error(str(e))
    print(f'SHYT_V224_PRIVATE_MATH_IMPORT_DESC_PASS count={n}')
