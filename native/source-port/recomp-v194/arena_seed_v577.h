/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_ARENA_SEED_V577_H
#define BB_ARENA_SEED_V577_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#define BB_ARENA_SIZE_V577 UINT64_C(0x7400000)
#define BB_ARENA_ALIGN_V577 UINT64_C(0x200000)
#define BB_ARENA_OBJECT_V577 0x488u
static inline void bb_arena_qword_v577(unsigned char *p,uint64_t v) {
    for (unsigned i=0;i<8;++i) p[i]=(unsigned char)(v>>(8*i));
}
/* Successful mapping path only. Both writable regions must be live,
 * disjoint, stable CPU storage. Mutex setup at object+0x10 is separate.
 * Stores native addresses, never RVAs into the input executable. */
static inline int bb_arena_seed_v577(unsigned char *obj,size_t size,
    unsigned char *mem,size_t length,uint64_t physical) {
    const uint64_t a=(uintptr_t)mem, o=(uintptr_t)obj;
    if (!obj || !mem || sizeof(uintptr_t)!=8 || size<BB_ARENA_OBJECT_V577 ||
        length!=BB_ARENA_SIZE_V577 || (a%BB_ARENA_ALIGN_V577) || (o&7) ||
        (physical%BB_ARENA_ALIGN_V577) || a>UINT64_MAX-length ||
        physical>UINT64_MAX-length || o>UINT64_MAX-BB_ARENA_OBJECT_V577 ||
        (o<a+length && a<o+BB_ARENA_OBJECT_V577)) return 0;
    const uint64_t end=a+length-16, last=end-16, free_size=last-a;
    unsigned bucket=0;
    for (uint64_t n=free_size;n>1;n>>=1) ++bucket;
    memset(obj+0x28,0,0x460);
    for (unsigned i=0;i<64;++i) {
        const size_t p=0x40+16u*i;
        bb_arena_qword_v577(obj+p+16,o+p);
        bb_arena_qword_v577(obj+p+24,o+p);
    }
    bb_arena_qword_v577(obj+0x30,a+16);
    bb_arena_qword_v577(obj+0x38,end);
    bb_arena_qword_v577(obj+0x40,free_size);
    bb_arena_qword_v577(obj+0x450,a);
    bb_arena_qword_v577(obj+0x458,last);
    bb_arena_qword_v577(obj+0x460,free_size);
    bb_arena_qword_v577(obj+0x468,a);
    bb_arena_qword_v577(obj+0x470,physical);
    bb_arena_qword_v577(obj+0x478,length);
    const size_t p=0x40+16u*bucket;
    bb_arena_qword_v577(obj+p+16,a);
    bb_arena_qword_v577(obj+p+24,a);
    bb_arena_qword_v577(obj+0x28,UINT64_C(1)<<bucket);
    bb_arena_qword_v577(mem+8,last|2);
    bb_arena_qword_v577(mem+16,o+p);
    bb_arena_qword_v577(mem+24,o+p);
    bb_arena_qword_v577(mem+length-32,a);
    bb_arena_qword_v577(mem+length-24,a|1);
    return 1;
}
#endif
