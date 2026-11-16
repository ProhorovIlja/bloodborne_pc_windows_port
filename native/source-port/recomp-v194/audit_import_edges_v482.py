# SPDX-License-Identifier: GPL-2.0-or-later
import argparse
import hashlib
import json
import mmap
from pathlib import Path
import struct
import sys
from census_v480 import census, EH, PH
from cfg_v481 import llvm, walk
from import_edges_v482 import Edges, import_index


def main():
    p=argparse.ArgumentParser(description='Offline whole-eboot relocation-backed edge audit')
    p.add_argument('--elf',required=True,type=Path)
    p.add_argument('--sha256',required=True)
    p.add_argument('--first-load-slot',required=True,type=lambda s:int(s,0))
    p.add_argument('--llvm',default='libLLVM.so.19.1')
    a=p.parse_args()
    try:
        if a.elf.is_symlink() or not a.elf.is_file() or not EH.size<=a.elf.stat().st_size<=512<<20:
            raise ValueError('invalid input')
        with a.elf.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as im:
            if hashlib.sha256(im).hexdigest()!=a.sha256:
                raise ValueError('invalid provenance')
            evidence={}
            groups,_=census(im,a.first_load_slot,evidence=evidence)
            edges=Edges(im,evidence,import_index(im,evidence))
            h=EH.unpack_from(im)
            x=next(row for row in (PH.unpack_from(im,h[5]+i*PH.size) for i in range(h[10])) if row[:2]==(1,5) and row[5])
            decode,close=llvm(a.llvm)
            try:
                report=walk(im,x[2],x[3],x[5],groups['entry']|groups['constructors']|groups['unwind'],groups['rx_relative'],decode,edges.observe)
                report['import_edges']=edges.summary()
            finally:
                close()
    except (ValueError,OSError,AttributeError,struct.error,StopIteration,KeyError):
        print('V482 refused: input, LLVM or provenance error',file=sys.stderr)
        return 2
    print(json.dumps(report,sort_keys=True))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
