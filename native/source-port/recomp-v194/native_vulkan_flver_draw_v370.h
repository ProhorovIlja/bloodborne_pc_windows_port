/* SPDX-License-Identifier: GPL-2.0-or-later
 * V370: native Vulkan offscreen indexed triangle rendering from a V369 GPU FLVER.
 * This only accepts a caller-declared float3 position layout and triangle list.
 * It does not infer real Bloodborne shader, vertex semantic, or topology.
 */
#ifndef SHYT_NATIVE_VULKAN_FLVER_DRAW_V370_H
#define SHYT_NATIVE_VULKAN_FLVER_DRAW_V370_H
#include "native_vulkan_flver_stream_v369.h"
#include <vulkan/vulkan.h>
#include <cstddef>
#include <cstdint>
#include <vector>
namespace shyt_native_v370 {
constexpr uint32_t kFrameWidthV370=64;
constexpr uint32_t kFrameHeightV370=64;
/* Headless/synchronous GPU draw smoke. The same device and GRAPHICS queue
 * that uploaded `model` must be used. The upload ticket must ALREADY be
 * complete (stream.ready(ticket)); its buffer must stay alive throughout.
 * `model` must describe exactly one indexed TRIANGLE_LIST face set, one
 * vertex buffer with tightly packed R32G32B32_SFLOAT at location 0/offset 0,
 * and three valid R16_UINT indices. These conditions describe our invented
 * regression fixture, NOT automatically any original Bloodborne model.
 * The SPIR-V is caller-supplied and may not be bundled from proprietary game.
 * On success returns RGBA8 UNORM 64x64 pixels, row-major, after an actual
 * render pass, indexed draw, image barrier, copy-to-buffer and GPU fence.
 * This function deliberately BLOCKS for the smoke test: it is not a
 * production frame presenter, swapchain, async render loop or scene renderer.
 */
bool draw_offscreen_flver_v370(VkPhysicalDevice physical,VkDevice device,
    VkQueue queue,uint32_t graphics_family,
    const shyt_native_v369::UploadedModelV369& model,
    const uint32_t* vertex_spirv,size_t vertex_words,
    const uint32_t* fragment_spirv,size_t fragment_words,
    std::vector<uint8_t>* rgba_out);
} // namespace shyt_native_v370
#endif
