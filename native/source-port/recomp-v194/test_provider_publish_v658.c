/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "provider_publish_v658.h"
#include <assert.h>
#include <stdio.h>

struct fixture { uintptr_t dependency; uint32_t flags; unsigned gets, queries; int ok; };
static uintptr_t get(void *p) {
    struct fixture *f = p;
    ++f->gets;
    return f->dependency;
}
static int query(void *p, uintptr_t dep, uint32_t *out) {
    struct fixture *f = p;
    assert(dep == f->dependency);
    ++f->queries;
    *out = f->flags;
    return f->ok;
}
int main(void) {
    unsigned char table;
    const uintptr_t binding = (uintptr_t)&table;
    for (unsigned i = 0; i < 256; ++i) {
        _Alignas(8) unsigned char bytes[96], expect[96];
        struct bb_provider_cache_v658 cell = {0};
        struct fixture f = {(uintptr_t)&f, 0x73, 0, 0, 1};
        const struct bb_provider_calls_v658 calls = {&f, get, query};
        memset(bytes, (int)i, sizeof bytes);
        memcpy(expect, bytes, sizeof expect);
        f.flags = 0x53;
        assert(!bb_provider_publish_v658(&cell,bytes,80,binding,&calls));
        f.flags = 0x73;
        f.ok = 0;
        assert(!bb_provider_publish_v658(&cell,bytes,80,binding,&calls));
        f.ok = 1;
        assert(!bb_provider_publish_v658(&cell,bytes,79,binding,&calls));
        assert(!memcmp(bytes,expect,sizeof bytes) && !cell.published);
        memcpy(expect,&binding,8);
        memset(expect+8,0,16);
        memset(expect+32,0,48);
        memcpy(expect+56,&f.dependency,8);
        assert(bb_provider_publish_v658(&cell,bytes,80,binding,&calls)==(uintptr_t)bytes);
        assert(bb_provider_publish_v658(&cell,NULL,0,0,NULL)==(uintptr_t)bytes);
        assert(!memcmp(bytes,expect,sizeof bytes) && f.gets==3 && f.queries==3);
    }
    puts("256 cold, warm and rejected publication fixtures OK");
    return 0;
}
