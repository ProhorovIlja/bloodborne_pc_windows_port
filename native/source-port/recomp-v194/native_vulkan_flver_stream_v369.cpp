/* SPDX-License-Identifier: GPL-2.0-or-later
 * Native Vulkan 1.0 persistent staging for user-owned FLVER2 resources.
 * Device-local buffers, ordered fence retirement, no emulator dependencies.
 */
#include "native_vulkan_flver_stream_v369.h"
#include <cstring>
#include <new>
#include <utility>

namespace shyt_native_v369 {
namespace {
constexpr uint32_t kMaxViews=4096u, kMaxDraws=131072u;

bool range_v369(uint64_t start,uint64_t bytes,uint64_t total) noexcept {
    return start<=total && bytes<=total-start;
}
uint32_t memory_type_v369(VkPhysicalDevice physical,uint32_t bits,
                          VkMemoryPropertyFlags required) noexcept {
    VkPhysicalDeviceMemoryProperties props{};
    vkGetPhysicalDeviceMemoryProperties(physical,&props);
    for (uint32_t i=0;i<props.memoryTypeCount;++i)
        if ((bits & (1u<<i)) &&
            (props.memoryTypes[i].propertyFlags & required)==required)
            return i;
    return UINT32_MAX;
}
bool create_buffer_v369(VkPhysicalDevice physical,VkDevice device,
    uint64_t size,VkBufferUsageFlags usage,VkMemoryPropertyFlags properties,
    VkBuffer* buffer,VkDeviceMemory* memory) noexcept {
    *buffer=VK_NULL_HANDLE;
    *memory=VK_NULL_HANDLE;
    if (!size) return false;
    VkBufferCreateInfo desc{};
    desc.sType=VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
    desc.size=size;
    desc.usage=usage;
    desc.sharingMode=VK_SHARING_MODE_EXCLUSIVE;
    if (vkCreateBuffer(device,&desc,nullptr,buffer)!=VK_SUCCESS)
        return false;
    VkMemoryRequirements required{};
    vkGetBufferMemoryRequirements(device,*buffer,&required);
    const uint32_t idx=memory_type_v369(
        physical,required.memoryTypeBits,properties);
    if (idx==UINT32_MAX || !required.size) return false;
    VkMemoryAllocateInfo alloc{};
    alloc.sType=VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    alloc.allocationSize=required.size;
    alloc.memoryTypeIndex=idx;
    if (vkAllocateMemory(device,&alloc,nullptr,memory)!=VK_SUCCESS)
        return false;
    return vkBindBufferMemory(device,*buffer,*memory,0)==VK_SUCCESS;
}
bool valid_queue_family_v369(VkPhysicalDevice physical,uint32_t family) noexcept {
    uint32_t count=0;
    vkGetPhysicalDeviceQueueFamilyProperties(physical,&count,nullptr);
    if (!count || count>256 || family>=count) return false;
    VkQueueFamilyProperties props[256]{};
    vkGetPhysicalDeviceQueueFamilyProperties(physical,&count,props);
    return family<count && props[family].queueCount>0 &&
        (props[family].queueFlags & VK_QUEUE_GRAPHICS_BIT)!=0;
}
} // namespace

DeviceBufferV369::~DeviceBufferV369() {
    if (device && buffer) vkDestroyBuffer(device,buffer,nullptr);
    if (device && memory) vkFreeMemory(device,memory,nullptr);
}
struct VulkanFlverStreamV369::Pending {
    VkDevice device=VK_NULL_HANDLE;
    VkFence fence=VK_NULL_HANDLE;
    VkCommandPool command_pool=VK_NULL_HANDLE;
    uint64_t ticket=0;
    std::shared_ptr<DeviceBufferV369> destination;
    ~Pending() {
        if (device && command_pool)
            vkDestroyCommandPool(device,command_pool,nullptr);
        if (device && fence) vkDestroyFence(device,fence,nullptr);
    }
};
VulkanFlverStreamV369::VulkanFlverStreamV369()=default;
VulkanFlverStreamV369::~VulkanFlverStreamV369() {
    if (!device_) return;
    if (!pending_.empty()) {
        /* This destructor can block, and is for shutdown on an asset worker
         * thread. Application MUST keep VkDevice alive until it returns. */
        (void)vkQueueWaitIdle(queue_);
    }
    pending_.clear();
    if (mapped_ && upload_memory_)
        vkUnmapMemory(device_,upload_memory_);
    if (upload_) vkDestroyBuffer(device_,upload_,nullptr);
    if (upload_memory_) vkFreeMemory(device_,upload_memory_,nullptr);
}
bool VulkanFlverStreamV369::initialize(
    VkPhysicalDevice physical,VkDevice device,VkQueue queue,
    uint32_t family,uint64_t capacity) noexcept {
    if (device_ || !physical || !device || !queue ||
        !valid_queue_family_v369(physical,family) ||
        capacity<4 ||
        capacity>shyt_native_v366::FenceUploadRingV366::kMaxCapacity ||
        (capacity&3u)) return false;
    try {
        auto ring=std::make_unique<shyt_native_v366::FenceUploadRingV366>(capacity);
        if (!ring->valid()) return false;
        VkBuffer upload=VK_NULL_HANDLE;
        VkDeviceMemory memory=VK_NULL_HANDLE;
        if (!create_buffer_v369(physical,device,capacity,
              VK_BUFFER_USAGE_TRANSFER_SRC_BIT,
              VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT |
              VK_MEMORY_PROPERTY_HOST_COHERENT_BIT,
              &upload,&memory)) {
            if (upload) vkDestroyBuffer(device,upload,nullptr);
            if (memory) vkFreeMemory(device,memory,nullptr);
            return false;
        }
        void* mapped=nullptr;
        if (vkMapMemory(device,memory,0,capacity,0,&mapped)!=VK_SUCCESS ||
            !mapped) {
            vkDestroyBuffer(device,upload,nullptr);
            vkFreeMemory(device,memory,nullptr);
            return false;
        }
        physical_=physical;
        device_=device;
        queue_=queue;
        family_=family;
        upload_=upload;
        upload_memory_=memory;
        mapped_=static_cast<unsigned char*>(mapped);
        ring_=std::move(ring);
        return true;
    } catch(const std::bad_alloc&) { return false; }
}
uint64_t VulkanFlverStreamV369::used_bytes() const noexcept {
    return ring_?ring_->used():0;
}
uint32_t VulkanFlverStreamV369::pending() const noexcept {
    return static_cast<uint32_t>(pending_.size());
}
uint32_t VulkanFlverStreamV369::retire_completed() noexcept {
    if (!ring_ || lost_) return 0;
    uint32_t retired=0;
    while(!pending_.empty()) {
        const VkResult status=vkGetFenceStatus(device_,pending_.front()->fence);
        if (status==VK_NOT_READY) break;
        if (status!=VK_SUCCESS) { lost_=true; break; }
        const uint64_t completed=pending_.front()->ticket;
        retired+=ring_->retire(completed);
        retired_ticket_=completed;
        pending_.pop_front();
    }
    return retired;
}
bool VulkanFlverStreamV369::ready(uint64_t ticket) noexcept {
    if (!ring_ || lost_) return false;
    if (ticket==0) return true; /* empty model */
    if (ticket>next_ticket_) return false;
    retire_completed();
    return !lost_ && ticket<=retired_ticket_;
}
bool VulkanFlverStreamV369::wait_for(
    uint64_t ticket,uint64_t timeout_ns) noexcept {
    if (!ring_ || lost_ || ticket>next_ticket_) return false;
    if (ready(ticket)) return true;
    VkFence requested=VK_NULL_HANDLE;
    for(const auto& pending:pending_)
        if (pending->ticket==ticket) {requested=pending->fence;break;}
    if (!requested) return false;
    const VkResult result=vkWaitForFences(
        device_,1,&requested,VK_TRUE,timeout_ns);
    if (result==VK_TIMEOUT) return false;
    if (result!=VK_SUCCESS) { lost_=true; return false; }
    retire_completed();
    return !lost_ && ticket<=retired_ticket_;
}
bool VulkanFlverStreamV369::submit_flver(
    const ShytNativeFlver2AssetV363* model,
    std::unique_ptr<UploadedModelV369>* out) noexcept {
    if (!out) return false;
    out->reset();
    if (!ring_ || !mapped_ || !device_ || !queue_ || lost_ || !model ||
        next_ticket_>=UINT64_MAX-1) return false;
    retire_completed();
    if (lost_) return false;
    ShytNativeGpuUploadCountsV364 counts{};
    if (!shyt_native_flver2_gpu_requirements_v364(model,&counts) ||
        counts.vertex_buffers>kMaxViews ||
        counts.index_buffers>kMaxViews ||
        counts.draws>kMaxDraws ||
        counts.staging_bytes_total>ring_->capacity())
        return false;
    shyt_native_v366::RingSliceV366 slice{};
    bool reserved=false;
    try {
        auto result=std::make_unique<UploadedModelV369>();
        std::vector<ShytNativeGpuVertexSpanV364> vb(counts.vertex_buffers);
        std::vector<ShytNativeGpuIndexSpanV364> ib(counts.index_buffers);
        result->draws.resize(counts.draws);
        ShytNativeGpuUploadCountsV364 plan{};
        if (!shyt_native_flver2_gpu_plan_v364(
              model,vb.data(),vb.size(),ib.data(),ib.size(),
              result->draws.data(),result->draws.size(),
              ring_->capacity(),&plan) ||
            plan.staging_bytes_total!=counts.staging_bytes_total)
            return false;
        result->bytes=plan.staging_bytes_total;
        if (!plan.staging_bytes_total) {
            *out=std::move(result);
            return true;
        }
        result->vertices.reserve(vb.size());
        for(const auto& v:vb) {
            if (!range_v369(v.staging_offset,v.bytes,plan.staging_bytes_total))
                return false;
            result->vertices.push_back({v.staging_offset,
                                        v.vertex_stride,v.vertex_count});
        }
        result->indices.reserve(ib.size());
        for(const auto& i:ib) {
            if (!range_v369(i.staging_offset,i.bytes,plan.staging_bytes_total) ||
                (i.index_element_bytes!=2 && i.index_element_bytes!=4))
                return false;
            result->indices.push_back({i.staging_offset,
                i.index_element_bytes==2?
                    VK_INDEX_TYPE_UINT16:VK_INDEX_TYPE_UINT32,
                i.index_count});
        }
        auto gpu=std::make_shared<DeviceBufferV369>();
        gpu->device=device_;
        if (!create_buffer_v369(physical_,device_,plan.staging_bytes_total,
                VK_BUFFER_USAGE_TRANSFER_DST_BIT |
                VK_BUFFER_USAGE_TRANSFER_SRC_BIT |
                VK_BUFFER_USAGE_VERTEX_BUFFER_BIT |
                VK_BUFFER_USAGE_INDEX_BUFFER_BIT,
                VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT,
                &gpu->buffer,&gpu->memory)) return false;
        auto pending=std::make_unique<Pending>();
        pending->device=device_;
        pending->destination=gpu;
        pending->ticket=next_ticket_+1;
        VkCommandPoolCreateInfo pool{};
        pool.sType=VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;
        pool.flags=VK_COMMAND_POOL_CREATE_TRANSIENT_BIT;
        pool.queueFamilyIndex=family_;
        if (vkCreateCommandPool(device_,&pool,nullptr,
                &pending->command_pool)!=VK_SUCCESS) return false;
        VkCommandBufferAllocateInfo cmd_alloc{};
        cmd_alloc.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
        cmd_alloc.commandPool=pending->command_pool;
        cmd_alloc.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        cmd_alloc.commandBufferCount=1;
        VkCommandBuffer cmd=VK_NULL_HANDLE;
        if (vkAllocateCommandBuffers(
                device_,&cmd_alloc,&cmd)!=VK_SUCCESS) return false;
        VkCommandBufferBeginInfo begin{};
        begin.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
        begin.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
        if (vkBeginCommandBuffer(cmd,&begin)!=VK_SUCCESS) return false;
        VkFenceCreateInfo fence_desc{};
        fence_desc.sType=VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;
        if (vkCreateFence(device_,&fence_desc,nullptr,
                &pending->fence)!=VK_SUCCESS) return false;
        /* All fallible C++ allocations and Vulkan resource creation are
         * complete before reserving a slice or submitting GPU commands. */
        if (!ring_->reserve(plan.staging_bytes_total,4,&slice)) return false;
        reserved=true;
        auto* destination=mapped_+slice.offset;
        std::memset(destination,0,static_cast<size_t>(slice.bytes));
        bool staged=true;
        for(const auto& v:vb) {
            if (!v.bytes) continue;
            size_t written=0;
            if (!shyt_native_flver2_stage_bytes_v364(
                  model,v.source_offset,v.bytes,
                  destination+v.staging_offset,
                  static_cast<size_t>(slice.bytes-v.staging_offset),
                  &written) || written!=v.bytes) {staged=false;break;}
        }
        if (staged) for(const auto& i:ib) {
            if (!i.bytes) continue;
            size_t written=0;
            if (!shyt_native_flver2_stage_bytes_v364(
                  model,i.source_offset,i.bytes,
                  destination+i.staging_offset,
                  static_cast<size_t>(slice.bytes-i.staging_offset),
                  &written) || written!=i.bytes) {staged=false;break;}
        }
        if (!staged) {
            ring_->cancel(slice);
            reserved=false;
            return false;
        }
        VkBufferCopy copy{};
        copy.srcOffset=slice.offset;
        copy.dstOffset=0;
        copy.size=slice.bytes;
        vkCmdCopyBuffer(cmd,upload_,gpu->buffer,1,&copy);
        VkBufferMemoryBarrier barrier{};
        barrier.sType=VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER;
        barrier.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT;
        barrier.dstAccessMask=VK_ACCESS_VERTEX_ATTRIBUTE_READ_BIT |
                              VK_ACCESS_INDEX_READ_BIT;
        barrier.srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;
        barrier.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;
        barrier.buffer=gpu->buffer;
        barrier.offset=0;
        barrier.size=VK_WHOLE_SIZE;
        vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_TRANSFER_BIT,
            VK_PIPELINE_STAGE_VERTEX_INPUT_BIT,0,0,nullptr,1,&barrier,0,nullptr);
        if (vkEndCommandBuffer(cmd)!=VK_SUCCESS) {
            ring_->cancel(slice);
            reserved=false;
            return false;
        }
        pending_.push_back(std::move(pending)); /* last allocation */
        VkSubmitInfo submit{};
        submit.sType=VK_STRUCTURE_TYPE_SUBMIT_INFO;
        submit.commandBufferCount=1;
        submit.pCommandBuffers=&cmd;
        const VkResult submitted=vkQueueSubmit(
            queue_,1,&submit,pending_.back()->fence);
        if (submitted!=VK_SUCCESS) {
            /* Do not reuse unknown device work or destroy an unknown GPU
             * reference following a driver/device submission failure. */
            lost_=true;
            return false;
        }
        if (!ring_->commit(slice,next_ticket_+1)) {
            lost_=true;
            return false;
        }
        reserved=false;
        ++next_ticket_;
        result->destination=std::move(gpu);
        result->ticket=next_ticket_;
        *out=std::move(result);
        return true;
    } catch(const std::bad_alloc&) {
        if (reserved && !lost_) ring_->cancel(slice);
        return false;
    }
}
} // namespace shyt_native_v369
