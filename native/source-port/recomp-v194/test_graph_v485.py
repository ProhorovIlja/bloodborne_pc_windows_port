# SPDX-License-Identifier: GPL-2.0-or-later
from pathlib import Path
from graph_v485 import graph,emit

# 0 MOV EAX,42; 8 JMP 0; 16 CALL 8/RET; 24 JMP 24;
# 32 JMP to an interior byte; 40 JMP to the end of RX.
image=bytearray(b'\x90'*48)
for off,s in [(0,'b82a000000c3'),(8,'ebf6'),(16,'e8f3ffffffc3'),
              (24,'ebfe'),(32,'ebdf'),(40,'eb06')]:
    raw=bytes.fromhex(s)
    image[off:off+len(raw)]=raw
x=(1,5,0,100,0,len(image),len(image),1)
rows,declined=graph(image,x,range(100,148,8))
assert list(rows)==[100,108,116] and declined==3
assert rows[116][-1]==108 and rows[108][-1]==100
assert 100 not in graph(image,x,[100,101])[0]
chain=b'\xeb\x00'*10+b'\xc3'
closed,n=graph(chain,(1,5,0,0,0,len(chain),len(chain),1),range(0,len(chain),2))
assert len(closed)==9 and n==2 and list(closed)[0]==4
with Path('v485_fixture.c').open('w',encoding='ascii') as f:
    emit(rows,f)
    f.write(r'''
int main(void) {
 struct bb_result_v484 r={1,2,3};
 for(uint64_t id=100;id<=116;id+=8)
   if(!bb_call_v485(id,7,8,9,10,11,0x8d5,&r) || r.rax!=42 ||
      r.flags!=0x8d5 || r.flags_valid!=0x8d5) return 1;
 r=(struct bb_result_v484){1,2,3};
 for(uint64_t id=124;id<=140;id+=8)
   if(bb_call_v485(id,0,0,0,0,0,0,&r)) return 2;
 return r.rax!=1 || r.flags!=2 || r.flags_valid!=3;
}
''')
