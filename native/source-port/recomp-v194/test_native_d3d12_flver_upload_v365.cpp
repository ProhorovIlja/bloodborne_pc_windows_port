/* SPDX-License-Identifier: GPL-2.0-or-later
 * Real GPU transfer on Microsoft's Windows software WARP adapter.
 * Synthetic FLVER: no Bloodborne/DS3 bytes, PS4 runtime or game executable.
 */
#include "native_d3d12_flver_upload_v365.h"
#include <dxgi1_4.h>
#include <windows.h>
#include <wrl/client.h>
#include <cstdio>
#include <cstring>
#include <cstdint>

using Microsoft::WRL::ComPtr;
using shyt_native_v365::submit_flver_d3d12_v365;

#define REQUIRE_V365(expr) do { if (!(expr)) { \
    std::fprintf(stderr,"NATIVE_V365_TEST_FAILED_AT_LINE_%d\n",__LINE__); \
    return false; } } while(0)

static void w16(unsigned char *p, unsigned off, uint16_t value) {
    p[off]=static_cast<unsigned char>(value);
    p[off+1]=static_cast<unsigned char>(value>>8);
}
static void w32(unsigned char *p, unsigned off, uint32_t value) {
    w16(p,off,static_cast<uint16_t>(value));
    w16(p,off+2,static_cast<uint16_t>(value>>16));
}
static constexpr unsigned kModelBytes=0x1b4;
static constexpr unsigned kDataOffset=0x180;
static void synthetic_model(unsigned char (&p)[kModelBytes]) {
    std::memset(p,0,sizeof(p));
    std::memcpy(p,"FLVER\0L\0",8);
    w32(p,8,0x20014u);w32(p,12,kDataOffset);w32(p,16,52u);
    w32(p,24,1u);w32(p,32,1u);w32(p,36,1u);
    p[0x49]=1u;
    w32(p,0x50,1u);w32(p,0x54,1u);
    p[0xa0]=1u;
    w32(p,0xa0+16,UINT32_MAX);w32(p,0xa0+32,1u);
    w32(p,0xa0+36,0x138u);w32(p,0xa0+40,1u);
    w32(p,0xa0+44,0x13cu);
    p[0xd0+4]=1u;p[0xd0+5]=1u;
    w32(p,0xd0+8,3u);w32(p,0xd0+16,6u);w32(p,0xd0+24,16u);
    w32(p,0xf0+8,12u);w32(p,0xf0+12,3u);
    w32(p,0xf0+24,36u);w32(p,0xf0+28,16u);
    w32(p,0x110,1u);w32(p,0x110+12,0x120u);
    w32(p,0x120+8,2u);
    w16(p,kDataOffset,0u);w16(p,kDataOffset+2,1u);
    w16(p,kDataOffset+4,2u);
    for (unsigned i=0;i<36u;++i)
        p[kDataOffset+16u+i]=static_cast<unsigned char>(i*7u);
}
static D3D12_RESOURCE_DESC buffer_desc(uint64_t bytes) {
    D3D12_RESOURCE_DESC desc{};
    desc.Dimension=D3D12_RESOURCE_DIMENSION_BUFFER;
    desc.Width=bytes;desc.Height=1;
    desc.DepthOrArraySize=1;desc.MipLevels=1;
    desc.Format=DXGI_FORMAT_UNKNOWN;desc.SampleDesc.Count=1;
    desc.Layout=D3D12_TEXTURE_LAYOUT_ROW_MAJOR;
    return desc;
}
static D3D12_HEAP_PROPERTIES readback_heap() {
    D3D12_HEAP_PROPERTIES p{};
    p.Type=D3D12_HEAP_TYPE_READBACK;
    p.CPUPageProperty=D3D12_CPU_PAGE_PROPERTY_UNKNOWN;
    p.MemoryPoolPreference=D3D12_MEMORY_POOL_UNKNOWN;
    p.CreationNodeMask=1;p.VisibleNodeMask=1;
    return p;
}
static bool readback_matches(ID3D12Device* device,ID3D12CommandQueue* queue,
                             ID3D12Resource* gpu,const unsigned char* expected,
                             const size_t bytes) {
    REQUIRE_V365(gpu && expected && bytes>0);
    const auto heap=readback_heap();
    const auto desc=buffer_desc(bytes);
    ComPtr<ID3D12Resource> readback;
    REQUIRE_V365(SUCCEEDED(device->CreateCommittedResource(
        &heap,D3D12_HEAP_FLAG_NONE,&desc,D3D12_RESOURCE_STATE_COPY_DEST,
        nullptr,IID_PPV_ARGS(&readback))));
    ComPtr<ID3D12CommandAllocator> allocator;
    ComPtr<ID3D12GraphicsCommandList> list;
    ComPtr<ID3D12Fence> fence;
    REQUIRE_V365(SUCCEEDED(device->CreateCommandAllocator(
        D3D12_COMMAND_LIST_TYPE_DIRECT,IID_PPV_ARGS(&allocator))));
    REQUIRE_V365(SUCCEEDED(device->CreateCommandList(
        0,D3D12_COMMAND_LIST_TYPE_DIRECT,allocator.Get(),nullptr,
        IID_PPV_ARGS(&list))));
    D3D12_RESOURCE_BARRIER barrier{};
    barrier.Type=D3D12_RESOURCE_BARRIER_TYPE_TRANSITION;
    barrier.Transition.pResource=gpu;
    barrier.Transition.Subresource=D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES;
    barrier.Transition.StateBefore=static_cast<D3D12_RESOURCE_STATES>(
        D3D12_RESOURCE_STATE_VERTEX_AND_CONSTANT_BUFFER |
        D3D12_RESOURCE_STATE_INDEX_BUFFER);
    barrier.Transition.StateAfter=D3D12_RESOURCE_STATE_COPY_SOURCE;
    list->ResourceBarrier(1,&barrier);
    list->CopyBufferRegion(readback.Get(),0,gpu,0,bytes);
    barrier.Transition.StateBefore=D3D12_RESOURCE_STATE_COPY_SOURCE;
    barrier.Transition.StateAfter=static_cast<D3D12_RESOURCE_STATES>(
        D3D12_RESOURCE_STATE_VERTEX_AND_CONSTANT_BUFFER |
        D3D12_RESOURCE_STATE_INDEX_BUFFER);
    list->ResourceBarrier(1,&barrier);
    REQUIRE_V365(SUCCEEDED(list->Close()));
    REQUIRE_V365(SUCCEEDED(device->CreateFence(
        0,D3D12_FENCE_FLAG_NONE,IID_PPV_ARGS(&fence))));
    ID3D12CommandList* const lists[]={list.Get()};
    queue->ExecuteCommandLists(1,lists);
    REQUIRE_V365(SUCCEEDED(queue->Signal(fence.Get(),1)));
    const HANDLE evt=CreateEventW(nullptr,FALSE,FALSE,nullptr);
    REQUIRE_V365(evt!=nullptr);
    const HRESULT set_hr=fence->SetEventOnCompletion(1,evt);
    const DWORD wait=SUCCEEDED(set_hr)?WaitForSingleObject(evt,30000):WAIT_FAILED;
    CloseHandle(evt);
    REQUIRE_V365(wait==WAIT_OBJECT_0);
    void* mapped=nullptr;
    D3D12_RANGE cpu_read={0,bytes};
    REQUIRE_V365(SUCCEEDED(readback->Map(0,&cpu_read,&mapped)) && mapped);
    const bool same=std::memcmp(mapped,expected,bytes)==0;
    const D3D12_RANGE no_write={0,0};
    readback->Unmap(0,&no_write);
    REQUIRE_V365(same);
    return true;
}
static bool test_warp_d3d12_v365() {
    ComPtr<IDXGIFactory4> factory;
    ComPtr<IDXGIAdapter> warp;
    ComPtr<ID3D12Device> device;
    ComPtr<ID3D12CommandQueue> queue;
    REQUIRE_V365(SUCCEEDED(CreateDXGIFactory1(IID_PPV_ARGS(&factory))));
    REQUIRE_V365(SUCCEEDED(factory->EnumWarpAdapter(IID_PPV_ARGS(&warp))));
    REQUIRE_V365(SUCCEEDED(D3D12CreateDevice(warp.Get(),D3D_FEATURE_LEVEL_11_0,
                                             IID_PPV_ARGS(&device))));
    D3D12_COMMAND_QUEUE_DESC qdesc{};
    qdesc.Type=D3D12_COMMAND_LIST_TYPE_DIRECT;
    REQUIRE_V365(SUCCEEDED(device->CreateCommandQueue(
        &qdesc,IID_PPV_ARGS(&queue))));
    unsigned char model[kModelBytes];
    synthetic_model(model);
    ShytNativeFlver2AssetV363 asset{};
    asset.flver=model;asset.flver_bytes=sizeof(model);
    REQUIRE_V365(!submit_flver_d3d12_v365(device.Get(),queue.Get(),&asset,41));
    REQUIRE_V365(!submit_flver_d3d12_v365(nullptr,queue.Get(),&asset,42));
    REQUIRE_V365(!submit_flver_d3d12_v365(device.Get(),nullptr,&asset,42));
    D3D12_COMMAND_QUEUE_DESC copy_q{};
    copy_q.Type=D3D12_COMMAND_LIST_TYPE_COPY;
    ComPtr<ID3D12CommandQueue> wrong_queue;
    REQUIRE_V365(SUCCEEDED(device->CreateCommandQueue(
        &copy_q,IID_PPV_ARGS(&wrong_queue))));
    REQUIRE_V365(!submit_flver_d3d12_v365(
        device.Get(),wrong_queue.Get(),&asset,42));
    unsigned char expected[42]={0};
    std::memcpy(expected,model+kDataOffset+16,36);
    std::memcpy(expected+36,model+kDataOffset,6);
    auto upload=submit_flver_d3d12_v365(device.Get(),queue.Get(),&asset,42);
    REQUIRE_V365(upload && upload->gpu_buffer && upload->uploaded_bytes==42);
    REQUIRE_V365(upload->vertex_views.size()==1 && upload->index_views.size()==1 &&
                 upload->draws.size()==1);
    REQUIRE_V365(upload->vertex_views[0].BufferLocation==
                 upload->gpu_buffer->GetGPUVirtualAddress());
    REQUIRE_V365(upload->index_views[0].BufferLocation==
                 upload->gpu_buffer->GetGPUVirtualAddress()+36);
    REQUIRE_V365(upload->vertex_views[0].SizeInBytes==36 &&
                 upload->vertex_views[0].StrideInBytes==12);
    REQUIRE_V365(upload->index_views[0].SizeInBytes==6 &&
                 upload->index_views[0].Format==DXGI_FORMAT_R16_UINT);
    REQUIRE_V365(upload->draws[0].face_set_index==0);
    /* Submission already copied data from the immutable source to the
     * upload heap, so the caller may reuse its game-resource RAM now. */
    std::memset(model,0,sizeof(model));
    REQUIRE_V365(upload->wait_for(30000));
    REQUIRE_V365(upload->ready() && !upload->submitted &&
                 !upload->staging_upload && !upload->command_allocator);
    REQUIRE_V365(readback_matches(device.Get(),queue.Get(),
                                  upload->gpu_buffer.Get(),expected,sizeof(expected)));
    upload.reset();

    synthetic_model(model);
    w16(model,kDataOffset+4,99u);
    REQUIRE_V365(!submit_flver_d3d12_v365(device.Get(),queue.Get(),&asset,42));
    synthetic_model(model);
    /* A geometry-less FLVER is valid but must not create zero-length
     * GPU buffers or submit empty command lists. */
    w32(model,24,0);w32(model,32,0);w32(model,36,0);
    w32(model,0x50,0);w32(model,0x54,0);
    w32(model,12,0x80);w32(model,16,0);
    auto empty=submit_flver_d3d12_v365(device.Get(),queue.Get(),&asset,0);
    REQUIRE_V365(empty && !empty->gpu_buffer && empty->uploaded_bytes==0 &&
                 empty->vertex_views.empty() && empty->draws.empty());
    REQUIRE_V365(empty->wait_for(0));
    return true;
}
int main() {
    if (!test_warp_d3d12_v365()) return 1;
    std::puts("NATIVE_V365_D3D12_WARP_REAL_GPU_UPLOAD_READBACK_PASS");
    return 0;
}
