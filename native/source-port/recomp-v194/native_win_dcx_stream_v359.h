/* SPDX-License-Identifier: GPL-2.0-or-later
 * Native Windows game resource streaming for Bloodborne / Dark Souls 3.
 * V359: read .dcx via actual Win32 owner-only root with bounded zlib
 * chunks (64 KiB compressed input), without copying whole compressed
 * containers into memory. No EBOOT and no PS4 runtime.
 */
#ifndef SHYT_NATIVE_WIN_DCX_STREAM_V359_H
#define SHYT_NATIVE_WIN_DCX_STREAM_V359_H
#include "native_win_asset_fs_v351.h"
#include <stddef.h>
#ifdef __cplusplus
extern "C" {
#endif
/* Caller provides output buffer capacity >= known uncompressed size
 * in header (max 512MiB). No guest-derived malloc by this service.
 * On refusal written=0; output buffer becomes untrusted after any
 * zlib error. No file path, filename or payload is logged.
 */
int shyt_native_win_dcx_stream_inflate_v359(
    const ShytNativeWinAssetRootV351 *root,
    const char *logical_path, void *out, size_t out_capacity,
    size_t *written);
#ifdef __cplusplus
}
#endif
#endif
