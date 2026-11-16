# SPDX-License-Identifier: GPL-2.0-or-later
from pathlib import Path
from leaf_v483 import decode, emit, find

cases={
    'c3':'rax', 'f30f1efac3':'rax', '89f8c3':'(uint32_t)rdi',
    '488bc6c3':'rsi','b8ffffffffc3':'4294967295ull',
    '48c7c0ffffffffc3':'18446744073709551615ull',
    '48b80000000000000080c3':'9223372036854775808ull',
}
rows=[]
for i,(text,expr) in enumerate(cases.items()):
    raw=bytes.fromhex(text)
    row=list(find(raw,0,100,len(raw),[100]))
    assert row==[(100,raw,expr)]
    assert decode(raw[:-1]) is None
    rows.append((i,raw,expr))
for text in ('31c0c3','488907c3','48b80200000000000000c2','41b801000000c3','e800000000c3','c20800'):
    assert decode(bytes.fromhex(text)) is None
with Path('v483_fixture.c').open('w',encoding='ascii') as f:
    emit(rows,f)
    print('int main(void) {',file=f)
    print(' uint64_t expected[]={42,42,9,8,4294967295ull,18446744073709551615ull,9223372036854775808ull};',file=f)
    print(' for(unsigned i=0;i<leaf_count;++i) if(leaves[i](42,3,5,8,0x100000009ull)!=expected[i])return 1;',file=f)
    print(' return 0; }',file=f)
