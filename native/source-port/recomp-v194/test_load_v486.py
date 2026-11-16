# SPDX-License-Identifier: GPL-2.0-or-later
from pathlib import Path
from load_v486 import decode, emit, find

rows=[]
for i,s in enumerate(('488b07c3','8b4701c3','0fbe47ffc3','48638700000000c3')):
    b=bytes.fromhex(s)
    x=(1,5,0,100+i,0,len(b),len(b),1)
    rows.extend(find(b,x,[100+i]))
    assert decode(b[:-1]) is None
assert len(rows)==4
for s in ('488907c3','8b05ffffffffc3','678b07c3','8b04c3','8b07c20800'):
    assert decode(bytes.fromhex(s)) is None
with Path('fixture_v486.c').open('w',encoding='ascii') as f:
    emit(rows,f)
    f.write(r'''
int main(void) {
 unsigned char b[8]={0x80,0xff,0xff,0xff,0xff,0,0,0};
 struct bb_region_v478 r={256,sizeof b,b};
 uint64_t v=0;
 if(!bb_load_v486(100,256,&r,&v)||v!=UINT64_C(0xffffffff80))return 1;
 if(!bb_load_v486(101,256,&r,&v)||v!=UINT32_MAX)return 2;
 if(!bb_load_v486(102,257,&r,&v)||v!=UINT32_C(0xffffff80))return 3;
 if(!bb_load_v486(103,256,&r,&v)||v!=UINT64_C(0xffffffffffffff80))return 4;
 if(bb_load_v486(104,256,&r,&v)||bb_load_v486(100,257,&r,&v)||
    bb_load_v486(102,256,&r,&v)||v!=UINT64_C(0xffffffffffffff80))return 5;
 return 0;
}
''')
