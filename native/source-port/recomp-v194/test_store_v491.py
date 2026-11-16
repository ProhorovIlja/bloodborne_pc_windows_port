# SPDX-License-Identifier: GPL-2.0-or-later
from pathlib import Path
from store_v491 import decode,emit,find

codes=['c607ffc3','66c74701ff80c3','48c74702ffffffffc3','884fffffc3',
       '8857ffc3','48897701c3','4889b7ffffffffc3','48893fc3']
rows=[]
for a,code in enumerate(codes):
    raw=bytes.fromhex(code)
    if a==3:
        assert decode(raw) is None
        continue
    assert decode(raw[:-1]) is None
    x=(1,5,0,a,0,len(raw),len(raw),1)
    got=list(find(raw,x,[a]))
    assert len(got)==1 and got[0][1]==raw
    if a==6:
        assert got[0][2:5]==(-1,8,6)
    rows+=got
for code in ('884707c3','408837c3','8827c3','678937c3','488937c20800','c70f01000000c3'):
    assert decode(bytes.fromhex(code)) is None
with Path('fixture_store_v491.c').open('w',encoding='ascii') as f:
    emit(rows,f)
    f.write(r'''
#include <string.h>
int main(void) {
    unsigned char data[16]={0}, old[16];
    struct bb_store_input_v491 r={100,UINT64_C(0x0807060504030201),0xc0,0x90};
    if(bb_store_v491(0,&r,data,100,16)!=1||data[0]!=255) return 1;
    if(bb_store_v491(1,&r,data,100,16)!=1||data[1]!=255||data[2]!=128||data[3]) return 2;
    if(bb_store_v491(2,&r,data,100,16)!=1||data[2]!=255||data[9]!=255||data[10]) return 3;
    if(bb_store_v491(5,&r,data,100,16)!=1||data[1]!=1||data[8]!=8) return 4;
    memcpy(old,data,sizeof old);
    if(bb_store_v491(4,&r,data,100,16)!=2||bb_store_v491(5,&r,data,100,8)!=2||
       bb_store_v491(3,&r,data,100,16)!=0||bb_store_v491(7,&r,0,100,16)!=2||
       bb_store_v491(0,&r,data,UINT64_MAX,16)!=2||memcmp(old,data,sizeof old)) return 5;
    r.rdi=101;
    if(bb_store_v491(4,&r,data,100,16)!=1||data[0]!=0xc0||
       bb_store_v491(6,&r,data,100,16)!=1||data[0]!=1||data[7]!=8) return 6;
    if(bb_store_v491(7,&r,data,100,16)!=1||data[1]!=101||data[8]) return 7;
    return 0;
}
''')
