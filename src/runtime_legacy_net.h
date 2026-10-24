/* SPDX-License-Identifier: GPL-2.0-or-later
 * Optional BBSC/NP online module bridge, NOT the existing encrypted visy party.
 * All APIs are no-op without BB_LEGACY_NET=1 or on non-Windows targets.
 */
#ifndef BB_RUNTIME_LEGACY_NET_H
#define BB_RUNTIME_LEGACY_NET_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif

int runtime_legacy_net_requested(void);
uintptr_t runtime_legacy_net_resolve(const char *scoped_nid);
void runtime_legacy_net_configure(const char *app0, const char *serial,
                                  const char *title, const char *version);
void runtime_legacy_net_image_mapped(uint8_t *image, uint64_t size);
void runtime_legacy_net_image_ready(uint64_t base, uint64_t size);
void runtime_legacy_net_start(void);
/* Guest-thread services with System V entrypoints; declared in runtime_thread.c. */
int32_t runtime_legacy_thread_spawn(void **thread,
    void *(__attribute__((sysv_abi)) *entry)(void *), void *arg,
    uint64_t stack_size, const char *name);
int32_t runtime_legacy_thread_join(void *thread, void **result);
void runtime_legacy_thread_exit(void *value) __attribute__((noreturn));

#ifdef __cplusplus
}
#endif
#endif
