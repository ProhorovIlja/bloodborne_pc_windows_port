# SPDX-License-Identifier: GPL-2.0-or-later
from pathlib import Path
from alu_v488 import decode, emit, find
from prepare_v488 import prepare
from test_v487 import p

ops=['4883c001c3','83e8ffc3','4821f8c3','4839f8c3','8d4477ffc3',
     '4831c04883c001c3','4805ffffffffc3']
image=bytearray(b'\x90'*192)
image[0:6]=bytes.fromhex('b82a000000c3')
image[16:20]=bytes.fromhex('488b07c3')
for j,s in enumerate(ops):
    a=32+16*j
    raw=bytes.fromhex(s)
    image[a:a+len(raw)]=raw
    assert decode(raw[:-1]) is None
for s in ('48830701c3','488d0500000000c3','488d042500000000c3','4883d001c3','f04801f8c3','c3'):
    assert decode(bytes.fromhex(s)) is None
x=(1,5,0,0,0,len(image),len(image),1)
ids=[0,16]+[32+16*j for j in range(len(ops))]
g,l,t=prepare(image,x,ids)
rows=list(find(image,x,ids,g.keys()|t.keys()))
assert [a for a,*_ in rows]==ids[2:]
with (p/'alu.c').open('w',encoding='ascii') as f:
    emit(rows,f)
