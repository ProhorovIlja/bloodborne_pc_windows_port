/* SPDX-License-Identifier: GPL-2.0-or-later
 * Native Linux Vulkan CPU/lavapipe transfer and GPU readback of invented FLVER.
 * Requires a software Vulkan device. No original Bloodborne/DS3 assets.
 */
#include "native_vulkan_flver_upload_v368.h"
#include <cassert>
#include <cstdio>
#include <cstring>
#include <cstdint>
#include <memory>
#include <vector>
#define REQUIRE368(c) do { if (!(c)) { \
    std::fprintf(stderr,"NATIVE_V368_FAIL_LINE_%d\n",__LINE__); \
    return false; }} while(0)
static void w16(unsigned char *p,unsigned off,uint16_t value) {
    p[off]=static_cast<unsigned char>(value);
    p[off+1]=static_cast<unsigned char>(value>>8);
}
static void w32(unsigned char *p,unsigned off,uint32_t value) {
    w16(p,off,static_cast<uint16_t>(value));
    w16(p,off+2,static_cast<uint16_t>(value>>16));
}
static constexpr unsigned kFileBytes=0x1b4,kDataOffset=0x180;
static void synthetic_model(unsigned char (&p)[kFileBytes],unsigned variant) {
    std::memset(p,0,sizeof(p));
    std::memcpy(p,"FLVER\0L\0",8);
    w32(p,8,0x20014);
    w32(p,12,kDataOffset);w32(p,16,52);
    w32(p,24,1);w32(p,32,1);w32(p,36,1);
    p[0x49]=1;w32(p,0x50,1);w32(p,0x54,1);
    p[0xa0]=1;w32(p,0xa0+16,UINT32_MAX);
    w32(p,0xa0+32,1);w32(p,0xa0+36,0x138);
    w32(p,0xa0+40,1);w32(p,0xa0+44,0x13c);
    p[0xd0+4]=1;p[0xd0+5]=1;
    w32(p,0xd0+8,3);w32(p,0xd0+16,6);w32(p,0xd0+24,16);
    w32(p,0xf0+8,12);w32(p,0xf0+12,3);
    w32(p,0xf0+24,36);w32(p,0xf0+28,16);
    w32(p,0x110,1);w32(p,0x110+12,0x120);
    w32(p,0x120+8,2);
    w16(p,kDataOffset,0);w16(p,kDataOffset+2,1);
    w16(p,kDataOffset+4,2);
    for(unsigned i=0;i<36;++i)
        p[kDataOffset+16+i]=static_cast<unsigned char>(i*7u+variant);
}
static uint32_t memory_type(VkPhysicalDevice physical,uint32_t allowed,
                            VkMemoryPropertyFlags flags) {
    VkPhysicalDeviceMemoryProperties props{};
    vkGetPhysicalDeviceMemoryProperties(physical,&props);
    for(uint32_t i=0;i<props.memoryTypeCount;++i)
        if ((allowed&(1u<<i)) &&
            (props.memoryTypes[i].propertyFlags&flags)==flags) return i;
    return UINT32_MAX;
}
static bool readback(VkPhysicalDevice physical,VkDevice device,
                     VkQueue queue,uint32_t family,VkBuffer source,
                     const unsigned char* expected) {
    VkBuffer destination=VK_NULL_HANDLE;
    VkDeviceMemory memory=VK_NULL_HANDLE;
    VkCommandPool pool=VK_NULL_HANDLE;
    VkFence fence=VK_NULL_HANDLE;
    bool valid=false;
    do {
        VkBufferCreateInfo desc{};
        desc.sType=VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
        desc.size=42;
        desc.usage=VK_BUFFER_USAGE_TRANSFER_DST_BIT;
        desc.sharingMode=VK_SHARING_MODE_EXCLUSIVE;
        if (vkCreateBuffer(device,&desc,nullptr,&destination)!=VK_SUCCESS) break;
        VkMemoryRequirements req{};
        vkGetBufferMemoryRequirements(device,destination,&req);
        const uint32_t type=memory_type(physical,req.memoryTypeBits,
            VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|
            VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
        if (type==UINT32_MAX) break;
        VkMemoryAllocateInfo alloc{};
        alloc.sType=VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
        alloc.allocationSize=req.size;
        alloc.memoryTypeIndex=type;
        if (vkAllocateMemory(device,&alloc,nullptr,&memory)!=VK_SUCCESS ||
            vkBindBufferMemory(device,destination,memory,0)!=VK_SUCCESS) break;
        VkCommandPoolCreateInfo pool_info{};
        pool_info.sType=VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;
        pool_info.queueFamilyIndex=family;
        if (vkCreateCommandPool(device,&pool_info,nullptr,&pool)!=VK_SUCCESS) break;
        VkCommandBufferAllocateInfo alloc_cmd{};
        alloc_cmd.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
        alloc_cmd.commandPool=pool;
        alloc_cmd.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;
        alloc_cmd.commandBufferCount=1;
        VkCommandBuffer cmd=VK_NULL_HANDLE;
        if (vkAllocateCommandBuffers(device,&alloc_cmd,&cmd)!=VK_SUCCESS) break;
        VkCommandBufferBeginInfo begin{};
        begin.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
        if (vkBeginCommandBuffer(cmd,&begin)!=VK_SUCCESS) break;
        VkBufferMemoryBarrier src_barrier{};
        src_barrier.sType=VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER;
        src_barrier.srcAccessMask=VK_ACCESS_VERTEX_ATTRIBUTE_READ_BIT |
                                  VK_ACCESS_INDEX_READ_BIT;
        src_barrier.dstAccessMask=VK_ACCESS_TRANSFER_READ_BIT;
        src_barrier.srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;
        src_barrier.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;
        src_barrier.buffer=source;
        src_barrier.offset=0;
        src_barrier.size=VK_WHOLE_SIZE;
        vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_VERTEX_INPUT_BIT,
            VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,nullptr,1,&src_barrier,0,nullptr);
        VkBufferCopy copy{};
        copy.size=42;
        vkCmdCopyBuffer(cmd,source,destination,1,&copy);
        VkBufferMemoryBarrier host_barrier{};
        host_barrier.sType=VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER;
        host_barrier.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT;
        host_barrier.dstAccessMask=VK_ACCESS_HOST_READ_BIT;
        host_barrier.srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;
        host_barrier.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;
        host_barrier.buffer=destination;
        host_barrier.offset=0;
        host_barrier.size=VK_WHOLE_SIZE;
        vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_TRANSFER_BIT,
            VK_PIPELINE_STAGE_HOST_BIT,0,0,nullptr,1,&host_barrier,0,nullptr);
        if (vkEndCommandBuffer(cmd)!=VK_SUCCESS) break;
        VkFenceCreateInfo fence_info{};
        fence_info.sType=VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;
        if (vkCreateFence(device,&fence_info,nullptr,&fence)!=VK_SUCCESS) break;
        VkSubmitInfo submit{};
        submit.sType=VK_STRUCTURE_TYPE_SUBMIT_INFO;
        submit.commandBufferCount=1;
        submit.pCommandBuffers=&cmd;
        if (vkQueueSubmit(queue,1,&submit,fence)!=VK_SUCCESS ||
            vkWaitForFences(device,1,&fence,VK_TRUE,30000000000ull)!=VK_SUCCESS)
            break;
        void* mapped=nullptr;
        if (vkMapMemory(device,memory,0,42,0,&mapped)!=VK_SUCCESS || !mapped)
            break;
        valid=std::memcmp(mapped,expected,42)==0;
        vkUnmapMemory(device,memory);
    } while(false);
    if (fence) vkDestroyFence(device,fence,nullptr);
    if (pool) vkDestroyCommandPool(device,pool,nullptr);
    if (destination) vkDestroyBuffer(device,destination,nullptr);
    if (memory) vkFreeMemory(device,memory,nullptr);
    return valid;
}
static bool test368() {
    VkInstance instance=VK_NULL_HANDLE;
    VkInstanceCreateInfo instance_info{};
    instance_info.sType=VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
    VkApplicationInfo app{};
    app.sType=VK_STRUCTURE_TYPE_APPLICATION_INFO;
    app.pApplicationName="Native V368 FLVER upload synthetic test";
    app.apiVersion=VK_API_VERSION_1_0;
    instance_info.pApplicationInfo=&app;
    REQUIRE368(vkCreateInstance(&instance_info,nullptr,&instance)==VK_SUCCESS);
    uint32_t count=0;
    REQUIRE368(vkEnumeratePhysicalDevices(instance,&count,nullptr)==VK_SUCCESS &&
               count>0 && count<=32);
    std::vector<VkPhysicalDevice> physicals(count);
    REQUIRE368(vkEnumeratePhysicalDevices(instance,&count,physicals.data())==VK_SUCCESS);
    VkPhysicalDevice physical=VK_NULL_HANDLE;
    for(auto p:physicals) {
        VkPhysicalDeviceProperties props{};
        vkGetPhysicalDeviceProperties(p,&props);
        if (props.deviceType==VK_PHYSICAL_DEVICE_TYPE_CPU) {
            physical=p;break;
        }
    }
    REQUIRE368(physical!=VK_NULL_HANDLE); /* CI requires Mesa lavapipe */
    uint32_t families=0;
    vkGetPhysicalDeviceQueueFamilyProperties(physical,&families,nullptr);
    REQUIRE368(families>0 && families<=32);
    VkQueueFamilyProperties props[32]{};
    vkGetPhysicalDeviceQueueFamilyProperties(physical,&families,props);
    uint32_t graphics=UINT32_MAX;
    for(uint32_t i=0;i<families;++i)
        if (props[i].queueCount && (props[i].queueFlags&VK_QUEUE_GRAPHICS_BIT)) {
            graphics=i;break;
        }
    REQUIRE368(graphics!=UINT32_MAX);
    float priority=1.0f;
    VkDeviceQueueCreateInfo q{};
    q.sType=VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
    q.queueFamilyIndex=graphics;
    q.queueCount=1;
    q.pQueuePriorities=&priority;
    VkDeviceCreateInfo create{};
    create.sType=VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
    create.queueCreateInfoCount=1;
    create.pQueueCreateInfos=&q;
    VkDevice device=VK_NULL_HANDLE;
    REQUIRE368(vkCreateDevice(physical,&create,nullptr,&device)==VK_SUCCESS);
    VkQueue queue=VK_NULL_HANDLE;
    vkGetDeviceQueue(device,graphics,0,&queue);
    REQUIRE368(queue!=VK_NULL_HANDLE);
    unsigned char model[kFileBytes];
    unsigned char expected[2][42]{};
    std::unique_ptr<shyt_native_v368::VulkanFlverUploadV368> uploaded[2];
    for(unsigned i=0;i<2;++i) {
        synthetic_model(model,i+1u);
        std::memcpy(expected[i],model+kDataOffset+16,36);
        std::memcpy(expected[i]+36,model+kDataOffset,6);
        ShytNativeFlver2AssetV363 asset{};
        asset.flver=model;asset.flver_bytes=sizeof(model);
        REQUIRE368(!shyt_native_v368::submit_flver_vulkan_v368(
            physical,device,queue,graphics,&asset,41));
        uploaded[i]=shyt_native_v368::submit_flver_vulkan_v368(
            physical,device,queue,graphics,&asset,42);
        REQUIRE368(uploaded[i] && uploaded[i]->gpu_buffer()!=VK_NULL_HANDLE &&
                   uploaded[i]->uploaded_bytes()==42 &&
                   uploaded[i]->vertices().size()==1 &&
                   uploaded[i]->indices().size()==1 &&
                   uploaded[i]->draws().size()==1);
        REQUIRE368(uploaded[i]->vertices()[0].stride==12 &&
                   uploaded[i]->vertices()[0].offset==0 &&
                   uploaded[i]->indices()[0].offset==36 &&
                   uploaded[i]->indices()[0].type==VK_INDEX_TYPE_UINT16);
        std::memset(model,0,sizeof(model)); /* asset memory can be reused */
    }
    for(unsigned i=0;i<2;++i) {
        REQUIRE368(uploaded[i]->wait_for(30000000000ull));
        REQUIRE368(uploaded[i]->ready() && !uploaded[i]->device_lost());
        REQUIRE368(readback(physical,device,queue,graphics,
                            uploaded[i]->gpu_buffer(),expected[i]));
        uploaded[i].reset();
    }
    synthetic_model(model,0);
    ShytNativeFlver2AssetV363 asset{};
    asset.flver=model;asset.flver_bytes=sizeof(model);
    w16(model,kDataOffset+4,999);
    REQUIRE368(!shyt_native_v368::submit_flver_vulkan_v368(
        physical,device,queue,graphics,&asset,42));
    synthetic_model(model,0);
    w32(model,24,0);w32(model,32,0);w32(model,36,0);
    w32(model,0x50,0);w32(model,0x54,0);
    w32(model,12,0x80);w32(model,16,0);
    auto empty=shyt_native_v368::submit_flver_vulkan_v368(
        physical,device,queue,graphics,&asset,0);
    REQUIRE368(empty && empty->uploaded_bytes()==0 &&
               empty->gpu_buffer()==VK_NULL_HANDLE && empty->wait_for(0));
    empty.reset();
    vkDestroyDevice(device,nullptr);
    vkDestroyInstance(instance,nullptr);
    std::puts("NATIVE_V368_LINUX_LAVAPIPE_REAL_VULKAN_FLVER_GPU_READBACK_PASS");
    return true;
}
int main() {return test368()?0:1;}
