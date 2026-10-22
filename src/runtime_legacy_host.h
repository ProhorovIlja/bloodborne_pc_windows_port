/* SPDX-License-Identifier: GPL-2.0-or-later
 * Host ABI exactly matching deadinside28/bloodborne_pc gpu/bbnet/bbnet.h
 * commit 8185b88d80573fa300595d5c54450183b4109935 (bbnet20).
 *
 * The upstream Linux shim is not a binary-compatible Windows module.
 * A Windows port must export these functions with the correct host
 * calling convention and honor ABI=2 before it can run a single game hook.
 */
#ifndef BB_RUNTIME_LEGACY_HOST_H
#define BB_RUNTIME_LEGACY_HOST_H
#include <stdint.h>
#include <stddef.h>
#if !defined(__x86_64__) && !defined(_M_X64)
#error BBSC native host ABI currently supports x86-64 only
#endif
#ifdef __cplusplus
extern "C" {
#endif
enum { BBNET_HOST_ABI_VERSION = 2 };
typedef struct BbNetHost {
    uint32_t abi;
    const char *app0;
    const char *serial;
    const char *title;
    const char *app_ver;
    int32_t (*thread_spawn)(void **thread,
        void *(__attribute__((sysv_abi)) *entry)(void *),
        void *argument, uint64_t stack_size, const char *name);
    int32_t (*thread_join)(void *thread, void **result);
    void (*thread_exit)(void *result);
    int (*memory_is_mapped)(uintptr_t address, uint64_t size);
} BbNetHost;
typedef int (*BbNetInitFn)(const BbNetHost *host);
typedef uintptr_t (*BbNetResolveFn)(const char *scoped_nid);
typedef void (*BbNetImageMappedFn)(uint8_t *image, uint64_t size);
typedef void (*BbNetImageReadyFn)(uint64_t base, uint64_t size);
typedef void (*BbNetStartFn)(void);

#if defined(__cplusplus)
static_assert(sizeof(BbNetHost) == 72, "bbnet ABI v2 must be 72 bytes on x64");
static_assert(offsetof(BbNetHost, thread_spawn) == 40, "bbnet callback layout drift");
#else
_Static_assert(sizeof(BbNetHost) == 72, "bbnet ABI v2 must be 72 bytes on x64");
_Static_assert(offsetof(BbNetHost, thread_spawn) == 40, "bbnet callback layout drift");
#endif
#ifdef __cplusplus
}
#endif
#endif
