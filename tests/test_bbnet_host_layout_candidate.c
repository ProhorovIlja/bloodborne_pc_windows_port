/* PE candidate ABI conformance against the EXACT pinned upstream bbnet20 header.
 * A pass proves struct/callback-layout equality, not network compatibility.
 * This test performs no network traffic and never loads a game or server.
 */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include "../src/runtime_legacy_host.h"

/* Both native host and original Linux bbnet20 define BbNetHost with the same
 * public C name. Rename only the UPSTREAM typedefs while including them so
 * compiler-visible sizes, offsets and function-pointer types can be compared.
 */
#define BbNetHost UpstreamBbNetHost
#define BbNetInitFn UpstreamBbNetInitFn
#define BbNetResolveFn UpstreamBbNetResolveFn
#define BbNetImageMappedFn UpstreamBbNetImageMappedFn
#define BbNetImageReadyFn UpstreamBbNetImageReadyFn
#define BbNetStartFn UpstreamBbNetStartFn
#include "../gpu/bbnet/bbnet.h"
#undef BbNetHost
#undef BbNetInitFn
#undef BbNetResolveFn
#undef BbNetImageMappedFn
#undef BbNetImageReadyFn
#undef BbNetStartFn

#define SAME_OFFSET(member) \
    _Static_assert(offsetof(BbNetHost, member) == offsetof(UpstreamBbNetHost, member), \
                   "bbnet20 host ABI offset changed: " #member)
_Static_assert(BBNET_HOST_ABI_VERSION == BBNET_ABI_VERSION, "host ABI version drift");
_Static_assert(sizeof(BbNetHost) == sizeof(UpstreamBbNetHost), "host ABI size drift");
_Static_assert(_Alignof(BbNetHost) == _Alignof(UpstreamBbNetHost), "host ABI alignment drift");
SAME_OFFSET(abi);
SAME_OFFSET(app0);
SAME_OFFSET(serial);
SAME_OFFSET(title);
SAME_OFFSET(app_ver);
SAME_OFFSET(thread_spawn);
SAME_OFFSET(thread_join);
SAME_OFFSET(thread_exit);
SAME_OFFSET(memory_is_mapped);

/* Calling convention drift would normally show up as an incompatible pointer
 * warning treated as an error. This includes the guest callback's SYSV ABI.
 */
static int32_t guest_spawn(void **p,
         void *(__attribute__((sysv_abi)) *entry)(void *),
         void *arg, uint64_t stack, const char *name) {
    (void)p; (void)entry; (void)arg; (void)stack; (void)name;
    return 0;
}
static int32_t guest_join(void *thread, void **result) {
    (void)thread; (void)result;
    return 0;
}
static void guest_exit(void *value) { (void)value; }
static int guest_mapped(uintptr_t addr, uint64_t size) {
    return addr != 0 && size != 0;
}
int main(void) {
    BbNetHost local = {0};
    UpstreamBbNetHost upstream = {0};
    local.thread_spawn = guest_spawn;
    upstream.thread_spawn = guest_spawn;
    local.thread_join = guest_join;
    upstream.thread_join = guest_join;
    local.thread_exit = guest_exit;
    upstream.thread_exit = guest_exit;
    local.memory_is_mapped = guest_mapped;
    upstream.memory_is_mapped = guest_mapped;
    if (local.thread_spawn != upstream.thread_spawn ||
        local.thread_join != upstream.thread_join ||
        local.thread_exit != upstream.thread_exit ||
        local.memory_is_mapped != upstream.memory_is_mapped) {
        return 1;
    }
    printf("Native Windows bbnet20 upstream ABI v%u: %zu bytes, %zu-byte alignment; all 9 fields and callback conventions match\n",
           (unsigned)BBNET_ABI_VERSION, sizeof(local), _Alignof(BbNetHost));
    return 0;
}
