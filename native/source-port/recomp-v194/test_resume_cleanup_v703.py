# SPDX-License-Identifier: GPL-2.0-or-later
"""Compare the nested cleanup thunk offline on Linux x86-64."""
from hashlib import sha256
from pathlib import Path
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory

from resume_switch_v697 import SHA


def run(path, compilers):
    blob = path.read_bytes()
    if sha256(blob).hexdigest() != SHA:
        raise ValueError('unexpected build')
    pc = 0x69750
    code = blob[pc+0x4000:pc+0x4000+30]
    if (code[10:13] != b'\x48\x8d\x05' or
            pc+17+struct.unpack_from('<i',code,13)[0] != 0x53e7320):
        raise ValueError('unexpected global receiver load')
    # Relocate the original LEA. The flag test, table lookup and tail call
    # are original instructions; the receiver and method are host fixtures.
    raw = lambda b: '.byte '+','.join(map(str,b))
    asm = '\n'.join(['.text','.globl ref','ref:',raw(code[:13]),
                     '.long receiver - . - 4',raw(code[17:]),
                     '.section .note.GNU-stack,"",@progbits',''])
    harness = r'''
#include "resume_cleanup_v703.h"
#include <stdio.h>
#include <stdlib.h>
#define OK(x) do { if (!(x)) abort(); } while (0)
struct receiver { void (**vt)(struct receiver *,uint64_t); };
struct receiver *receiver;
extern void ref(const void *);
static unsigned calls, miss;
static struct receiver *actual;
static uint64_t seen;
static void method(struct receiver *p, uint64_t value) {
    ++calls; actual=p; seen=value;
}
static int invoke(void *ctx, unsigned slot, uint64_t value) {
    OK(!ctx && slot==0x68);
    if (miss || !receiver) return 0;
    receiver->vt[slot/8](receiver,value);
    return 1;
}
int main(void) {
    void (*vt[14])(struct receiver *,uint64_t) = {[13]=method};
    struct receiver a={vt}, b={vt};
    unsigned char record[0x39]={0};
    for (unsigned i=0;i<4096;i++) {
        uint64_t arg = i%4 ? UINT64_MAX-i : 0;
        memcpy(record+0x10,&arg,8);
        record[0x38]=i%256;
        receiver=i&1 ? &a : &b;
        calls=0; actual=NULL; seen=0;
        ref(record);
        unsigned n=calls;
        struct receiver *which=actual;
        uint64_t expected=seen;
        calls=0; actual=NULL; seen=0;
        OK(bb_resume_cleanup703(record,sizeof record,NULL,invoke));
        OK(calls==n && actual==which && seen==expected);
        calls=0;
        OK(!bb_resume_cleanup703(record,0x38,NULL,invoke) && !calls);
        OK(!bb_resume_cleanup703(NULL,sizeof record,NULL,invoke) && !calls);
        miss=1;
        OK(bb_resume_cleanup703(record,sizeof record,NULL,invoke)==!record[0x38] && !calls);
        miss=0;
    }
    puts("4096 differential outcomes; 12288 bounds/resolution checks");
}
'''
    with TemporaryDirectory(prefix='bb703-') as d:
        tmp = Path(d)
        (tmp/'oracle.S').write_text(asm)
        (tmp/'test.c').write_text(harness)
        for cc in compilers:
            subprocess.run([cc,'-O2','-Wall','-Wextra','-Werror','-no-pie','-I',
                            str(Path(__file__).resolve().parent),'oracle.S','test.c',
                            '-o','test'],cwd=tmp,check=True)
            print(cc, subprocess.check_output([tmp/'test'],text=True,timeout=10).strip())


if __name__ == '__main__':
    run(Path(sys.argv[1]), sys.argv[2:] or ['cc'])
