# SPDX-License-Identifier: GPL-2.0-or-later
"""Compare the V702 direct helper against original instructions on Linux x86-64."""
from hashlib import sha256
from pathlib import Path
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory


def oracle(path):
    blob = path.read_bytes()
    if sha256(blob).hexdigest() != '941f887a562aae054fac35af8cc8f27cf075f3d4cc2e029fb5ae2a663aaa5ae7':
        raise ValueError('unexpected executable')
    start = 0x3d1ba0
    code = blob[start:0x3d1c9c]
    asm = ['.text', '.globl ref', 'ref:']
    pos = 0
    for addr, dst, name in ((0x3d1c06,0x3d1ca0,'prep'),(0x3d1c20,0x3cb350,'detach'),
                           (0x3d1c30,0x3d0820,'drop'),(0x3d1c5a,0x3cb350,'detach'),
                           (0x3d1c68,0x3d0820,'drop'),(0x3d1c81,0x3d0820,'drop')):
        at = addr-start
        if code[at] != 0xe8 or addr+5+struct.unpack_from('<i',code,at+1)[0] != dst:
            raise ValueError('unexpected direct dependency')
        asm += ['.byte '+','.join(map(str,code[pos:at])), 'call '+name]
        pos = at+5
    asm += ['.byte '+','.join(map(str,code[pos:])), '.section .note.GNU-stack,"",@progbits']
    return '\n'.join(asm)+'\n'


TEST = r'''
#include "resume_release_v704.h"
#include <stdio.h>
#include <stdlib.h>
#define OK(x) do { if (!(x)) abort(); } while (0)
static uint64_t mem[120], slots[3], logbuf[32];
static size_t used;
extern void ref(uint64_t *,uint64_t *,uint64_t *);
void prep(const void *p,uint64_t a,uint64_t b) {
    OK(p==mem);
    logbuf[used++]=1; logbuf[used++]=a; logbuf[used++]=b;
    mem[117]++; mem[119]++; slots[1]^=123; slots[2]^=321;
}
void detach(const void *p,uint64_t child,uint32_t cap,uint32_t mode) {
    OK(p==mem && cap==0x4000 && mode==UINT32_MAX);
    logbuf[used++]=2; logbuf[used++]=child;
    logbuf[used++]=slots[1]; logbuf[used++]=slots[2];
}
void drop(uint64_t token,uint64_t x,uint64_t y) {
    logbuf[used++]=3; logbuf[used++]=token;
    logbuf[used++]=x; logbuf[used++]=y;
}
static void pwrap(void *c,const void *p,uint64_t a,uint64_t b) { OK(!c); prep(p,a,b); }
static void dwrap(void *c,const void *p,uint64_t t,uint32_t n,uint32_t m) { OK(!c); detach(p,t,n,m); }
static void rwrap(void *c,uint64_t t,uint64_t x,uint64_t y) { OK(!c); drop(t,x,y); }
static void reset(const uint64_t init[3],unsigned i) {
    memcpy(slots,init,sizeof slots); memset(logbuf,0,sizeof logbuf); used=0;
    mem[117]=UINT64_MAX-i; mem[119]=i*99u;
}
int main(void) {
    const struct bb_release_ops704 ops={NULL,pwrap,dwrap,rwrap};
    for (unsigned i=0;i<4096;i++) {
        uint64_t init[]={i&1?(uintptr_t)mem:0,i&2?i:0,i&4?UINT64_MAX-i:0};
        uint64_t *o=i&8?NULL:slots, *a=i&16?NULL:slots+1, *b=i&32?NULL:slots+2;
        if (i&64) b=a;
        if (i&128) a=o;
        if (i&256) b=o;
        reset(init,i); ref(o,a,b);
        uint64_t expected[32], after[3], x=mem[117], y=mem[119];
        size_t count=used;
        memcpy(expected,logbuf,sizeof expected); memcpy(after,slots,sizeof after);
        reset(init,i);
        int noop=!o || !*o;
        OK(bb_release704(o,a,b,mem,sizeof mem-1,&ops)==noop);
        OK(bb_release704(o,a,b,mem,sizeof mem,NULL)==noop);
        OK(!used && !memcmp(slots,init,sizeof slots));
        OK(bb_release704(o,a,b,mem,sizeof mem,&ops));
        OK(used==count && !memcmp(expected,logbuf,sizeof expected));
        OK(!memcmp(after,slots,sizeof after) && x==mem[117] && y==mem[119]);
    }
    puts("4096 original/native comparisons, 8192 span/provider checks");
}
'''


if __name__ == '__main__':
    asm = oracle(Path(sys.argv[1]))
    with TemporaryDirectory(prefix='bb704-') as d:
        root = Path(d)
        (root/'oracle.S').write_text(asm)
        (root/'test.c').write_text(TEST)
        for cc in sys.argv[2:] or ['cc']:
            subprocess.run([cc,'-O2','-Wall','-Wextra','-Werror','-I',
                            str(Path(__file__).resolve().parent),'oracle.S','test.c',
                            '-o','test'],cwd=root,check=True)
            print(cc,subprocess.check_output([root/'test'],text=True,timeout=10).strip())
