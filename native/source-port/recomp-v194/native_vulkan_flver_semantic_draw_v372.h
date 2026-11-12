/* SPDX-License-Identifier: GPL-2.0-or-later
 * V372: validate real FLVER2 member semantics before a Vulkan indexed draw.
 * No proprietary data, no runtime EBOOT/ELF, Wine, Proton or emulator.
 */
#ifndef SHYT_NATIVE_VULKAN_FLVER_SEMANTIC_DRAW_V372_H
#define SHYT_NATIVE_VULKAN_FLVER_SEMANTIC_DRAW_V372_H
#include "native_vulkan_flver_draw_v370.h"
#include "native_flver2_vertex_decode_v371.h"
#include <vector>
#include <cstdint>
#include <cstddef>
namespace shyt_native_v372 {

/* Narrow proof: raw FLVER2 V371-verified 12/36/44-byte vertices are bound
 * DIRECTLY to the GPU (zero intermediate vertex repacking). Position must
 * be Float3 at offset 0; normals, UVs, bones, colors are not used by this
 * diagnostic shader. A single mesh/face-set, exactly 3 triangle-list
 * R16 indices and 3 vertices are required.
 *
 * source MUST be the same immutable FLVER2 bytes used for V369 GPU upload.
 * This API validates source vs GPU metadata but does NOT hash/attest
 * content identity. Caller must wait for stream.ready(model.ticket) and
 * keep GPU destination and VkDevice alive through this blocking smoke.
 * Not a production renderer, no skinning/material mapping yet.
 */
bool draw_offscreen_verified_flver_v372(
    VkPhysicalDevice physical,VkDevice device,VkQueue queue,
    uint32_t graphics_family,
    const ShytNativeFlver2AssetV363& original,
    const shyt_native_v369::UploadedModelV369& uploaded,
    const uint32_t* vertex_spirv,size_t vertex_words,
    const uint32_t* fragment_spirv,size_t fragment_words,
    std::vector<uint8_t>* rgba_out);
} // namespace shyt_native_v372
#endif
