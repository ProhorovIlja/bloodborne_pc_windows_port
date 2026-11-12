/* SPDX-License-Identifier: GPL-2.0-or-later
 * V368: native Linux Vulkan staging of validated FLVER2 geometry.
 * No Proton/Wine, PS4 executable, game assets or guest GPU command stream.
 */
#ifndef SHYT_NATIVE_VULKAN_FLVER_UPLOAD_V368_H
#define SHYT_NATIVE_VULKAN_FLVER_UPLOAD_V368_H
#include "native_flver2_gpu_plan_v364.h"
#include <vulkan/vulkan.h>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <vector>

namespace shyt_native_v368 {
struct IndexViewV368 {
    VkDeviceSize offset=0;
    VkIndexType type=VK_INDEX_TYPE_UINT16;
    uint32_t index_count=0;
};
struct VertexViewV368 {
    VkDeviceSize offset=0;
    uint32_t stride=0;
    uint32_t vertex_count=0;
};

/* A ticket owns its destination buffer and temporary upload objects.
 * The VkDevice (and queue) belong to the caller and MUST outlive ticket.
 * No Vulkan resources may be consumed until ready()/wait_for() succeeds.
 * Destruction of an unfinished ticket waits: retire on a worker thread,
 * NEVER destroy live upload tickets on the latency-critical render loop.
 */
class VulkanFlverUploadV368 final {
public:
    VulkanFlverUploadV368()=default;
    VulkanFlverUploadV368(const VulkanFlverUploadV368&)=delete;
    VulkanFlverUploadV368& operator=(const VulkanFlverUploadV368&)=delete;
    ~VulkanFlverUploadV368();
    bool ready() const noexcept;
    bool wait_for(uint64_t timeout_nanoseconds) noexcept;
    VkBuffer gpu_buffer() const noexcept {return gpu_buffer_;}
    uint64_t uploaded_bytes() const noexcept {return bytes_;}
    bool device_lost() const noexcept {return failed_;}
    const std::vector<VertexViewV368>& vertices() const noexcept {return vertices_;}
    const std::vector<IndexViewV368>& indices() const noexcept {return indices_;}
    const std::vector<ShytNativeGpuDrawV364>& draws() const noexcept {return draws_;}
private:
    friend std::unique_ptr<VulkanFlverUploadV368> submit_flver_vulkan_v368(
        VkPhysicalDevice,VkDevice,VkQueue,uint32_t,
        const ShytNativeFlver2AssetV363*,uint64_t);
    void release_staging() noexcept;
    VkDevice device_=VK_NULL_HANDLE;
    VkBuffer staging_buffer_=VK_NULL_HANDLE;
    VkDeviceMemory staging_memory_=VK_NULL_HANDLE;
    VkBuffer gpu_buffer_=VK_NULL_HANDLE;
    VkDeviceMemory gpu_memory_=VK_NULL_HANDLE;
    VkCommandPool command_pool_=VK_NULL_HANDLE;
    VkFence fence_=VK_NULL_HANDLE;
    std::vector<VertexViewV368> vertices_;
    std::vector<IndexViewV368> indices_;
    std::vector<ShytNativeGpuDrawV364> draws_;
    uint64_t bytes_=0;
    bool submitted_=false,completed_=false,failed_=false;
};
/* Vulkan 1.0-compatible, single-resource transfer. Queue family must
 * support GRAPHICS, physical device and logical device must match.
 * Attempts a HOST_VISIBLE|HOST_COHERENT upload and DEVICE_LOCAL destination
 * memory type; refuses unsupported hardware rather than accessing memory
 * without an explicit flush. Both memories are private to this ticket.
 *
 * This is a proof of native Linux Vulkan transfer, not yet the pooled
 * V367-style Vulkan upload ring or a full renderer.
 */
std::unique_ptr<VulkanFlverUploadV368> submit_flver_vulkan_v368(
    VkPhysicalDevice physical,VkDevice device,VkQueue graphics_queue,
    uint32_t graphics_family,const ShytNativeFlver2AssetV363* model,
    uint64_t staging_budget_bytes);
} // namespace shyt_native_v368
#endif
