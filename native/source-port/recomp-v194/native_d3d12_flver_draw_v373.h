/* SPDX-License-Identifier: GPL-2.0-or-later
 * Native V373: Direct3D12 indexed offscreen draw of V371-verified packed FLVER2.
 * Experimental diagnostic, independently authored, no proprietary asset bytes.
 */
#ifndef SHYT_NATIVE_D3D12_FLVER_DRAW_V373_H
#define SHYT_NATIVE_D3D12_FLVER_DRAW_V373_H
#if !defined(_WIN32)
#error Native V373 Direct3D12 backend is Windows only
#endif
#include "native_d3d12_flver_stream_v367.h"
#include "native_flver2_vertex_decode_v371.h"
#include <cstdint>
#include <vector>
namespace shyt_native_v373 {
constexpr unsigned kFrameWidthV373=64;
constexpr unsigned kFrameHeightV373=64;
/* A single synthetic triangle-list mesh, one VB of stride 12/36/44, one
 * R16_UINT IB of three indices; Float3 position at offset zero.
 * All unsupported vertex members/indices/topologies fail closed.
 * Source must be the same immutable bytes submitted to the V367 upload.
 * The V367 upload must have been confirmed complete on this very queue.
 * The function intentionally blocks for a WARP pixel-level smoke test and
 * is NOT a production renderer, swapchain/presenter or frame-time benchmark.
 * On success rgba_out contains contiguous 64x64 RGBA8 pixels after genuine
 * D3D12 indexed drawing into an offscreen texture and GPU READBACK.
 */
bool draw_offscreen_verified_flver_v373(
    ID3D12Device* device,ID3D12CommandQueue* direct_queue,
    const ShytNativeFlver2AssetV363& source,
    const shyt_native_v367::UploadedModelV367& uploaded,
    std::vector<uint8_t>* rgba_out);
} // namespace shyt_native_v373
#endif
