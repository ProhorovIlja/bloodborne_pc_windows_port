/* SPDX-License-Identifier: GPL-2.0-or-later
 * V360: platform-neutral, bounded DCX_DFLT streaming decode.
 * No game executables, PS4 ABI, filesystem paths, or game-owned data.
 */
#ifndef SHYT_NATIVE_DCX_DFLT_STREAM_CORE_V360_H
#define SHYT_NATIVE_DCX_DFLT_STREAM_CORE_V360_H
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
/* Reader returns 1 only after filling EXACTLY count bytes at offset.
 * No seek state is shared. The caller remains responsible for keeping
 * its underlying file or immutable memory alive until this call returns.
 */
typedef int (*ShytNativeDcxReadExactV360)(
    void *context, uint64_t offset, void *destination, size_t count);
/* Decodes exactly one supported zlib-wrapped DCX_DFLT member in blocks
 * <=64 KiB, plus at most 15 zero padding bytes. file_size and output
 * capacity are untrusted and must pass the V354 bounded-envelope checks.
 * Failure sets *written=0; the destination buffer may have been modified
 * and MUST NOT be consumed after failure. No path or asset content logged.
 */
int shyt_native_dcx_dflt_stream_core_v360(
    ShytNativeDcxReadExactV360 read_exact, void *context,
    uint64_t file_size, void *output, size_t output_capacity,
    size_t *written);
#ifdef __cplusplus
}
#endif
#endif
