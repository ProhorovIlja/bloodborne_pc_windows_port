/* SPDX-License-Identifier: GPL-2.0-or-later
 * V369 independent native Linux Vulkan multi-FLVER streaming.
 * No PS4 EBOOT/ELF, runtime interpreter, Wine or Proton dependency.
 */
#ifndef SHYT_NATIVE_VULKAN_FLVER_STREAM_V369_H
#define SHYT_NATIVE_VULKAN_FLVER_STREAM_V369_H
#include "native_flver2_gpu_plan_v364.h"
#include "native_fence_upload_ring_v366.h"
#include <vulkan/vulkan.h>
#include <cstdint>
#include <memory>
#include <vector>
#include <deque>

namespace shyt_native_v369 {
struct VertexViewV369 { VkDeviceSize offset=0; uint32_t stride=0, count=0; };
struct IndexViewV369 { VkDeviceSize offset=0; VkIndexType type=VK_INDEX_TYPE_UINT16; uint32_t count=0; };
/* Shared ownership means the GPU destination cannot disappear when a
 * caller drops its ticket before the queued copy finishes.
 * VkDevice must outlive both the stream and every result ticket. */
struct DeviceBufferV369 {
    VkDevice device=VK_NULL_HANDLE;
    VkBuffer buffer=VK_NULL_HANDLE;
    VkDeviceMemory memory=VK_NULL_HANDLE;
    ~DeviceBufferV369();
};
struct UploadedModelV369 {
    std::shared_ptr<DeviceBufferV369> destination;
    std::vector<VertexViewV369> vertices;
    std::vector<IndexViewV369> indices;
    std::vector<ShytNativeGpuDrawV364> draws;
    uint64_t bytes=0, ticket=0;
    VkBuffer gpu_buffer() const noexcept {
        return destination ? destination->buffer : VK_NULL_HANDLE;
    }
};
/* A portable Vulkan 1.0 implementation: per-submission VkFence rather than
 * requiring Vulkan 1.2 timeline-semaphore support.
 *
 * A single caller-owned graphics VkQueue must be used for every transfer
 * and for subsequent draw/readback operations. No internal mutexes.
 * Never free VkDevice until stream and its destination tickets are gone.
 * Nonblocking submit returns false when the staging arena is full.
 */
class VulkanFlverStreamV369 final {
public:
    VulkanFlverStreamV369(); /* out-of-line: Pending is intentionally opaque */
    VulkanFlverStreamV369(const VulkanFlverStreamV369&)=delete;
    VulkanFlverStreamV369& operator=(const VulkanFlverStreamV369&)=delete;
    ~VulkanFlverStreamV369();
    bool initialize(VkPhysicalDevice physical,VkDevice device,VkQueue queue,
                    uint32_t graphics_family,uint64_t staging_bytes) noexcept;
    bool submit_flver(const ShytNativeFlver2AssetV363* model,
                      std::unique_ptr<UploadedModelV369>* out) noexcept;
    /* Retire only signaled, ordered GPU submissions; do not block. */
    uint32_t retire_completed() noexcept;
    bool ready(uint64_t ticket) noexcept;
    bool wait_for(uint64_t ticket,uint64_t timeout_ns) noexcept;
    uint64_t used_bytes() const noexcept;
    uint32_t pending() const noexcept;
    bool device_lost() const noexcept { return lost_; }
private:
    struct Pending;
    VkPhysicalDevice physical_=VK_NULL_HANDLE;
    VkDevice device_=VK_NULL_HANDLE;
    VkQueue queue_=VK_NULL_HANDLE;
    uint32_t family_=UINT32_MAX;
    VkBuffer upload_=VK_NULL_HANDLE;
    VkDeviceMemory upload_memory_=VK_NULL_HANDLE;
    unsigned char* mapped_=nullptr;
    std::unique_ptr<shyt_native_v366::FenceUploadRingV366> ring_;
    std::deque<std::unique_ptr<Pending>> pending_;
    uint64_t next_ticket_=0, retired_ticket_=0;
    bool lost_=false;
    /* If vkQueueSubmit reports device loss or the ring cannot be
     * committed, retire/freeing becomes unsafe until device teardown. */
};
} // namespace shyt_native_v369
#endif
