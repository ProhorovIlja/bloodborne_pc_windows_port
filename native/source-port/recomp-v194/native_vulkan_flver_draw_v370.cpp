/* SPDX-License-Identifier: GPL-2.0-or-later
 * V370: genuine native Vulkan 1.0 indexed geometry -> offscreen RGBA8 pixels.
 * Original-game material/shader semantics are deliberately NOT presumed.
 */
#include "native_vulkan_flver_draw_v370.h"
#include <cstring>
#include <new>

namespace shyt_native_v370 {
namespace {
constexpr VkFormat kColorV370=VK_FORMAT_R8G8B8A8_UNORM;
constexpr VkDeviceSize kPixelsV370=kFrameWidthV370*kFrameHeightV370*4u;

uint32_t find_type_v370(VkPhysicalDevice physical,uint32_t compatible,
                        VkMemoryPropertyFlags desired) noexcept {
    VkPhysicalDeviceMemoryProperties mem{};
    vkGetPhysicalDeviceMemoryProperties(physical,&mem);
    for(uint32_t i=0;i<mem.memoryTypeCount;++i) {
        if ((compatible&(1u<<i)) &&
            (mem.memoryTypes[i].propertyFlags&desired)==desired) return i;
    }
    return UINT32_MAX;
}

struct FrameResourcesV370 {
    VkDevice device=VK_NULL_HANDLE;
    VkQueue queue=VK_NULL_HANDLE;
    VkImage image=VK_NULL_HANDLE;
    VkDeviceMemory image_mem=VK_NULL_HANDLE;
    VkImageView image_view=VK_NULL_HANDLE;
    VkRenderPass render_pass=VK_NULL_HANDLE;
    VkFramebuffer framebuffer=VK_NULL_HANDLE;
    VkShaderModule vertex_module=VK_NULL_HANDLE;
    VkShaderModule fragment_module=VK_NULL_HANDLE;
    VkPipelineLayout pipeline_layout=VK_NULL_HANDLE;
    VkPipeline pipeline=VK_NULL_HANDLE;
    VkBuffer readback_buffer=VK_NULL_HANDLE;
    VkDeviceMemory readback_mem=VK_NULL_HANDLE;
    VkCommandPool pool=VK_NULL_HANDLE;
    VkFence fence=VK_NULL_HANDLE;
    bool submitted=false;
    bool completed=false;
    ~FrameResourcesV370() {
        /* This is a synchronous smoke test. Never reuse such a blocking
         * destructor in a production frame loop. */
        if (submitted && !completed && queue)
            (void)vkQueueWaitIdle(queue);
        if (!device) return;
        if (fence) vkDestroyFence(device,fence,nullptr);
        if (pool) vkDestroyCommandPool(device,pool,nullptr);
        if (pipeline) vkDestroyPipeline(device,pipeline,nullptr);
        if (pipeline_layout) vkDestroyPipelineLayout(device,pipeline_layout,nullptr);
        if (vertex_module) vkDestroyShaderModule(device,vertex_module,nullptr);
        if (fragment_module) vkDestroyShaderModule(device,fragment_module,nullptr);
        if (framebuffer) vkDestroyFramebuffer(device,framebuffer,nullptr);
        if (render_pass) vkDestroyRenderPass(device,render_pass,nullptr);
        if (image_view) vkDestroyImageView(device,image_view,nullptr);
        if (image) vkDestroyImage(device,image,nullptr);
        if (image_mem) vkFreeMemory(device,image_mem,nullptr);
        if (readback_buffer) vkDestroyBuffer(device,readback_buffer,nullptr);
        if (readback_mem) vkFreeMemory(device,readback_mem,nullptr);
    }
};

bool allocation_for_image_v370(VkPhysicalDevice physical,
    FrameResourcesV370& f) noexcept {
    VkImageCreateInfo image{};
    image.sType=VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO;
    image.imageType=VK_IMAGE_TYPE_2D;
    image.format=kColorV370;
    image.extent={kFrameWidthV370,kFrameHeightV370,1};
    image.mipLevels=1;
    image.arrayLayers=1;
    image.samples=VK_SAMPLE_COUNT_1_BIT;
    image.tiling=VK_IMAGE_TILING_OPTIMAL;
    image.usage=VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT|VK_IMAGE_USAGE_TRANSFER_SRC_BIT;
    image.sharingMode=VK_SHARING_MODE_EXCLUSIVE;
    image.initialLayout=VK_IMAGE_LAYOUT_UNDEFINED;
    if (vkCreateImage(f.device,&image,nullptr,&f.image)!=VK_SUCCESS) return false;
    VkMemoryRequirements req{};
    vkGetImageMemoryRequirements(f.device,f.image,&req);
    const uint32_t type=find_type_v370(physical,req.memoryTypeBits,
                                       VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
    if (type==UINT32_MAX || !req.size) return false;
    VkMemoryAllocateInfo mem{};
    mem.sType=VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    mem.allocationSize=req.size;
    mem.memoryTypeIndex=type;
    if (vkAllocateMemory(f.device,&mem,nullptr,&f.image_mem)!=VK_SUCCESS ||
        vkBindImageMemory(f.device,f.image,f.image_mem,0)!=VK_SUCCESS) return false;
    VkImageViewCreateInfo view{};
    view.sType=VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO;
    view.image=f.image;
    view.viewType=VK_IMAGE_VIEW_TYPE_2D;
    view.format=kColorV370;
    view.subresourceRange.aspectMask=VK_IMAGE_ASPECT_COLOR_BIT;
    view.subresourceRange.levelCount=1;
    view.subresourceRange.layerCount=1;
    return vkCreateImageView(f.device,&view,nullptr,&f.image_view)==VK_SUCCESS;
}

bool allocation_for_readback_v370(VkPhysicalDevice physical,
    FrameResourcesV370& f) noexcept {
    VkBufferCreateInfo desc{};
    desc.sType=VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO;
    desc.size=kPixelsV370;
    desc.usage=VK_BUFFER_USAGE_TRANSFER_DST_BIT;
    desc.sharingMode=VK_SHARING_MODE_EXCLUSIVE;
    if (vkCreateBuffer(f.device,&desc,nullptr,&f.readback_buffer)!=VK_SUCCESS)
        return false;
    VkMemoryRequirements req{};
    vkGetBufferMemoryRequirements(f.device,f.readback_buffer,&req);
    const uint32_t type=find_type_v370(physical,req.memoryTypeBits,
        VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT);
    if (type==UINT32_MAX || !req.size) return false;
    VkMemoryAllocateInfo mem{};
    mem.sType=VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO;
    mem.allocationSize=req.size;
    mem.memoryTypeIndex=type;
    return vkAllocateMemory(f.device,&mem,nullptr,&f.readback_mem)==VK_SUCCESS &&
           vkBindBufferMemory(f.device,f.readback_buffer,f.readback_mem,0)==VK_SUCCESS;
}

bool create_pass_v370(FrameResourcesV370& f) noexcept {
    VkAttachmentDescription color{};
    color.format=kColorV370;
    color.samples=VK_SAMPLE_COUNT_1_BIT;
    color.loadOp=VK_ATTACHMENT_LOAD_OP_CLEAR;
    color.storeOp=VK_ATTACHMENT_STORE_OP_STORE;
    color.stencilLoadOp=VK_ATTACHMENT_LOAD_OP_DONT_CARE;
    color.stencilStoreOp=VK_ATTACHMENT_STORE_OP_DONT_CARE;
    color.initialLayout=VK_IMAGE_LAYOUT_UNDEFINED;
    color.finalLayout=VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    VkAttachmentReference ref{};
    ref.attachment=0;
    ref.layout=VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    VkSubpassDescription subpass{};
    subpass.pipelineBindPoint=VK_PIPELINE_BIND_POINT_GRAPHICS;
    subpass.colorAttachmentCount=1;
    subpass.pColorAttachments=&ref;
    VkSubpassDependency dep{};
    dep.srcSubpass=VK_SUBPASS_EXTERNAL;
    dep.dstSubpass=0;
    dep.srcStageMask=VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
    dep.dstStageMask=VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT;
    dep.dstAccessMask=VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
    VkRenderPassCreateInfo pass{};
    pass.sType=VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO;
    pass.attachmentCount=1;
    pass.pAttachments=&color;
    pass.subpassCount=1;
    pass.pSubpasses=&subpass;
    pass.dependencyCount=1;
    pass.pDependencies=&dep;
    if(vkCreateRenderPass(f.device,&pass,nullptr,&f.render_pass)!=VK_SUCCESS)
        return false;
    VkFramebufferCreateInfo frame{};
    frame.sType=VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO;
    frame.renderPass=f.render_pass;
    frame.attachmentCount=1;
    frame.pAttachments=&f.image_view;
    frame.width=kFrameWidthV370;
    frame.height=kFrameHeightV370;
    frame.layers=1;
    return vkCreateFramebuffer(f.device,&frame,nullptr,&f.framebuffer)==VK_SUCCESS;
}

bool shader_module_v370(VkDevice device,const uint32_t* words,size_t count,
                        VkShaderModule* out) noexcept {
    if (!words || count<5 || count>262144 || words[0]!=0x07230203u)
        return false;
    VkShaderModuleCreateInfo info{};
    info.sType=VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO;
    info.codeSize=count*sizeof(uint32_t);
    info.pCode=words;
    return vkCreateShaderModule(device,&info,nullptr,out)==VK_SUCCESS;
}

bool create_pipeline_v370(FrameResourcesV370& f,
    const uint32_t* vs,size_t vlen,const uint32_t* fs,size_t flen) noexcept {
    if(!shader_module_v370(f.device,vs,vlen,&f.vertex_module) ||
       !shader_module_v370(f.device,fs,flen,&f.fragment_module)) return false;
    VkPipelineLayoutCreateInfo layout{};
    layout.sType=VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO;
    if(vkCreatePipelineLayout(f.device,&layout,nullptr,&f.pipeline_layout)!=VK_SUCCESS)
        return false;
    VkPipelineShaderStageCreateInfo shaders[2]{};
    for(auto& s:shaders) {
        s.sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO;
        s.pName="main";
    }
    shaders[0].stage=VK_SHADER_STAGE_VERTEX_BIT;
    shaders[0].module=f.vertex_module;
    shaders[1].stage=VK_SHADER_STAGE_FRAGMENT_BIT;
    shaders[1].module=f.fragment_module;
    VkVertexInputBindingDescription binding{};
    binding.binding=0;
    binding.stride=12;
    binding.inputRate=VK_VERTEX_INPUT_RATE_VERTEX;
    VkVertexInputAttributeDescription attr{};
    attr.location=0;
    attr.binding=0;
    attr.format=VK_FORMAT_R32G32B32_SFLOAT;
    attr.offset=0;
    VkPipelineVertexInputStateCreateInfo input{};
    input.sType=VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO;
    input.vertexBindingDescriptionCount=1;
    input.pVertexBindingDescriptions=&binding;
    input.vertexAttributeDescriptionCount=1;
    input.pVertexAttributeDescriptions=&attr;
    VkPipelineInputAssemblyStateCreateInfo assembly{};
    assembly.sType=VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO;
    assembly.topology=VK_PRIMITIVE_TOPOLOGY_TRIANGLE_LIST;
    VkViewport viewport{};
    viewport.x=0;viewport.y=0;
    viewport.width=static_cast<float>(kFrameWidthV370);
    viewport.height=static_cast<float>(kFrameHeightV370);
    viewport.minDepth=0;viewport.maxDepth=1;
    VkRect2D scissor{};
    scissor.extent={kFrameWidthV370,kFrameHeightV370};
    VkPipelineViewportStateCreateInfo viewport_info{};
    viewport_info.sType=VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO;
    viewport_info.viewportCount=1;
    viewport_info.pViewports=&viewport;
    viewport_info.scissorCount=1;
    viewport_info.pScissors=&scissor;
    VkPipelineRasterizationStateCreateInfo raster{};
    raster.sType=VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO;
    raster.polygonMode=VK_POLYGON_MODE_FILL;
    raster.cullMode=VK_CULL_MODE_NONE;
    raster.frontFace=VK_FRONT_FACE_COUNTER_CLOCKWISE;
    raster.lineWidth=1.0f;
    VkPipelineMultisampleStateCreateInfo multisample{};
    multisample.sType=VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO;
    multisample.rasterizationSamples=VK_SAMPLE_COUNT_1_BIT;
    VkPipelineColorBlendAttachmentState blend_attachment{};
    blend_attachment.colorWriteMask=VK_COLOR_COMPONENT_R_BIT|
        VK_COLOR_COMPONENT_G_BIT|VK_COLOR_COMPONENT_B_BIT|VK_COLOR_COMPONENT_A_BIT;
    VkPipelineColorBlendStateCreateInfo blend{};
    blend.sType=VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO;
    blend.attachmentCount=1;
    blend.pAttachments=&blend_attachment;
    VkGraphicsPipelineCreateInfo pipeline{};
    pipeline.sType=VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO;
    pipeline.stageCount=2;
    pipeline.pStages=shaders;
    pipeline.pVertexInputState=&input;
    pipeline.pInputAssemblyState=&assembly;
    pipeline.pViewportState=&viewport_info;
    pipeline.pRasterizationState=&raster;
    pipeline.pMultisampleState=&multisample;
    pipeline.pColorBlendState=&blend;
    pipeline.layout=f.pipeline_layout;
    pipeline.renderPass=f.render_pass;
    pipeline.subpass=0;
    return vkCreateGraphicsPipelines(f.device,VK_NULL_HANDLE,1,&pipeline,nullptr,
                                     &f.pipeline)==VK_SUCCESS;
}

} // namespace

bool draw_offscreen_flver_v370(VkPhysicalDevice physical,VkDevice device,
    VkQueue queue,uint32_t family,
    const shyt_native_v369::UploadedModelV369& model,
    const uint32_t* vertex_spirv,size_t vertex_words,
    const uint32_t* fragment_spirv,size_t fragment_words,
    std::vector<uint8_t>* out) {
    if (!out) return false;
    out->clear();
    if (!physical || !device || !queue || !model.gpu_buffer() ||
        model.vertices.size()!=1 || model.indices.size()!=1 ||
        model.draws.size()!=1 || model.vertices[0].stride!=12 ||
        model.vertices[0].count!=3 || model.indices[0].count!=3 ||
        model.indices[0].type!=VK_INDEX_TYPE_UINT16 ||
        model.draws[0].vertex_buffer_count!=1 ||
        model.draws[0].vertex_buffer_indices[0]!=0 ||
        model.draws[0].face_set_index!=0 ||
        model.vertices[0].offset>model.bytes ||
        36u>model.bytes-model.vertices[0].offset ||
        model.indices[0].offset>model.bytes ||
        6u>model.bytes-model.indices[0].offset)
        return false;
    uint32_t family_count=0;
    vkGetPhysicalDeviceQueueFamilyProperties(physical,&family_count,nullptr);
    if (!family_count || family_count>256 || family>=family_count) return false;
    VkQueueFamilyProperties families[256]{};
    vkGetPhysicalDeviceQueueFamilyProperties(physical,&family_count,families);
    if (!(families[family].queueFlags&VK_QUEUE_GRAPHICS_BIT) ||
        families[family].queueCount==0) return false;
    VkFormatProperties support{};
    vkGetPhysicalDeviceFormatProperties(physical,kColorV370,&support);
    if (!(support.optimalTilingFeatures&VK_FORMAT_FEATURE_COLOR_ATTACHMENT_BIT))
        return false;
    FrameResourcesV370 f;
    f.device=device;
    f.queue=queue;
    if (!allocation_for_image_v370(physical,f) ||
        !allocation_for_readback_v370(physical,f) ||
        !create_pass_v370(f) ||
        !create_pipeline_v370(f,vertex_spirv,vertex_words,fragment_spirv,
                              fragment_words)) return false;
    VkCommandPoolCreateInfo pool{};
    pool.sType=VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO;
    pool.queueFamilyIndex=family;
    if(vkCreateCommandPool(device,&pool,nullptr,&f.pool)!=VK_SUCCESS) return false;
    VkCommandBufferAllocateInfo command{};
    command.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO;
    command.commandPool=f.pool;
    command.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY;
    command.commandBufferCount=1;
    VkCommandBuffer cmd=VK_NULL_HANDLE;
    if(vkAllocateCommandBuffers(device,&command,&cmd)!=VK_SUCCESS) return false;
    VkCommandBufferBeginInfo begin{};
    begin.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO;
    begin.flags=VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT;
    if(vkBeginCommandBuffer(cmd,&begin)!=VK_SUCCESS) return false;
    VkClearValue clear{};
    clear.color.float32[3]=1.0f;
    VkRenderPassBeginInfo pass{};
    pass.sType=VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO;
    pass.renderPass=f.render_pass;
    pass.framebuffer=f.framebuffer;
    pass.renderArea.extent={kFrameWidthV370,kFrameHeightV370};
    pass.clearValueCount=1;
    pass.pClearValues=&clear;
    vkCmdBeginRenderPass(cmd,&pass,VK_SUBPASS_CONTENTS_INLINE);
    vkCmdBindPipeline(cmd,VK_PIPELINE_BIND_POINT_GRAPHICS,f.pipeline);
    VkBuffer gpu=model.gpu_buffer();
    const VkDeviceSize offset=model.vertices[0].offset;
    vkCmdBindVertexBuffers(cmd,0,1,&gpu,&offset);
    vkCmdBindIndexBuffer(cmd,gpu,model.indices[0].offset,VK_INDEX_TYPE_UINT16);
    vkCmdDrawIndexed(cmd,3,1,0,0,0);
    vkCmdEndRenderPass(cmd);
    VkImageMemoryBarrier image_barrier{};
    image_barrier.sType=VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER;
    image_barrier.srcAccessMask=VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT;
    image_barrier.dstAccessMask=VK_ACCESS_TRANSFER_READ_BIT;
    image_barrier.oldLayout=VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL;
    image_barrier.newLayout=VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL;
    image_barrier.srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;
    image_barrier.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;
    image_barrier.image=f.image;
    image_barrier.subresourceRange.aspectMask=VK_IMAGE_ASPECT_COLOR_BIT;
    image_barrier.subresourceRange.levelCount=1;
    image_barrier.subresourceRange.layerCount=1;
    vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT,
        VK_PIPELINE_STAGE_TRANSFER_BIT,0,0,nullptr,0,nullptr,1,&image_barrier);
    VkBufferImageCopy copy{};
    copy.imageSubresource.aspectMask=VK_IMAGE_ASPECT_COLOR_BIT;
    copy.imageSubresource.layerCount=1;
    copy.imageExtent={kFrameWidthV370,kFrameHeightV370,1};
    vkCmdCopyImageToBuffer(cmd,f.image,VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL,
                            f.readback_buffer,1,&copy);
    VkBufferMemoryBarrier host_barrier{};
    host_barrier.sType=VK_STRUCTURE_TYPE_BUFFER_MEMORY_BARRIER;
    host_barrier.srcAccessMask=VK_ACCESS_TRANSFER_WRITE_BIT;
    host_barrier.dstAccessMask=VK_ACCESS_HOST_READ_BIT;
    host_barrier.srcQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;
    host_barrier.dstQueueFamilyIndex=VK_QUEUE_FAMILY_IGNORED;
    host_barrier.buffer=f.readback_buffer;
    host_barrier.offset=0;
    host_barrier.size=VK_WHOLE_SIZE;
    vkCmdPipelineBarrier(cmd,VK_PIPELINE_STAGE_TRANSFER_BIT,
        VK_PIPELINE_STAGE_HOST_BIT,0,0,nullptr,1,&host_barrier,0,nullptr);
    if(vkEndCommandBuffer(cmd)!=VK_SUCCESS) return false;
    VkFenceCreateInfo fence_info{};
    fence_info.sType=VK_STRUCTURE_TYPE_FENCE_CREATE_INFO;
    if(vkCreateFence(device,&fence_info,nullptr,&f.fence)!=VK_SUCCESS)
        return false;
    VkSubmitInfo submit{};
    submit.sType=VK_STRUCTURE_TYPE_SUBMIT_INFO;
    submit.commandBufferCount=1;
    submit.pCommandBuffers=&cmd;
    if(vkQueueSubmit(queue,1,&submit,f.fence)!=VK_SUCCESS) return false;
    f.submitted=true;
    if(vkWaitForFences(device,1,&f.fence,VK_TRUE,30000000000ull)!=VK_SUCCESS)
        return false;
    f.completed=true;
    void* pixels=nullptr;
    if(vkMapMemory(device,f.readback_mem,0,kPixelsV370,0,&pixels)!=VK_SUCCESS ||
        !pixels) return false;
    bool copied=true;
    try {
        auto* start=static_cast<const uint8_t*>(pixels);
        out->assign(start,start+static_cast<size_t>(kPixelsV370));
    } catch (const std::bad_alloc&) {
        copied=false;
    }
    vkUnmapMemory(device,f.readback_mem);
    if (!copied) out->clear();
    return copied;
}
} // namespace shyt_native_v370
