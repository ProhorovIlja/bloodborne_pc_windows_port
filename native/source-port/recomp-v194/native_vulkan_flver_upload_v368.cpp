/* SPDX-License-Identifier: GPL-2.0-or-later
 * V368: independent Vulkan FLVER2 upload path for native Linux.
 * No Wine/Proton, D3D emulation, game code or original asset bytes.
 */
#include "native_vulkan_flver_upload_v368.h"
#include <algorithm>
#include <cstring>
#include <new>
#include <utility>

namespace shyt_native_v368 {
namespace {
constexpr uint64_t kMaxBytes=256ull*1024ull*1024ull;
constexpr uint32_t kMaxViews=4096u;
constexpr uint32_t kMaxDraws=131072u;

bool valid_range(uint64_t start,uint64_t bytes,uint64_t limit) noexcept {
    return start<=limit && bytes<=limit-start;
}
uint32_t memory_type(VkPhysicalDevice physical,uint32_t allowed,
                     VkMemoryPropertyFlags required) noexcept {
    VkPhysicalDeviceMemoryProperties props{};
    vkGetPhysicalDeviceMemoryProperties(physical,&props);
    for(uint32_t i=0;i<props.memoryTypeCount;++i) {
        if ((allowed & (1u<<i)) &&
            (props.memoryTypes[i].propertyFlags & required)==required)
            return i;
    }
    return UINT32_MAX;
}
bool allocate_buffer(
    VkPhysicalDevice physical,VkDevice device,VkDeviceSize logical_bytes,
    VkBufferUsageFlags usage,VkMemoryPropertyFlags required,
    VkBuffer* out_buffer,VkDeviceMemory* out_memory) noexcept {
    *out_buffer=VK_NULL_HANDLE;
    *out_memory=VK_NULL_HANDLE;
    if (!logical_bytes) return false;
    VkBufferCreateInfo info{VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};
    info.size=logical_bytes;
    info.usage=usage;
    info.sharingMode=VK_SHARING_MODE_EXCLUSIVE;
    if (vkCreateBuffer(device,&info,nullptr,out_buffer)!=VK_SUCCESS)
        return false;
    VkMemoryRequirements req{};
    vkGetBufferMemoryRequirements(device,*out_buffer,&req);
    const uint32_t idx=memory_type(physical,req.memoryTypeBits,required);
    if (idx==UINT32_MAX || !req.size) return false;
    VkMemoryAllocateInfo alloc{VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO};
    alloc.allocationSize=req.size;
    alloc.memoryTypeIndex=idx;
    if (vkAllocateMemory(device,&alloc,nullptr,out_memory)!=VK_SUCCESS)
        return false;
    return vkBindBufferMemory(device,*out_buffer,*out_memory,0)==VK_SUCCESS;
}
bool queue_is_graphics(VkPhysicalDevice physical,uint32_t family) {
    uint32_t count=0;
    vkGetPhysicalDeviceQueueFamilyProperties(physical,&count,nullptr);
    if (family>=count || !count || count>256) return false;
    std::vector<VkQueueFamilyProperties> props(count);
    vkGetPhysicalDeviceQueueFamilyProperties(physical,&count,props.data());
    return family<count && props[family].queueCount!=0 &&
           (props[family].queueFlags & VK_QUEUE_GRAPHICS_BIT)!=0;
}
}

void VulkanFlverUploadV368::release_staging() noexcept {
    if (!device_) return;
    if (staging_buffer_) {
        vkDestroyBuffer(device_,staging_buffer_,nullptr);
        staging_buffer_=VK_NULL_HANDLE;
    }
    if (staging_memory_) {
        vkFreeMemory(device_,staging_memory_,nullptr);
        staging_memory_=VK_NULL_HANDLE;
    }
    if (command_pool_) {
        vkDestroyCommandPool(device_,command_pool_,nullptr);
        command_pool_=VK_NULL_HANDLE;
    }
}
VulkanFlverUploadV368::~VulkanFlverUploadV368() {
    if (!device_) return;
    if (submitted_ && !completed_) (void)wait_for(UINT64_MAX);
    release_staging();
    if (fence_) vkDestroyFence(device_,fence_,nullptr);
    if (gpu_buffer_) vkDestroyBuffer(device_,gpu_buffer_,nullptr);
    if (gpu_memory_) vkFreeMemory(device_,gpu_memory_,nullptr);
}
bool VulkanFlverUploadV368::ready() const noexcept {
    if (failed_) return false;
    if (!submitted_) return true; /* valid zero-geometry model */
    if (completed_) return true;
    if (!device_ || !fence_) return false;
    return vkGetFenceStatus(device_,fence_)==VK_SUCCESS;
}
bool VulkanFlverUploadV368::wait_for(uint64_t timeout_nanoseconds) noexcept {
    if (failed_) return false;
    if (!submitted_) return true;
    if (completed_) return true;
    if (!device_ || !fence_) return false;
    const VkResult result=vkWaitForFences(
        device_,1,&fence_,VK_TRUE,timeout_nanoseconds);
    if (result==VK_TIMEOUT) return false;
    if (result!=VK_SUCCESS) {
        failed_=true; /* device loss requires caller-owned device teardown */
        return false;
    }
    completed_=true;
    release_staging();
    return true;
}

std::unique_ptr<VulkanFlverUploadV368> submit_flver_vulkan_v368(
    VkPhysicalDevice physical,VkDevice device,VkQueue queue,
    uint32_t family,const ShytNativeFlver2AssetV363* model,
    uint64_t budget) {
    if (!physical || !device || !queue || !model ||
        !queue_is_graphics(physical,family)) return nullptr;
    ShytNativeGpuUploadCountsV364 counts{};
    if (!shyt_native_flver2_gpu_requirements_v364(model,&counts) ||
        counts.vertex_buffers>kMaxViews || counts.index_buffers>kMaxViews ||
        counts.draws>kMaxDraws ||
        counts.staging_bytes_total>kMaxBytes ||
        counts.staging_bytes_total>budget)
        return nullptr;
    try {
        auto ticket=std::make_unique<VulkanFlverUploadV368>();
        ticket->device_=device;
        std::vector<ShytNativeGpuVertexSpanV364> vb(counts.vertex_buffers);
        std::vector<ShytNativeGpuIndexSpanV364> ib(counts.index_buffers);
        ticket->draws_.resize(counts.draws);
        ShytNativeGpuUploadCountsV364 plan{};
        if (!shyt_native_flver2_gpu_plan_v364(
                model,vb.data(),vb.size(),ib.data(),ib.size(),
                ticket->draws_.data(),ticket->draws_.size(),budget,&plan) ||
            plan.staging_bytes_total!=counts.staging_bytes_total)
            return nullptr;
        ticket->bytes_=plan.staging_bytes_total;
        if (!plan.staging_bytes_total) return ticket;
        ticket->vertices_.reserve(vb.size());
        for(const auto& v:vb) {
            if (!valid_range(v.staging_offset,v.bytes,plan.staging_bytes_total))
                return nullptr;
            ticket->vertices_.push_back({v.staging_offset,v.vertex_stride,
                                         v.vertex_count});
        }
        ticket->indices_.reserve(ib.size());
        for(const auto& i:ib) {
            if (!valid_range(i.staging_offset,i.bytes,plan.staging_bytes_total) ||
                (i.index_element_bytes!=2 && i.index_element_bytes!=4))
                return nullptr;
            ticket->indices_.push_back({i.staging_offset,
                i.index_element_bytes==2?VK_INDEX_TYPE_UINT16:VK_INDEX_TYPE_UINT32,
                i.index_count});
        }
        if (!allocate_buffer(physical,device,plan.staging_bytes_total,
                VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
                VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
                VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
                &ticket->staging_buffer_,&ticket->staging_memory_) ||
            !allocate_buffer(physical,device,plan.staging_bytes_total,
                VK_BUFFER_USAGE_TRANSFER_DST_BIT |
                VK_BUFFER_USAGE_TRANSFER_SRC_BIT |
                VK_BUFFER_USAGE_VERTEX_BUFFER_BIT |
                VK_BUFFER_USAGE_INDEX_BUFFER_BIT,
                VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT,
                &ticket->gpu_buffer_,&ticket->gpu_memory_))
            return nullptr;
        void* mapped=nullptr;
        if (vkMapMemory(device,ticket->staging_memory_,0,
                        plan.staging_bytes_total,0,&mapped)!=VK_SUCCESS ||
            !mapped) return nullptr;
        std::memset(mapped,0,static_cast<size_t>(plan.staging_bytes_total));
        auto* bytes=static_cast<unsigned char*>(mapped);
        bool copied=true;
        for(const auto& v:vb) {
            if (!v.bytes) continue;
            size_t written=0;
            if (!shyt_native_flver2_stage_bytes_v364(
                    model,v.source_offset,v.bytes,bytes+v.staging_offset,
                    static_cast<size_t>(plan.staging_bytes_total-v.staging_offset),
                    &written) || written!=v.bytes) {copied=false;break;}
        }
        if (copied) for(const auto& i:ib) {
            if (!i.bytes) continue;
            size_t written=0;
            if (!shyt_native_flver2_stage_bytes_v364(
                    model,i.source_offset,i.bytes,bytes+i.staging_offset,
                    static_cast<size_t>(plan.staging_bytes_total-i.staging_offset),
                    &written) || written!=i.bytes) {copied=false;break;}
        }
        vkUnmapMemory(device,ticket->staging_memory_);
        if (!copied) return nullptr;

        VkCommandPoolCreateInfo pool{VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO};
        pool.flags=VK_COMMAND_POOL_CREATE_TRANSIENT_BIT;
        pool.queueFamilyIndex=family;
        if (vkCreateCommandPool(device,&pool,nullptr,&ticket->command_pool_)!=VK_SUCCESS)
            return nullptr;
        VkCommandBufferAllocateInfo alloc{VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO};
        alloc.commandPool=ticket->command_pool_;
        alloc.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        alloc.commandBufferCount=1;
        VkCommandBuffer cmd=VK_NULL_HANDLE;
        if (vkAllocateCommandBuffers(device,&alloc,&cmd)!=VK_SUCCESS)
            return nullptr;
        VkCommandBufferBeginInfo begin{VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO};
        begin.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
        if (vkBeginCommandBuffer(cmd,&begin)!=VK_SUCCESS)
            return nullptr;
        VkBufferCopy copy{};
        copy.size=plan.staging_bytes_total;
        vkCmdCopyBuffer(cmd,ticket->staging_buffer_,ticket->gpu_buffer_,1,&copy);
        VkBufferMemoryBarrier barrier{VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER};
        barrier.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT;
        barrier.dstAccessMask=VK_ACCESS_VERTEX_ATTRIBUTE_READ_BIT |
                              VK_ACCESS_INDEX_READ_BIT;
        barrier.srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;
        barrier.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;
        barrier.buffer=ticket->gpu_buffer_;
        barrier.offset=0;
        barrier.size=VK_WHOLE_SIZE;
        vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_TRANSFER_BIT,
            VK_PIPELINE_STAGE_VERTEX_INPUT_BIT,0,0,nullptr,1,&barrier,0,nullptr);
        if (vkEndCommandBuffer(cmd)!=VK_SUCCESS) return nullptr;

        VkFenceCreateInfo fence_info{VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};
        if (vkCreateFence(device,&fence_info,nullptr,&ticket->fence_)!=VK_SUCCESS)
            return nullptr;
        VkSubmitInfo submit{VK_STRUCTURE_TYPE_SUBMIT_INFO};
        submit.commandBufferCount=1;
        submit.pCommandBuffers=&cmd;
        if (vkQueueSubmit(queue,1,&submit,ticket->fence_)!=VK_SUCCESS)
            return nullptr;
        ticket->submitted_=true; /* no fallible operations after GPU submission */
        return ticket;
    } catch (const std::bad_alloc&) {
        return nullptr;
    }
}
} // namespace shyt_native_v368
