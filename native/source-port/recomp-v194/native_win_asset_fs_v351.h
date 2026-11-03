/* SPDX-License-Identifier: GPL-2.0-or-later
 * V351: REAL WIN32 read-only Bloodborne asset mount for a future native PC port.
 * Maps /dvdroot_ps4/... to the owner's own extracted dvdroot_ps4 tree.
 * No emulator, ELF/EBOOT loader, game bytes, server or network access.
 * PS4 guest ABI and engine file-handle semantics are NOT implemented here.
 */
#ifndef SHYT_NATIVE_WIN_ASSET_FS_V351_H
#define SHYT_NATIVE_WIN_ASSET_FS_V351_H
#include <stddef.h>
#include <stdint.h>
#include <wchar.h>

#define SHYT_WIN_ASSET_PATH_CAP_V351 4096u
#define SHYT_WIN_ASSET_MAX_READ_V351 (16u * 1024u * 1024u)
typedef struct ShytNativeWinAssetRootV351 {
    wchar_t canonical_prefix[SHYT_WIN_ASSET_PATH_CAP_V351];
    size_t prefix_chars;
    int mounted;
} ShytNativeWinAssetRootV351;

#ifdef __cplusplus
extern "C" {
#endif
/* root_dir: local owner-owned CUSA03173/dvdroot_ps4 directory. */
int shyt_native_win_asset_mount_v351(ShytNativeWinAssetRootV351 *root,
                                      const wchar_t *root_dir);
/* Logical path must be absolute /dvdroot_ps4/name.ext with ASCII-only
 * canonical components. No .., hidden ADS, devices, links or writes.
 * Returns 1 on clean read/EOF, 0 on refusal. On failure *got is
 * zero; when the OS itself aborts a read, caller must discard the output
 * buffer. Offset is an absolute file offset.
 * This opens one native Windows file handle per call (safe for threads,
 * not yet optimized for the actual game's sustained streaming load).
 */
int shyt_native_win_asset_read_at_v351(
    const ShytNativeWinAssetRootV351 *root, const char *logical_path,
    uint64_t offset, void *out, size_t max_bytes, size_t *got);
/* V352: native Windows I/O handle retained across asset stream reads.
 * A stream belongs to one caller and must not be copied. Concurrent reads
 * from the SAME stream are supported via distinct OVERLAPPED file offsets;
 * the caller must not close the handle while any read is in progress.
 * Read-only and strictly rooted in the mount from V351.
 */
typedef struct ShytNativeWinAssetStreamV352 {
    void *native_handle;
    uint64_t file_size;
    int open;
} ShytNativeWinAssetStreamV352;

int shyt_native_win_asset_stream_open_v352(
    const ShytNativeWinAssetRootV351 *root, const char *logical_path,
    ShytNativeWinAssetStreamV352 *stream);
int shyt_native_win_asset_stream_read_v352(
    const ShytNativeWinAssetStreamV352 *stream,
    uint64_t offset, void *out, size_t max_bytes, size_t *got);
void shyt_native_win_asset_stream_close_v352(
    ShytNativeWinAssetStreamV352 *stream);
#ifdef __cplusplus
}
#endif
#endif
