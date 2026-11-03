#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V342: owner-local, read-only Bloodborne / Dark Souls III asset census.

Both games were supplied by their owner in private Drive folders. For a
true standalone Windows port, the next native I/O step requires identifying
which game asset-container families can share a parser/streamer. This CLI
checks ONLY owner-local mounted/private trees and emits bounded aggregate
format counts, never file names, file content or original paths. No data
is sent to GitHub or the network. This is NOT game data decoding or boot.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import stat

MAX_FILES=250_000
MAX_DEPTH=16
MAX_FILE_BYTES=64*1024**3
FAMILIES={
    b'DCX\0':'DCX compression wrapper',
    b'BND4':'BND4 asset binder',
    b'BHF4':'BHF4 binder index',
    b'BDF4':'BDF4 binder data',
    b'BND3':'BND3 asset binder',
    b'BHF3':'BHF3 binder index',
    b'BDF3':'BDF3 binder data',
    b'FLVER':'FLVER geometry',
    b'TPF\0':'TPF texture pack',
    b'DDS ':'DDS texture',
    b'MSB ':'MSB map data',
}
KNOWN_DIRS=frozenset({
    'chr','map','parts','obj','sfx','shader','sound','menu','msg','event',
    'param','paramdef','drawparam','gameparam','script','remo','movie',
    'mtd','facegen','action','other','font','adhoc'
})

def owner_root(root:Path)->Path:
    # Reject any directory owned by this repository, including a parent
    # of the checkout. Original assets may never become public CI inputs.
    root=root.absolute()
    if not root.is_dir() or root.is_symlink() or any(
        (parent/'.git').exists() for parent in (root,*root.parents)
    ):
        raise ValueError('private original-game tree must be outside Git')
    return root.resolve(strict=True)

def family(name:str,first:bytes)->str:
    # Magic wins. File extension is only a *candidate* for encrypted
    # containers, not proof their format is decoded or compatible.
    for prefix,label in FAMILIES.items():
        if first.startswith(prefix):
            return label
    ext=Path(name).suffix.lower()
    if ext in ('.dcx','.bnd','.bhd','.bdt','.param','.hkx','.hkx.dcx',
               '.flver','.tpf','.msb','.emevd','.esd','.fmg','.ffx',
               '.wem','.bnk','.fsb','.fev','.fxr'):
        return 'extension:'+ext
    return 'unclassified'

def census(root:Path)->dict:
    root=owner_root(root)
    todo=[(root,0)]
    total=0
    size=0
    formats=Counter()
    directories=Counter()
    while todo:
        directory,depth=todo.pop()
        if depth>MAX_DEPTH:
            raise ValueError('private game folder nesting exceeds cap')
        with os.scandir(directory) as children:
            for child in children:
                info=child.stat(follow_symlinks=False)
                if stat.S_ISLNK(info.st_mode):
                    raise ValueError('private game tree includes link')
                if stat.S_ISDIR(info.st_mode):
                    if depth==MAX_DEPTH:
                        raise ValueError('private game folder nesting exceeds cap')
                    todo.append((Path(child.path),depth+1))
                    continue
                if not stat.S_ISREG(info.st_mode):
                    raise ValueError('unexpected special private game file')
                total+=1
                if total>MAX_FILES or info.st_size>MAX_FILE_BYTES:
                    raise ValueError('private game inventory budget exceeded')
                size+=info.st_size
                # Only a small signature, never content or filenames.
                with open(child.path,'rb') as fp:
                    head=fp.read(16)
                formats[family(child.name,head)]+=1
                try:
                    relative=Path(child.path).relative_to(root)
                except ValueError as error:
                    raise ValueError('private file escaped root') from error
                name=relative.parts[0].lower()
                directories[name if name in KNOWN_DIRS else 'other_dirs']+=1
    if not total:
        raise ValueError('no original assets found')
    return {'files':total,'bytes':size,
            'formats':dict(sorted(formats.items())),
            'groups':dict(sorted(directories.items()))}

def main()->None:
    parser=argparse.ArgumentParser()
    parser.add_argument('--bloodborne-dvdroot',required=True,type=Path)
    parser.add_argument('--dark-souls-iii-game',required=True,type=Path)
    args=parser.parse_args()
    bb=owner_root(args.bloodborne_dvdroot)
    ds=owner_root(args.dark_souls_iii_game)
    if bb==ds or bb in ds.parents or ds in bb.parents:
        raise ValueError('private title roots are not independent')
    data={'schema':'SHYT_NATIVE_PRIVATE_ASSET_CENSUS_V342',
          'bloodborne':census(bb),'dark_souls_iii':census(ds)}
    # Aggregate-only JSON, no private path, file name, asset bytes,
    # hash or full filename manifest leaves the owner's workstation.
    print(json.dumps(data,sort_keys=True,separators=(',',':')))

if __name__=='__main__':
    try:main()
    except (ValueError,OSError) as exc:
        raise SystemExit('SHYT_V342_PRIVATE_ASSET_CENSUS_REFUSED: '+
                         type(exc).__name__) from None
