/* SPDX-License-Identifier: GPL-2.0-or-later
 * Original synthetic FLVER2 packed geometry, D3D12 WARP real draw/readback.
 * Public fixture contains no copyrighted game files or shaders.
 */
#include "native_d3d12_flver_draw_v373.h"
#include <dxgi1_4.h>
#include <windows.h>
#include <wrl/client.h>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <memory>
#include <vector>
using Microsoft::WRL::ComPtr;
#define CHECK373(x) do { if(!(x)) { \
    std::fprintf(stderr,"NATIVE_V373_CHECK_FAILED_LINE_%d\n",__LINE__); \
    return false; } } while(0)
static void u16(unsigned char* p,unsigned off,uint16_t value) {
    p[off]=static_cast<unsigned char>(value);
    p[off+1]=static_cast<unsigned char>(value>>8);
}
static void u32(unsigned char* p,unsigned off,uint32_t value) {
    u16(p,off,static_cast<uint16_t>(value));
    u16(p,off+2,static_cast<uint16_t>(value>>16));
}
static constexpr unsigned kFile=0x294,kData=0x200;
static void synthetic_flver(unsigned char (&p)[kFile],bool visible,
                             unsigned stride) {
    std::memset(p,0,sizeof(p));
    std::memcpy(p,"FLVER\0L\0",8);
    u32(p,8,0x20014);u32(p,12,kData);u32(p,16,16+3*stride);
    u32(p,24,1);u32(p,32,1);u32(p,36,1);
    p[0x49]=1;u32(p,0x50,1);u32(p,0x54,1);
    p[0xa0]=1;u32(p,0xa0+16,UINT32_MAX);
    u32(p,0xa0+32,1);u32(p,0xa0+36,0x1c0);
    u32(p,0xa0+40,1);u32(p,0xa0+44,0x1c4);
    p[0xd0+4]=0; // triangle list, not triangle strip
    u32(p,0xd0+8,3);u32(p,0xd0+16,6);u32(p,0xd0+24,16);
    u32(p,0xf0+8,stride);u32(p,0xf0+12,3);
    u32(p,0xf0+24,3*stride);u32(p,0xf0+28,16);
    const unsigned count=stride==44?8:6;
    u32(p,0x110,count);u32(p,0x110+12,0x120);
    const uint32_t types44[]={2,0x11,0x11,0x11,0x11,0x13,0x13,0x16};
    const uint32_t sem44[]={0,3,6,6,2,1,10,5};
    const uint32_t idx44[]={0,0,0,1,0,0,1,0};
    const uint32_t off44[]={0,12,16,20,24,28,32,36};
    const uint32_t types36[]={2,0x11,0x11,0x11,0x13,0x16};
    const uint32_t sem36[]={0,3,6,6,10,5};
    const uint32_t idx36[]={0,0,0,1,1,0};
    const uint32_t off36[]={0,12,16,20,24,28};
    for(unsigned i=0;i<count;++i) {
        const unsigned o=0x120+i*20;
        u32(p,o+4,stride==44?off44[i]:off36[i]);
        u32(p,o+8,stride==44?types44[i]:types36[i]);
        u32(p,o+12,stride==44?sem44[i]:sem36[i]);
        u32(p,o+16,stride==44?idx44[i]:idx36[i]);
    }
    u16(p,kData,0);u16(p,kData+2,1);u16(p,kData+4,2);
    constexpr float xyz[9]={-0.75f,-0.70f,0.f,
                             0.75f,-0.70f,0.f,
                             0.f,0.75f,0.f};
    for(unsigned i=0;i<3;++i) {
        unsigned off=kData+16+i*stride;
        float position[3];
        for(unsigned k=0;k<3;++k)
            position[k]=xyz[i*3+k]+((k==0&&!visible)?3.0f:0.0f);
        std::memcpy(p+off,position,sizeof(position));
        p[off+12]=127;p[off+13]=127;p[off+14]=254;p[off+15]=6;
        p[off+16]=254;p[off+17]=127;p[off+18]=127;p[off+19]=127;
        p[off+20]=127;p[off+21]=254;p[off+22]=127;p[off+23]=127;
        if(stride==44) {
            p[off+24]=0;p[off+25]=1;p[off+26]=2;p[off+27]=3;
            p[off+28]=128;p[off+29]=64;p[off+30]=32;p[off+31]=31;
        }
        const unsigned c=stride==44?32:24;
        p[off+c]=255;p[off+c+1]=128;p[off+c+2]=0;p[off+c+3]=255;
        u16(p,off+c+4,2048);u16(p,off+c+6,1024);
        u16(p,off+c+8,4096);u16(p,off+c+10,512);
    }
}
static bool pixels_match(const std::vector<uint8_t>& p,bool visible) {
    constexpr unsigned w=shyt_native_v373::kFrameWidthV373;
    constexpr unsigned h=shyt_native_v373::kFrameHeightV373;
    CHECK373(p.size()==w*h*4u);
    CHECK373(p[0]<8 && p[1]<8 && p[2]<8 && p[3]>248);
    const unsigned center=(h/2u*w+w/2u)*4u;
    CHECK373(p[center]<8 && p[center+2]<8 && p[center+3]>248);
    if(visible)CHECK373(p[center+1]>245);
    else CHECK373(p[center+1]<8);
    unsigned green=0;
    for(size_t i=0;i<p.size();i+=4)
        if(p[i]<8&&p[i+1]>245&&p[i+2]<8&&p[i+3]>248)++green;
    if(visible)CHECK373(green>400&&green<2400);
    else CHECK373(green==0);
    std::printf("NATIVE_V373_WARP_GREEN_PIXELS=%u VISIBLE=%u\n",
                green,visible?1u:0u);
    return true;
}
static bool run() {
    ComPtr<IDXGIFactory4> factory;
    ComPtr<IDXGIAdapter> warp;
    ComPtr<ID3D12Device> device;
    ComPtr<ID3D12CommandQueue> queue;
    CHECK373(SUCCEEDED(CreateDXGIFactory1(IID_PPV_ARGS(&factory))));
    CHECK373(SUCCEEDED(factory->EnumWarpAdapter(IID_PPV_ARGS(&warp))));
    CHECK373(SUCCEEDED(D3D12CreateDevice(warp.Get(),D3D_FEATURE_LEVEL_11_0,
                                         IID_PPV_ARGS(&device))));
    D3D12_COMMAND_QUEUE_DESC qdesc{};
    qdesc.Type=D3D12_COMMAND_LIST_TYPE_DIRECT;
    CHECK373(SUCCEEDED(device->CreateCommandQueue(&qdesc,
                                                  IID_PPV_ARGS(&queue))));
    {
        shyt_native_v367::D3D12FlverStreamV367 stream;
        CHECK373(stream.initialize(device.Get(),queue.Get(),320));
        unsigned char files[2][kFile]{};
        std::unique_ptr<shyt_native_v367::UploadedModelV367> models[2];
        for(unsigned i=0;i<2;++i) {
            unsigned stride=i==0?44u:36u;
            synthetic_flver(files[i],i==0,stride);
            ShytNativeFlver2AssetV363 asset{};
            asset.flver=files[i];asset.flver_bytes=sizeof(files[i]);
            ShytNativeFlver2VertexLayoutV371 layout{};
            CHECK373(shyt_native_flver2_vertex_layout_v371(asset.flver,
                        asset.flver_bytes,0,&layout));
            CHECK373(layout.stride==stride && layout.vertex_count==3);
            CHECK373(stream.submit_flver(&asset,&models[i]));
            CHECK373(models[i] && models[i]->gpu_buffer &&
                     models[i]->vertices.size()==1 &&
                     models[i]->vertices[0].StrideInBytes==stride);
        }
        CHECK373(stream.wait_for(models[1]->fence,30000));
        CHECK373(stream.is_complete(models[0]->fence));
        std::vector<uint8_t> pixels;
        for(unsigned i=0;i<2;++i) {
            ShytNativeFlver2AssetV363 a{};
            a.flver=files[i];a.flver_bytes=sizeof(files[i]);
            CHECK373(shyt_native_v373::draw_offscreen_verified_flver_v373(
                device.Get(),queue.Get(),a,*models[i],&pixels));
            CHECK373(pixels_match(pixels,i==0));
        }
        ShytNativeFlver2AssetV363 src{};
        src.flver=files[0];src.flver_bytes=sizeof(files[0]);
        CHECK373(!shyt_native_v373::draw_offscreen_verified_flver_v373(
            nullptr,queue.Get(),src,*models[0],&pixels));
        CHECK373(pixels.empty());
        auto wrong=*models[0];
        wrong.vertices[0].StrideInBytes=16;
        CHECK373(!shyt_native_v373::draw_offscreen_verified_flver_v373(
            device.Get(),queue.Get(),src,wrong,&pixels));
        CHECK373(pixels.empty());
        u32(files[0],0x120+20+8,0x10);
        CHECK373(!shyt_native_v373::draw_offscreen_verified_flver_v373(
            device.Get(),queue.Get(),src,*models[0],&pixels));
        CHECK373(pixels.empty());
        u32(files[0],0x120+20+8,0x11);
        files[0][0xd0+4]=1;
        CHECK373(!shyt_native_v373::draw_offscreen_verified_flver_v373(
            device.Get(),queue.Get(),src,*models[0],&pixels));
        CHECK373(pixels.empty());
        files[0][0xd0+4]=0;
        u32(files[0],kData+16,0x7fc00000u);
        CHECK373(!shyt_native_v373::draw_offscreen_verified_flver_v373(
            device.Get(),queue.Get(),src,*models[0],&pixels));
        CHECK373(pixels.empty());
        CHECK373(stream.pending()==0);
        models[0].reset();models[1].reset();
    }
    std::puts("NATIVE_V373_WIN_D3D12_WARP_REAL_FLVER44_36_INDEXED_PIXEL_DRAW_PASS");
    return true;
}
int main() { return run()?0:1; }
