# SPDX-License-Identifier: GPL-2.0-or-later
from pathlib import Path
from prepare_v487 import prepare,emit_graph,emit_loads,emit_routes

image=bytearray(b'\x90'*48)
for pos,code in [(0,'b82a000000c3'),(8,'488b07c3'),(16,'ebf6'),
                 (24,'ebf6'),(32,'ebfe'),(40,'ebdf')]:
    b=bytes.fromhex(code)
    image[pos:pos+len(b)]=b
x=(1,5,0,100,0,len(image),len(image),1)
g,l,t=prepare(image,x,range(100,148,8))
assert list(g)==[100] and t=={108:108,116:108,124:108}
p=Path('v487-fixture')
p.mkdir(exist_ok=True)
for name,emit,rows in (('native.c',emit_graph,g),('loads.c',emit_loads,l),('routes_v487.inc',emit_routes,t)):
    with (p/name).open('w',encoding='ascii') as f:
        emit(rows,f)
