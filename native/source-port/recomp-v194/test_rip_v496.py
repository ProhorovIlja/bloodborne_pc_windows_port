# SPDX-License-Identifier: GPL-2.0-or-later
from pathlib import Path
from rip_v496 import emit,find

rx=(1,5,0,100,0,80,80,1)
rw=(1,6,80,200,0,8,16,1)
image=bytearray(b'\x90'*80)
def lea(a,t,prefix=b'',op=b'\x48\x8d\x05'):
    body=prefix+op+(t-a-len(prefix)-7).to_bytes(4,'little',signed=True)+b'\xc3'
    image[a-100:a-100+len(body)]=body
lea(100,200)
lea(116,215,b'\xf3\x0f\x1e\xfa')
lea(132,100)
lea(148,216)
lea(164,210,op=b'\x48\x8b\x05')
ids=[100,116,132,148,164]
rows=list(find(image,rx,rw,ids))
assert [(a,t) for a,_,t in rows]==[(100,200),(116,215)]
assert [a for a,*_ in find(image,rx,rw,[*ids,103])]==[116]
try:
    list(find(image,rx,(1,6,80,170,0,8,16,1),ids))
except ValueError:
    pass
else:
    raise AssertionError('overlapping RX/RW accepted')
with Path('fixture_rip_v496.c').open('w',encoding='ascii') as f:
    emit(rows,f)
    f.write(r'''
int main(void) {
    struct bb_result_v484 out={0};
    if(bb_rip_v496(100,0,0x202,&out)!=BB_RIP_OK_V496 ||
        out.rax!=200 || out.flags!=0x202 || out.flags_valid!=0x8d5) return 1;
    if(bb_rip_v496(116,UINT64_MAX-215,0x8d5,&out)!=BB_RIP_OK_V496 ||
        out.rax!=UINT64_MAX || out.flags!=0x8d5 || out.flags_valid!=0x8d5) return 2;
    if(bb_rip_v496(116,UINT64_MAX-214,0,&out)!=BB_RIP_DENIED_V496 ||
        bb_rip_v496(116,0,0,NULL)!=BB_RIP_DENIED_V496 ||
        bb_rip_v496(132,0,0,&out)!=BB_RIP_MISS_V496 ||
        bb_rip_v496(148,0,0,&out)!=BB_RIP_MISS_V496 ||
        bb_rip_v496(164,0,0,&out)!=BB_RIP_MISS_V496 ||
        out.rax!=UINT64_MAX || out.flags!=0x8d5 || out.flags_valid!=0x8d5) return 3;
    return 0;
}
''')


alias_image=bytearray(b'\x90'*128)
alias_rx=(1,5,0,256,0,128,128,1)
alias_rw=(1,6,128,400,0,0,8,1)
def jmp(a,t,prefix=b'',short=False):
    n=1 if short else 4
    raw=prefix+(b'\xeb' if short else b'\xe9')+(t-a-len(prefix)-1-n).to_bytes(n,'little',signed=True)
    alias_image[a-256:a-256+len(raw)]=raw
jmp(256,272)
jmp(272,320,b'\xf3\x0f\x1e\xfa',short=True)
jmp(288,304)
jmp(304,288)
jmp(336,321)
jmp(352,320)
jmp(368,320,short=True)
alias_image[64:72]=b'\x48\x8d\x05'+(400-327).to_bytes(4,'little',signed=True)+b'\xc3'
starts=[256,272,288,304,320,336,352,354,368]
assert [(a,t) for a,_,t in find(alias_image,alias_rx,alias_rw,starts)]==[(320,400)]
alias_rows=list(find(alias_image,alias_rx,alias_rw,starts,tail_aliases=True))
assert [(a,t) for a,_,t in alias_rows]==[(256,400),(272,400),(320,400),(368,400)]
assert not list(find(alias_image,alias_rx,alias_rw,[a for a in starts if a!=320],tail_aliases=True))
