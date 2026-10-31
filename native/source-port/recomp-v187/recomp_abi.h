/* v187: Windows/Linux dynamic ABI smoke-test for bloodborne-recomp (GPL-2.0-or-later).
 * This exact external-layout slice matches upstream src/recomp/rc.h API v4.
 * No PS4 game code, eboot.bin or platform compatibility implementation included.
 */
#ifndef BB_V187_RECOMP_ABI_H
#define BB_V187_RECOMP_ABI_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
#define BB_RECOMP_API_VERSION 4u
#define BB_RECOMP_INIT "bb_recomp_init"
typedef struct BbCpu BbCpu;
typedef void (*RcFn)(BbCpu *cpu);
typedef struct {
    uint32_t version;
    uint64_t image_base;
    uint64_t (*step)(BbCpu *cpu);
    void (*call)(BbCpu *cpu, uint64_t target, uint64_t next);
    void (*tail)(BbCpu *cpu);
    void (*bail)(BbCpu *cpu, uint64_t entry_rsp);
    void (*trace)(uint64_t offset, const uint64_t r[16], const BbCpu *cpu);
} RcApi;
typedef struct { uint64_t offset, size, hash; RcFn fn; RcFn *direct; } RcFunction;
typedef const RcFunction *(*RcInit)(const RcApi *api, size_t *count);
#ifdef _WIN32
#define RC_EXPORT __declspec(dllexport)
#else
#define RC_EXPORT __attribute__((visibility("default")))
#endif
#ifdef __cplusplus
}
#endif
#endif
