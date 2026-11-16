/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <stdint.h>

/* Route data is supplied by the private offline planner. Guest addresses
 * are never cast to host pointers. read64 must perform bounded LE loads. */
struct startup_getter_v465 { uint64_t site, receiver, table, target; unsigned lane; };
typedef int (*read64_v465)(void *, uint64_t, uint64_t *);
int native_startup_getter_v465(const struct startup_getter_v465 *r,
    uint64_t site, uint64_t receiver, read64_v465 read64, void *mem, uint64_t *rax) {
    uint64_t table, target, value;
    if (!r || !read64 || !rax || !site || site != r->site || !receiver ||
        receiver != r->receiver || !r->table || !r->target || r->lane > 1) return 0;
    const uint64_t slot = 16u + 8u*r->lane, field = 64u + 8u*r->lane;
    if (r->table > UINT64_MAX - slot - 7 || receiver > UINT64_MAX - field - 7) return 0;
    if (!read64(mem, receiver, &table) || table != r->table ||
        !read64(mem, table+slot, &target) || target != r->target ||
        !read64(mem, receiver+field, &value)) return 0;
    *rax = value;
    return 1;
}

#ifdef NATIVE_STARTUP_GETTER_V465_TEST
struct fixture { uint64_t table, targets[2], fields[2], deny; unsigned reads; };
static int rd(void *mem, uint64_t addr, uint64_t *out) {
    struct fixture *f = mem;
    ++f->reads;
    if (addr == f->deny) return 0;
    switch (addr) {
        case 256: *out=f->table; return 1;
        case 528: *out=f->targets[0]; return 1;
        case 536: *out=f->targets[1]; return 1;
        case 320: *out=f->fields[0]; return 1;
        case 328: *out=f->fields[1]; return 1;
        default: return 0;
    }
}
int main(void) {
    for (unsigned lane=0; lane<2; ++lane) {
        struct startup_getter_v465 r = {10+lane,256,512,100+lane,lane};
        struct fixture f = {512,{100,101},{0,UINT64_MAX},0,0};
        uint64_t ret = 7;
        if (!native_startup_getter_v465(&r,r.site,256,rd,&f,&ret) ||
            ret != f.fields[lane] || f.reads != 3) return 1;
        ret=7; f.reads=0;
        if (native_startup_getter_v465(&r,12,256,rd,&f,&ret) ||
            native_startup_getter_v465(&r,r.site,257,rd,&f,&ret) || f.reads) return 2;
        const uint64_t deny[] = {256,528+8*lane,320+8*lane};
        for (unsigned i=0;i<3;++i) {
            f.deny=deny[i]; f.reads=0;
            if (native_startup_getter_v465(&r,r.site,256,rd,&f,&ret) ||
                f.reads != i+1 || ret != 7) return 3;
        }
        f.deny=0; f.table=513; f.reads=0;
        if (native_startup_getter_v465(&r,r.site,256,rd,&f,&ret) || f.reads!=1) return 4;
        f.table=512; f.targets[lane]^=16; f.reads=0;
        if (native_startup_getter_v465(&r,r.site,256,rd,&f,&ret) || f.reads!=2) return 5;
        f.reads=0; r.table=UINT64_MAX-17;
        if (native_startup_getter_v465(&r,r.site,256,rd,&f,&ret) || f.reads) return 6;
        r.table=512; r.receiver=UINT64_MAX-60;
        if (native_startup_getter_v465(&r,r.site,r.receiver,rd,&f,&ret) || f.reads) return 7;
        r.receiver=256; r.lane=2;
        if (native_startup_getter_v465(&r,r.site,256,rd,&f,&ret) || f.reads || ret!=7) return 8;
    }
    return 0;
}
#endif
