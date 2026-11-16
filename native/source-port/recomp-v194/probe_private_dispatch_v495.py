# SPDX-License-Identifier: GPL-2.0-or-later
"""Compile and compare both dispatch paths on every generated ID (Linux)."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

UNITS=('native.c','loads.c','alu.c','stores.c','routes_v487.inc','index_v493.inc')


def checked(report,count):
    if (not isinstance(report,dict) or set(report)!={'entries','miss_ids','calls','fingerprint'} or
            type(report['entries']) is not int or report['entries']!=count or
            type(report['miss_ids']) is not int or not 0<=report['miss_ids']<=258 or
            type(report['calls']) is not int or report['calls']!=16*(count+report['miss_ids']) or
            not isinstance(report['fingerprint'],str) or not re.fullmatch('[0-9a-f]{16}',report['fingerprint'])):
        raise ValueError('invalid probe report')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('generated',type=Path,help='existing trusted owner-local prepare_v493 output')
    p.add_argument('--with-rip',action='store_true',help='check the V497 five-family build')
    a=p.parse_args()
    if sys.platform!='linux':
        p.error('the dual static compiler driver requires Linux; the C probe is portable')
    src=Path(__file__).resolve().parent
    g=a.generated.absolute()
    try:
        if any(q.is_symlink() or (q/'.git').exists() for q in (g,*g.parents)):
            raise ValueError('unsafe input directory')
        units=(*UNITS,'rip.c') if a.with_rip else UNITS
        for n in (*units,'progress.json'):
            q=g/n
            if q.is_symlink() or not q.is_file() or not 0<q.stat().st_size<=64<<20:
                raise ValueError('missing or unsafe generated unit')
        q=g/'progress.json'
        if q.stat().st_size>32768:
            raise ValueError('oversized inventory')
        inventory=json.loads(q.read_text(encoding='ascii'))
        count=inventory['metadata_start_generation']['done']
        if type(count) is not int or not 0<count<=1_000_000:
            raise ValueError('invalid inventory count')
        evidence=[]
        with tempfile.TemporaryDirectory(prefix='bb495-') as path:
            work=Path(path)
            run=work/'empty'
            run.mkdir()
            for cc in ('gcc','clang'):
                compiler=shutil.which(cc)
                if not compiler:
                    raise ValueError('missing compiler')
                exe=work/cc
                mode=['-DBB_WITH_RIP_V497'] if a.with_rip else []
                subprocess.run([compiler,*mode,'-std=c11','-O2','-static','-Wall','-Wextra','-Werror',
                                '-I',str(src),'-I',str(g),str(src/'probe_dispatch_v495.c'),
                                str(src/'dispatch_v492.c'),'-o',str(exe)],
                               cwd=work,check=True,timeout=240)
                result=subprocess.run([str(exe)],cwd=run,env={'LC_ALL':'C'},stdout=subprocess.PIPE,
                                      check=True,timeout=90)
                evidence.append(checked(json.loads(result.stdout),count))
        if evidence[0]!=evidence[1]:
            raise ValueError('compiler results differ')
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError):
        print('V495 refused: incomplete build, inconsistent inventory or failed parity',file=sys.stderr)
        return 2
    print(json.dumps(dict(probe=evidence[0],compilers=['gcc','clang'],
                          game_boot_proven=False,retail_instruction_parity_proven=False),sort_keys=True))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
