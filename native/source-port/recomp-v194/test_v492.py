# SPDX-License-Identifier: GPL-2.0-or-later
from test_v488 import p
from store_v491 import find,emit
from progress_v490 import inventory

raw=bytes.fromhex('48897701c3')
x=(1,5,0,200,0,len(raw),len(raw),1)
rows=list(find(raw,x,[200]))
assert len(rows)==1
report=inventory([100,108,200],{'other':[100,108],'store':[200]},[108])
assert report['metadata_start_generation']['percent']=='100.00'
try:
    inventory([100,108,200],{'other':[100,200],'store':[200]},[108])
except ValueError:
    pass
else:
    raise AssertionError('ambiguous route accepted')
with (p/'stores.c').open('w',encoding='ascii') as f:
    emit(rows,f)
