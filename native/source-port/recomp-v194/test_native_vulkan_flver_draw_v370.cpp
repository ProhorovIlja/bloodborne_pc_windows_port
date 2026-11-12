/* SPDX-License-Identifier: GPL-2.0-or-later
 * Native Vulkan offscreen indexed draw, readback and pixel assertions.
 * Invented FLVER2 mesh, public GLSL; no original game assets or PS4 ELF.
 */
#include "native_vulkan_flver_draw_v370.h"
#include <vulkan/vulkan.h>
#include <cstdio>
#include <cstring>
#include <cstdint>
#include <fstream>
#include <memory>
#include <vector>
#define CHECK370(x) do { if(!(x)) { \
    std::fprintf(stderr,"NATIVE_V370_CHECK_FAILED_LINE_%d\n",__LINE__); \
    return false; } } while(0)

static void u16(unsigned char* p,unsigned off,uint16_t val) {
    p[off]=static_cast<unsigned char>(val);
    p[off+1]=static_cast<unsigned char>(val>>8);
}
static void u32(unsigned char* p,unsigned off,uint32_t val) {
    u16(p,off,static_cast<uint16_t>(val));
    u16(p,off+2,static_cast<uint16_t>(val>>16));
}
static constexpr unsigned kFile=0x1b4,kData=0x180;
static void invented_flver(unsigned char (&p)[kFile],bool visible) {
    std::memset(p,0,sizeof(p));
    std::memcpy(p,"FLVER\0L\0",8);
    u32(p,8,0x20014);u32(p,12,kData);u32(p,16,52);
    u32(p,24,1);u32(p,32,1);u32(p,36,1);
    p[0x49]=1;u32(p,0x50,1);u32(p,0x54,1);
    p[0xa0]=1;
    u32(p,0xa0+16,UINT32_MAX);
    u32(p,0xa0+32,1);u32(p,0xa0+36,0x138);
    u32(p,0xa0+40,1);u32(p,0xa0+44,0x13c);
    p[0xd0+4]=1;p[0xd0+5]=1;
    u32(p,0xd0+8,3);u32(p,0xd0+16,6);u32(p,0xd0+24,16);
    u32(p,0xf0+8,12);u32(p,0xf0+12,3);
    u32(p,0xf0+24,36);u32(p,0xf0+28,16);
    u32(p,0x110,1);u32(p,0x110+12,0x120);
    u32(p,0x120+8,2);
    u16(p,kData,0);u16(p,kData+2,1);u16(p,kData+4,2);
    float vertices[9]={-0.75f,-0.70f,0.0f,
                        0.75f,-0.70f,0.0f,
                        0.0f,0.75f,0.0f};
    if(!visible) for(unsigned i=0;i<3;++i) vertices[i*3]+=3.0f;
    static_assert(sizeof(vertices)==36,"three float3 vertices");
    std::memcpy(p+kData+16,vertices,sizeof(vertices));
}
static std::vector<uint32_t> shader(const char* path) {
    if (!path) return {};
    std::ifstream file(path,std::ios::binary|std::ios::ate);
    if (!file) return {};
    const auto size=file.tellg();
    if (size<=0 || size>1048576 || size%4!=0) return {};
    std::vector<uint32_t> data(static_cast<size_t>(size)/4);
    file.seekg(0,std::ios::beg);
    if (!file.read(reinterpret_cast<char*>(data.data()),size)) return {};
    return data;
}
static bool evaluate_pixels(const std::vector<uint8_t>& pixels,bool expect_triangle) {
    constexpr unsigned W=shyt_native_v370::kFrameWidthV370;
    constexpr unsigned H=shyt_native_v370::kFrameHeightV370;
    CHECK370(pixels.size()==W*H*4u);
    const auto* corner=&pixels[0];
    CHECK370(corner[0]<8 && corner[1]<8 && corner[2]<8 && corner[3]>248);
    const size_t center=(H/2u*W+W/2u)*4u;
    if (expect_triangle) {
        CHECK370(pixels[center+0]<8 && pixels[center+1]>245 &&
                 pixels[center+2]<8 && pixels[center+3]>248);
    } else {
        CHECK370(pixels[center+0]<8 && pixels[center+1]<8 &&
                 pixels[center+2]<8 && pixels[center+3]>248);
    }
    unsigned green=0;
    for(size_t i=0;i<pixels.size();i+=4)
        if (pixels[i+0]<8 && pixels[i+1]>245 && pixels[i+2]<8) ++green;
    if (expect_triangle) CHECK370(green>400 && green<2400);
    else CHECK370(green==0);
    std::printf("NATIVE_V370_DRAW_GREEN_PIXELS=%u EXPECT_TRIANGLE=%u\n",
                green,expect_triangle?1u:0u);
    return true;
}
static bool run_v370(const char* vs,const char* fs) {
    const auto vertex_shader=shader(vs),fragment_shader=shader(fs);
    CHECK370(vertex_shader.size()>5 && fragment_shader.size()>5);
    VkInstance instance=VK_NULL_HANDLE;
    VkApplicationInfo app{};
    app.sType=VK_STRUCTURE_TYPE_APPLICATION_INFO;
    app.pApplicationName="Native V370 indexed FLVER draw test";
    app.apiVersion=VK_API_VERSION_1_0;
    VkInstanceCreateInfo info{};
    info.sType=VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
    info.pApplicationInfo=&app;
    CHECK370(vkCreateInstance(&info,nullptr,&instance)==VK_SUCCESS);
    uint32_t count=0;
    CHECK370(vkEnumeratePhysicalDevices(instance,&count,nullptr)==VK_SUCCESS &&
             count>0 && count<=32);
    std::vector<VkPhysicalDevice> physicals(count);
    CHECK370(vkEnumeratePhysicalDevices(instance,&count,physicals.data())==VK_SUCCESS);
    VkPhysicalDevice physical=VK_NULL_HANDLE;
    for(const auto& dev:physicals) {
        VkPhysicalDeviceProperties props{};
        vkGetPhysicalDeviceProperties(dev,&props);
        if (props.deviceType==VK_PHYSICAL_DEVICE_TYPE_CPU) {
            physical=dev;break;
        }
    }
    CHECK370(physical!=VK_NULL_HANDLE); /* mesa lavapipe required */
    uint32_t family_count=0;
    vkGetPhysicalDeviceQueueFamilyProperties(physical,&family_count,nullptr);
    CHECK370(family_count>0 && family_count<=32);
    VkQueueFamilyProperties families[32]{};
    vkGetPhysicalDeviceQueueFamilyProperties(physical,&family_count,families);
    uint32_t graphics=UINT32_MAX;
    for(uint32_t i=0;i<family_count;++i)
        if (families[i].queueCount &&
            (families[i].queueFlags&VK_QUEUE_GRAPHICS_BIT)) {
            graphics=i;break;
        }
    CHECK370(graphics!=UINT32_MAX);
    float priority=1.0f;
    VkDeviceQueueCreateInfo queue_info{};
    queue_info.sType=VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO;
    queue_info.queueFamilyIndex=graphics;
    queue_info.queueCount=1;
    queue_info.pQueuePriorities=&priority;
    VkDeviceCreateInfo create{};
    create.sType=VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO;
    create.queueCreateInfoCount=1;
    create.pQueueCreateInfos=&queue_info;
    VkDevice device=VK_NULL_HANDLE;
    CHECK370(vkCreateDevice(physical,&create,nullptr,&device)==VK_SUCCESS);
    VkQueue queue=VK_NULL_HANDLE;
    vkGetDeviceQueue(device,graphics,0,&queue);
    CHECK370(queue!=VK_NULL_HANDLE);
    {
        shyt_native_v369::VulkanFlverStreamV369 stream;
        CHECK370(stream.initialize(physical,device,queue,graphics,96));
        std::unique_ptr<shyt_native_v369::UploadedModelV369> models[2];
        unsigned char source[kFile];
        for(unsigned i=0;i<2;++i) {
            invented_flver(source,i==0);
            ShytNativeFlver2AssetV363 a{};
            a.flver=source;a.flver_bytes=sizeof(source);
            CHECK370(stream.submit_flver(&a,&models[i]));
            CHECK370(models[i] && models[i]->gpu_buffer()!=VK_NULL_HANDLE);
            std::memset(source,0,sizeof(source));
        }
        CHECK370(stream.wait_for(models[1]->ticket,30000000000ull));
        CHECK370(stream.ready(models[0]->ticket));
        std::vector<uint8_t> rgba;
        for(unsigned i=0;i<2;++i) {
            CHECK370(shyt_native_v370::draw_offscreen_flver_v370(
                physical,device,queue,graphics,*models[i],
                vertex_shader.data(),vertex_shader.size(),
                fragment_shader.data(),fragment_shader.size(),&rgba));
            CHECK370(evaluate_pixels(rgba,i==0));
        }
        const uint32_t wrong_spv[]={0u,1u,2u,3u,4u};
        CHECK370(!shyt_native_v370::draw_offscreen_flver_v370(
            physical,device,queue,graphics,*models[0],
            wrong_spv,5,fragment_shader.data(),fragment_shader.size(),&rgba));
        CHECK370(rgba.empty());
        auto wrong_layout=*models[0];
        wrong_layout.vertices[0].stride=16;
        CHECK370(!shyt_native_v370::draw_offscreen_flver_v370(
            physical,device,queue,graphics,wrong_layout,
            vertex_shader.data(),vertex_shader.size(),
            fragment_shader.data(),fragment_shader.size(),&rgba));
        CHECK370(rgba.empty());
        models[0].reset();models[1].reset();
    }
    vkDestroyDevice(device,nullptr);
    vkDestroyInstance(instance,nullptr);
    std::puts("NATIVE_V370_LINUX_VULKAN_REAL_INDEXED_FLVER_TRIANGLE_AND_BLANK_PIXELS_PASS");
    return true;
}
int main(int argc,char** argv) {
    if (argc!=3) return 2;
    return run_v370(argv[1],argv[2])?0:1;
}
