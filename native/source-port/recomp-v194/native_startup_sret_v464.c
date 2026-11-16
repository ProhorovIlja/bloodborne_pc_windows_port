/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <stddef.h>
#include <stdint.h>

/* Private, verified routes are supplied by the caller, never compiled in here.
 * Use only with single-threaded startup guest memory. Callbacks must perform
 * bounded guest accesses; a failed write must leave memory unchanged.
 * Route targets are guest IDs only: this function never jumps to one.
 */
struct startup_route_v464 {
    uint64_t sites[2], receiver, table, target;
    uint32_t result;
};
typedef int (*read64_v464)(void *, uint64_t, uint64_t *);
typedef int (*write32_v464)(void *, uint64_t, uint32_t);

int native_startup_sret_v464(const struct startup_route_v464 *route,
                            uint64_t site, uint64_t receiver, uint64_t out,
                            read64_v464 read64, write32_v464 write32,
                            void *memory, uint64_t *return_reg) {
    uint64_t table, target;
    if (!route || !read64 || !write32 || !return_reg ||
        !route->sites[0] || !route->sites[1] ||
        route->sites[0] == route->sites[1] ||
        (site != route->sites[0] && site != route->sites[1]) ||
        !receiver || receiver != route->receiver || receiver > UINT64_MAX - 7 ||
        !out || out > UINT64_MAX - 3 || !route->table ||
        route->table > UINT64_MAX - 39 || !route->target) return 0;
    if (!read64(memory, receiver, &table) || table != route->table ||
        !read64(memory, table + 32, &target) || target != route->target ||
        !write32(memory, out, route->result)) return 0;
    *return_reg = out;
    return 1;
}

#ifdef NATIVE_STARTUP_SRET_V464_TEST
#include <string.h>
struct fixture { uint64_t table, target; unsigned char stack[8]; unsigned writes; };
static int rd(void *mem, uint64_t addr, uint64_t *out) {
    struct fixture *f = mem;
    if (addr == 64) *out = f->table;
    else if (addr == 160) *out = f->target;
    else return 0;
    return 1;
}
static int wr(void *mem, uint64_t addr, uint32_t value) {
    struct fixture *f = mem;
    if (addr != 257) return 0;
    for (unsigned i = 0; i < 4; ++i) f->stack[1+i] = (unsigned char)(value >> (8*i));
    ++f->writes;
    return 1;
}
int main(void) {
    const struct startup_route_v464 r = {{1,2}, 64,128,192,UINT32_C(0xaabbccdd)};
    struct fixture f = {128,192,{0},0};
    uint64_t ret = 0;
    const unsigned char expected[8] = {255,221,204,187,170,255,255,255};
    memset(f.stack, 255, sizeof f.stack);
    for (uint64_t i = 1; i <= 2; ++i)
        if (!native_startup_sret_v464(&r,i,64,257,rd,wr,&f,&ret) ||
            ret != 257 || memcmp(f.stack, expected, sizeof f.stack)) return 1;
    ret = 17;
    if (native_startup_sret_v464(&r,3,64,257,rd,wr,&f,&ret) ||
        native_startup_sret_v464(&r,1,65,257,rd,wr,&f,&ret) ||
        native_startup_sret_v464(&r,1,64,258,rd,wr,&f,&ret) ||
        native_startup_sret_v464(&r,1,64,UINT64_MAX-2,rd,wr,&f,&ret)) return 2;
    f.table = 129;
    if (native_startup_sret_v464(&r,1,64,257,rd,wr,&f,&ret)) return 3;
    f.table = 128; f.target = 193;
    if (native_startup_sret_v464(&r,1,64,257,rd,wr,&f,&ret) ||
        ret != 17 || f.writes != 2 || memcmp(f.stack, expected, sizeof f.stack)) return 4;
    return 0;
}
#endif
