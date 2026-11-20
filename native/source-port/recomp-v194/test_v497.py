# SPDX-License-Identifier: GPL-2.0-or-later
from pathlib import Path
from shutil import copyfile
from test_v493 import p
from index_v493 import write_index
from rip_v496 import find,emit

dest=Path('v497-fixture')
dest.mkdir(exist_ok=True)
for n in ('native.c','loads.c','alu.c','stores.c','routes_v487.inc'):
    copyfile(p/n,dest/n)
raw=bytes.fromhex('488d055d000000c3')
x=(1,5,0,256,0,len(raw),len(raw),1)
rw=(1,6,8,356,0,0,8,1)
rows=list(find(raw,x,rw,[256]))
assert [a for a,_,t in rows if t==356]==[256]
with (dest/'rip.c').open('w',encoding='ascii') as f:
    emit(rows,f)
(dest/'index_v493.inc').unlink(missing_ok=True)
assert write_index(dest,with_rip=True)==15
