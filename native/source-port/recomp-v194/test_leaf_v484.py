# SPDX-License-Identifier: GPL-2.0-or-later
from io import StringIO
from pathlib import Path
from leaf_v484 import decode, find, emit

cases=['31c0c3','33c0c3','4831c0c3','f30f1efab080c3','488d07c3',
       '488d47ffc3','488d8700000080c3']
rows=[]
for i,s in enumerate(cases):
    raw=bytes.fromhex(s)
    x=(1,5,0,100+i*16,0,len(raw),len(raw),1)
    row=list(find(raw,x,[x[3]]))
    assert len(row)==1 and row[0][1]==raw
    assert not list(find(raw[:-1],x[:5]+(len(raw)-1,)*2+x[7:],[x[3]]))
    rows.extend(row)
for s in ('31c9c3','483100c3','488d4601c3','8a4708c3','b001c20000','488d05c3'):
    assert decode(bytes.fromhex(s)) is None
try:
    emit(rows[::-1],StringIO())
except ValueError:
    pass
else:
    raise AssertionError('unsorted dispatch accepted')
with Path('v484_fixture.c').open('w',encoding='ascii') as f:
    emit(rows,f)
    f.write(r'''
int main(void) {
 struct bb_result_v484 r={5,6,7};
 const uint64_t expected[]={0,0,0,0xfedcba9876543280ull,0,UINT64_MAX,0xffffffff80000000ull};
 for(size_t i=0;i<7;++i) {
   if(!bb_call_v484(100+i*16,0xfedcba9876543210ull,0,0x8d5,&r) || r.rax!=expected[i]) return 1;
   if(i<3) { if(r.flags_valid!=0x8c5 || (r.flags&r.flags_valid)!=0x44) return 2; }
   else if(r.flags_valid!=0x8d5 || r.flags!=0x8d5) return 3;
 }
 r=(struct bb_result_v484){5,6,7};
 if(bb_call_v484(101,0,0,0,&r) || bb_call_v484(UINT64_MAX,0,0,0,&r)
     || bb_call_v484(100,0,0,0,NULL) || r.rax!=5 || r.flags!=6 || r.flags_valid!=7) return 4;
 return 0;
}
''')
