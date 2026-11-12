/* SPDX-License-Identifier: GPL-2.0-or-later
 * Native Vulkan offscreen indexed draw, readback and pixel assertions.
 * Invented FLVER2 mesh, public GLSL; no original game assets or PS4 ELF.
 */
#include "native_vulkan_flver_semantic_draw_v372.h"
#include <vulkan/vulkan.h>
#include <cstdio>
#include <cstring>
#include <cstdint>
#include <fstream>
#include <memory>
#include <vector>
#define CHECK372(x) do { if(!(x)) { \
    std::fprintf(stderr,"NATIVE_V372_CHECK_FAILED_LINE_%d\n",__LINE__); \
    return false; } } while(0)

static void u16(unsigned char* p,unsigned off,uint16_t val) {
    p[off]=static_cast<unsigned char>(val);
    p[off+1]=static_cast<unsigned char>(val>>8);
}
static void u32(unsigned char* p,unsigned off,uint32_t val) {
    u16(p,off,static_cast<uint16_t>(val));
    u16(p,off+2,static_cast<uint16_t>(val>>16));
}
static constexpr unsigned kFile=0x294,kData=0x200;
static void invented_flver(unsigned char (&p)[kFile],bool visible,
                           unsigned stride) {
    std::memset(p,0,sizeof(p));
    std::memcpy(p,"FLVER\0L\0",8);
    u32(p,8,0x20014);u32(p,12,kData);u32(p,16,16+3*stride);
    u32(p,24,1);u32(p,32,1);u32(p,36,1);
    p[0x49]=1;u32(p,0x50,1);u32(p,0x54,1);
    p[0xa0]=1;u32(p,0xa0+16,UINT32_MAX);
    u32(p,0xa0+32,1);u32(p,0xa0+36,0x1c0);
    u32(p,0xa0+40,1);u32(p,0xa0+44,0x1c4);
    /* A triangle LIST, not a strip. */
    p[0xd0+4]=0;
    u32(p,0xd0+8,3);u32(p,0xd0+16,6);u32(p,0xd0+24,16);
    u32(p,0xf0+8,stride);u32(p,0xf0+12,3);
    u32(p,0xf0+24,3*stride);u32(p,0xf0+28,16);
    const unsigned count=stride==44 ? 8 : 6;
    u32(p,0x110,count);u32(p,0x110+12,0x120);
    const uint32_t semantics44[]={0,3,6,6,2,1,10,5};
    const uint32_t types44[]={2,0x11,0x11,0x11,0x11,0x13,0x13,0x16};
    const uint32_t indexes44[]={0,0,0,1,0,0,1,0};
    const uint32_t offsets44[]={0,12,16,20,24,28,32,36};
    const uint32_t semantics36[]={0,3,6,6,10,5};
    const uint32_t types36[]={2,0x11,0x11,0x11,0x13,0x16};
    const uint32_t indexes36[]={0,0,0,1,1,0};
    const uint32_t offsets36[]={0,12,16,20,24,28};
    for(unsigned i=0;i<count;++i) {
        const unsigned m=0x120+i*20;
        u32(p,m+4,stride==44?offsets44[i]:offsets36[i]);
        u32(p,m+8,stride==44?types44[i]:types36[i]);
        u32(p,m+12,stride==44?semantics44[i]:semantics36[i]);
        u32(p,m+16,stride==44?indexes44[i]:indexes36[i]);
    }
    u16(p,kData,0);u16(p,kData+2,1);u16(p,kData+4,2);
    static constexpr float coordinates[9]={
        -0.75f,-0.70f,0.0f,
         0.75f,-0.70f,0.0f,
         0.0f, 0.75f,0.0f
    };
    for(unsigned i=0;i<3;++i) {
        unsigned off=kData+16+i*stride;
        float xyz[3];
        for(unsigned k=0;k<3;++k)
            xyz[k]=coordinates[i*3+k] + (k==0 && !visible ? 3.0f : 0.f);
        std::memcpy(p+off,xyz,12);
        /* This layout matches the actual private BB/DS3 semantic/type
         * sequence: float3, packed normals/tangents, bone data, RGBA,
         * signed16 UV pairs. Values are entirely synthetic. */
        p[off+12]=127;p[off+13]=127;p[off+14]=254;p[off+15]=6;
        p[off+16]=254;p[off+17]=127;p[off+18]=127;p[off+19]=127;
        p[off+20]=127;p[off+21]=254;p[off+22]=127;p[off+23]=127;
        if(stride==44) {
            p[off+24]=0;p[off+25]=1;p[off+26]=2;p[off+27]=3;
            p[off+28]=128;p[off+29]=64;p[off+30]=32;p[off+31]=31;
        }
        const unsigned color=stride==44 ? 32 : 24;
        p[off+color]=255;p[off+color+1]=128;
        p[off+color+2]=0;p[off+color+3]=255;
        u16(p,off+color+4,2048);u16(p,off+color+6,1024);
        u16(p,off+color+8,4096);u16(p,off+color+10,512);
    }
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
    CHECK372(pixels.size()==W*H*4u);
    const auto* corner=&pixels[0];
    CHECK372(corner[0]<8 && corner[1]<8 && corner[2]<8 && corner[3]>248);
    const size_t center=(H/2u*W+W/2u)*4u;
    if (expect_triangle) {
        CHECK372(pixels[center+0]<8 && pixels[center+1]>245 &&
                 pixels[center+2]<8 && pixels[center+3]>248);
    } else {
        CHECK372(pixels[center+0]<8 && pixels[center+1]<8 &&
                 pixels[center+2]<8 && pixels[center+3]>248);
    }
    unsigned green=0;
    for(size_t i=0;i<pixels.size();i+=4)
        if (pixels[i+0]<8 && pixels[i+1]>245 && pixels[i+2]<8) ++green;
    if (expect_triangle) CHECK372(green>400 && green<2400);
    else CHECK372(green==0);
    std::printf("NATIVE_V372_DRAW_GREEN_PIXELS=%u EXPECT_TRIANGLE=%u\n",
                green,expect_triangle?1u:0u);
    return true;
}
static bool run_v372(const char* vs,const char* fs) {
    const auto vertex_shader=shader(vs),fragment_shader=shader(fs);
    CHECK372(vertex_shader.size()>5 && fragment_shader.size()>5);
    VkInstance instance=VK_NULL_HANDLE;
    VkApplicationInfo app{};
    app.sType=VK_STRUCTURE_TYPE_APPLICATION_INFO;
    app.pApplicationName="Native V372 real-layout FLVER draw smoke";
    app.apiVersion=VK_API_VERSION_1_0;
    VkInstanceCreateInfo info{};
    info.sType=VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO;
    info.pApplicationInfo=&app;
    CHECK372(vkCreateInstance(&info,nullptr,&instance)==VK_SUCCESS);
    uint32_t count=0;
    CHECK372(vkEnumeratePhysicalDevices(instance,&count,nullptr)==VK_SUCCESS &&
             count>0 && count<=32);
    std::vector<VkPhysicalDevice> devices(count);
    CHECK372(vkEnumeratePhysicalDevices(instance,&count,devices.data())==VK_SUCCESS);
    VkPhysicalDevice physical=VK_NULL_HANDLE;
    for(const auto& candidate:devices) {
        VkPhysicalDeviceProperties props{};
        vkGetPhysicalDeviceProperties(candidate,&props);
        if (props.deviceType==VK_PHYSICAL_DEVICE_TYPE_CPU) {
            physical=candidate;break;
        }
    }
    CHECK372(physical!=VK_NULL_HANDLE);
    uint32_t family_count=0;
    vkGetPhysicalDeviceQueueFamilyProperties(physical,&family_count,nullptr);
    CHECK372(family_count>0 && family_count<=32);
    VkQueueFamilyProperties families[32]{};
    vkGetPhysicalDeviceQueueFamilyProperties(physical,&family_count,families);
    uint32_t graphics=UINT32_MAX;
    for(uint32_t i=0;i<family_count;++i)
        if (families[i].queueCount &&
            (families[i].queueFlags&VK_QUEUE_GRAPHICS_BIT)) {
            graphics=i;break;
        }
    CHECK372(graphics!=UINT32_MAX);
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
    CHECK372(vkCreateDevice(physical,&create,nullptr,&device)==VK_SUCCESS);
    VkQueue queue=VK_NULL_HANDLE;
    vkGetDeviceQueue(device,graphics,0,&queue);
    CHECK372(queue!=VK_NULL_HANDLE);
    {
        shyt_native_v369::VulkanFlverStreamV369 stream;
        CHECK372(stream.initialize(physical,device,queue,graphics,320));
        std::unique_ptr<shyt_native_v369::UploadedModelV369> models[2];
        unsigned char source[2][kFile]{};
        for(unsigned i=0;i<2;++i) {
            const unsigned stride=i==0 ? 44u : 36u;
            invented_flver(source[i],i==0,stride);
            ShytNativeFlver2AssetV363 asset{};
            asset.flver=source[i];asset.flver_bytes=sizeof(source[i]);
            ShytNativeFlver2VertexLayoutV371 layout{};
            CHECK372(shyt_native_flver2_vertex_layout_v371(
                asset.flver,asset.flver_bytes,0,&layout));
            CHECK372(layout.stride==stride && layout.vertex_count==3);
            CHECK372(stream.submit_flver(&asset,&models[i]));
            CHECK372(models[i] && models[i]->gpu_buffer()!=VK_NULL_HANDLE);
            CHECK372(models[i]->vertices[0].stride==stride);
        }
        CHECK372(stream.wait_for(models[1]->ticket,30000000000ull));
        CHECK372(stream.ready(models[0]->ticket));
        std::vector<uint8_t> rgba;
        for(unsigned i=0;i<2;++i) {
            ShytNativeFlver2AssetV363 asset{};
            asset.flver=source[i];asset.flver_bytes=sizeof(source[i]);
            CHECK372(shyt_native_v372::draw_offscreen_verified_flver_v372(
                physical,device,queue,graphics,asset,*models[i],
                vertex_shader.data(),vertex_shader.size(),
                fragment_shader.data(),fragment_shader.size(),&rgba));
            CHECK372(evaluate_pixels(rgba,i==0));
        }
        ShytNativeFlver2AssetV363 a{};
        a.flver=source[0];a.flver_bytes=sizeof(source[0]);
        const uint32_t wrong_spv[]={0u,1u,2u,3u,4u};
        CHECK372(!shyt_native_v372::draw_offscreen_verified_flver_v372(
            physical,device,queue,graphics,a,*models[0],
            wrong_spv,5,fragment_shader.data(),fragment_shader.size(),&rgba));
        CHECK372(rgba.empty());
        auto wrong_layout=*models[0];
        wrong_layout.vertices[0].stride=16;
        CHECK372(!shyt_native_v372::draw_offscreen_verified_flver_v372(
            physical,device,queue,graphics,a,wrong_layout,
            vertex_shader.data(),vertex_shader.size(),
            fragment_shader.data(),fragment_shader.size(),&rgba));
        CHECK372(rgba.empty());
        /* Real old V370 interface still refuses 44-byte attributes. */
        CHECK372(!shyt_native_v370::draw_offscreen_flver_v370(
            physical,device,queue,graphics,*models[0],
            vertex_shader.data(),vertex_shader.size(),
            fragment_shader.data(),fragment_shader.size(),&rgba));
        CHECK372(rgba.empty());
        /* The V371 real-layout gate must catch unsupported same-width
         * normal variants, despite already-uploaded GPU data. */
        u32(source[0],0x120+20+8,0x10);
        CHECK372(!shyt_native_v372::draw_offscreen_verified_flver_v372(
            physical,device,queue,graphics,a,*models[0],
            vertex_shader.data(),vertex_shader.size(),
            fragment_shader.data(),fragment_shader.size(),&rgba));
        CHECK372(rgba.empty());
        u32(source[0],0x120+20+8,0x11);
        /* Triangle STRIP must not be misrepresented as triangle LIST. */
        source[0][0xd0+4]=1;
        CHECK372(!shyt_native_v372::draw_offscreen_verified_flver_v372(
            physical,device,queue,graphics,a,*models[0],
            vertex_shader.data(),vertex_shader.size(),
            fragment_shader.data(),fragment_shader.size(),&rgba));
        CHECK372(rgba.empty());
        source[0][0xd0+4]=0;
        /* NaN in position is detected via V371 preflight even if model
         * GPU bytes were staged earlier. */
        u32(source[0],kData+16,0x7fc00000u);
        CHECK372(!shyt_native_v372::draw_offscreen_verified_flver_v372(
            physical,device,queue,graphics,a,*models[0],
            vertex_shader.data(),vertex_shader.size(),
            fragment_shader.data(),fragment_shader.size(),&rgba));
        CHECK372(rgba.empty());
        models[0].reset();models[1].reset();
    }
    vkDestroyDevice(device,nullptr);
    vkDestroyInstance(instance,nullptr);
    std::puts("NATIVE_V372_LINUX_VULKAN_REAL_PACKED_FLVER44_36_INDEXED_DRAW_PASS");
    return true;
}
int main(int argc,char** argv) {
    if (argc!=3) return 2;
    return run_v372(argv[1],argv[2])?0:1;
}
