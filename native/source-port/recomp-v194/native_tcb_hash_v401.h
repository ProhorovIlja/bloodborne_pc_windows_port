/* SPDX-License-Identifier: GPL-2.0-or-later
 * Native V401: deliberately BOUNDED synthetic 64-bit TCB MOV/RET
 * code hash probe. This is not a general x86 decoder, original-game
 * executable hash, or guest interpreter.
 *
 * For exactly the invented 10-byte absolute MOV r64, FS/GS:[disp32];
 * RET shapes, apply pinned public bbcpu's special FNV-1a64 normalization
 * iff source mem is FS:[0] or GS:[disp]. Other opcode shapes fail
 * closed instead of falling back to an unsafe generic hash.
 */
#ifndef SHYT_NATIVE_TCB_HASH_V401_H
#define SHYT_NATIVE_TCB_HASH_V401_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
int shyt_native_hash_tcb_probe_v401(const uint8_t *code,size_t length,
                                     uint64_t *out);
#ifdef __cplusplus
}
#endif
#endif
