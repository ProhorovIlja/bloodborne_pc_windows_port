/* Offline test-only mock BBSC module. NEVER distribute with a real game client.
 * It deliberately exports the native BbNetHost ABI v2 and no game hooks.
 */
#include "../src/runtime_legacy_host.h"
#include <stdint.h>
#include <string.h>
#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT __attribute__((visibility("default")))
#endif
static unsigned flags;
EXPORT int bbnet_init(const BbNetHost *host) {
    if (!host || host->abi != 2 || !host->app0 || !host->serial ||
        !host->title || !host->app_ver || !host->thread_spawn ||
        !host->thread_join || !host->thread_exit || !host->memory_is_mapped)
        return -1;
    if (strcmp(host->serial,"CUSA03173") ||
        strcmp(host->app_ver,"1.09") ||
        !host->memory_is_mapped(0x1234,16))
        return -2;
    flags |= 1;
    return 0;
}
EXPORT uintptr_t bbnet_resolve(const char *scoped) {
    if (!scoped || !(flags & 1)) return 0;
    if (!strcmp(scoped, "sceNetSocket")) return (uintptr_t)0x567890;
    if (!strcmp(scoped, "z123456789A#E#F")) return (uintptr_t)0x567891;
    return 0;
}
EXPORT void bbnet_image_mapped(uint8_t *p,uint64_t n) {
    if (p && n == 32) flags |= 2;
}
EXPORT void bbnet_image_ready(uint64_t p,uint64_t n) {
    if (p == 0x1234 && n == 32) flags |= 4;
}
EXPORT void bbnet_start(void) { flags |= 8; }
EXPORT unsigned bbnet_mock_status(void) { return flags; }
