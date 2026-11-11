/* SPDX-License-Identifier: GPL-2.0-or-later
 * Actual D3D12/WARP multi-resource FLVER uploads with ONE shared ring/fence.
 * All geometry is invented; no game executable, private assets or PS4 APIs.
 */
#include "native_d3d12_flver_stream_v367.h"
#include <dxgi1_4.h>
#include <windows.h>
#include <wrl/client.h>
#include <cstdint>
#include <cstdio>
#include <cstring>
using Microsoft::WRL::ComPtr;
using shyt_native_v367::D3D12FlverStreamV367;
using shyt_native_v367::UploadedModelV367;
#define CHECK367(x) do { if (!(x)) { \
    std::fprintf(stderr,"NATIVE_V367_FAIL_LINE_%d\n",__LINE__); \
    return false; } } while(0)

static void w16(unsigned char* p,unsigned off,uint16_t n) {
    p[off]=static_cast<unsigned char>(n);
    p[off+1]=static_cast<unsigned char>(n>>8);
}
static void w32(unsigned char* p,unsigned off,uint32_t n) {
    w16(p,off,static_cast<uint16_t>(n));
    w16(p,off+2,static_cast<uint16_t>(n>>16));
}
static constexpr unsigned kFile=0x1b4,kData=0x180;
static void synthetic_model(unsigned char (&p)[kFile],unsigned variant) {
    std::memset(p,0,sizeof(p));
    std::memcpy(p,"FLVER\0L\0",8);
    w32(p,8,0x20014);
    w32(p,12,kData);w32(p,16,52);
    w32(p,24,1);w32(p,32,1);w32(p,36,1);
    p[0x49]=1;
    w32(p,0x50,1);w32(p,0x54,1);
    p[0xa0]=1;
    w32(p,0xa0+16,UINT32_MAX);
    w32(p,0xa0+32,1);
    w32(p,0xa0+36,0x138);
    w32(p,0xa0+40,1);
    w32(p,0xa0+44,0x13c);
    p[0xd0+4]=1;p[0xd0+5]=1;
    w32(p,0xd0+8,3);w32(p,0xd0+16,6);w32(p,0xd0+24,16);
    w32(p,0xf0+8,12);w32(p,0xf0+12,3);w32(p,0xf0+24,36);w32(p,0xf0+28,16);
    w32(p,0x110,1);w32(p,0x110+12,0x120);
    w32(p,0x120+8,2);
    w16(p,kData,0);w16(p,kData+2,1);w16(p,kData+4,2);
    for(unsigned i=0;i<36;++i)
        p[kData+16+i]=static_cast<unsigned char>(i*7u+variant);
}
static D3D12_RESOURCE_DESC desc367(uint64_t bytes) {
    D3D12_RESOURCE_DESC d{};
    d.Dimension=D3D12_RESOURCE_DIMENSION_BUFFER;
    d.Width=bytes;d.Height=1;d.DepthOrArraySize=1;d.MipLevels=1;
    d.Format=DXGI_FORMAT_UNKNOWN;d.SampleDesc.Count=1;
    d.Layout=D3D12_TEXTURE_LAYOUT_ROW_MAJOR;
    return d;
}
static D3D12_HEAP_PROPERTIES props367(D3D12_HEAP_TYPE type) {
    D3D12_HEAP_PROPERTIES h{};
    h.Type=type;
    h.CPUPageProperty=D3D12_CPU_PAGE_PROPERTY_UNKNOWN;
    h.MemoryPoolPreference=D3D12_MEMORY_POOL_UNKNOWN;
    h.CreationNodeMask=1;h.VisibleNodeMask=1;
    return h;
}
static bool readback367(ID3D12Device* device,ID3D12CommandQueue* queue,
                        ID3D12Resource* gpu,const unsigned char* expected) {
    CHECK367(gpu && expected);
    const auto props=props367(D3D12_HEAP_TYPE_READBACK);
    const auto desc=desc367(42);
    ComPtr<ID3D12Resource> destination;
    ComPtr<ID3D12CommandAllocator> alloc;
    ComPtr<ID3D12GraphicsCommandList> list;
    ComPtr<ID3D12Fence> fence;
    CHECK367(SUCCEEDED(device->CreateCommittedResource(
        &props,D3D12_HEAP_FLAG_NONE,&desc,D3D12_RESOURCE_STATE_COPY_DEST,
        nullptr,IID_PPV_ARGS(&destination))));
    CHECK367(SUCCEEDED(device->CreateCommandAllocator(
        D3D12_COMMAND_LIST_TYPE_DIRECT,IID_PPV_ARGS(&alloc))));
    CHECK367(SUCCEEDED(device->CreateCommandList(
        0,D3D12_COMMAND_LIST_TYPE_DIRECT,alloc.Get(),nullptr,
        IID_PPV_ARGS(&list))));
    D3D12_RESOURCE_BARRIER barrier{};
    barrier.Type=D3D12_RESOURCE_BARRIER_TYPE_TRANSITION;
    barrier.Transition.pResource=gpu;
    barrier.Transition.Subresource=D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES;
    barrier.Transition.StateBefore=static_cast<D3D12_RESOURCE_STATES>(
        D3D12_RESOURCE_STATE_VERTEX_AND_CONSTANT_BUFFER|
        D3D12_RESOURCE_STATE_INDEX_BUFFER);
    barrier.Transition.StateAfter=D3D12_RESOURCE_STATE_COPY_SOURCE;
    list->ResourceBarrier(1,&barrier);
    list->CopyBufferRegion(destination.Get(),0,gpu,0,42);
    barrier.Transition.StateBefore=D3D12_RESOURCE_STATE_COPY_SOURCE;
    barrier.Transition.StateAfter=static_cast<D3D12_RESOURCE_STATES>(
        D3D12_RESOURCE_STATE_VERTEX_AND_CONSTANT_BUFFER|
        D3D12_RESOURCE_STATE_INDEX_BUFFER);
    list->ResourceBarrier(1,&barrier);
    CHECK367(SUCCEEDED(list->Close()));
    CHECK367(SUCCEEDED(device->CreateFence(
        0,D3D12_FENCE_FLAG_NONE,IID_PPV_ARGS(&fence))));
    ID3D12CommandList* lists[]={list.Get()};
    queue->ExecuteCommandLists(1,lists);
    CHECK367(SUCCEEDED(queue->Signal(fence.Get(),1)));
    HANDLE event=CreateEventW(nullptr,FALSE,FALSE,nullptr);
    CHECK367(event!=nullptr);
    const HRESULT event_status=fence->SetEventOnCompletion(1,event);
    const DWORD wait=SUCCEEDED(event_status)?
        WaitForSingleObject(event,30000):WAIT_FAILED;
    CloseHandle(event);
    CHECK367(wait==WAIT_OBJECT_0 && fence->GetCompletedValue()!=UINT64_MAX);
    void* mapped=nullptr;
    const D3D12_RANGE read={0,42};
    CHECK367(SUCCEEDED(destination->Map(0,&read,&mapped))&&mapped);
    const bool equal=std::memcmp(mapped,expected,42)==0;
    const D3D12_RANGE no_write={0,0};
    destination->Unmap(0,&no_write);
    CHECK367(equal);
    return true;
}
static bool test367() {
    ComPtr<IDXGIFactory4> factory;
    ComPtr<IDXGIAdapter> warp;
    ComPtr<ID3D12Device> device;
    ComPtr<ID3D12CommandQueue> queue;
    CHECK367(SUCCEEDED(CreateDXGIFactory1(IID_PPV_ARGS(&factory))));
    CHECK367(SUCCEEDED(factory->EnumWarpAdapter(IID_PPV_ARGS(&warp))));
    CHECK367(SUCCEEDED(D3D12CreateDevice(warp.Get(),D3D_FEATURE_LEVEL_11_0,
                                         IID_PPV_ARGS(&device))));
    D3D12_COMMAND_QUEUE_DESC qdesc{};
    qdesc.Type=D3D12_COMMAND_LIST_TYPE_DIRECT;
    CHECK367(SUCCEEDED(device->CreateCommandQueue(&qdesc,
                                                  IID_PPV_ARGS(&queue))));
    D3D12FlverStreamV367 invalid;
    CHECK367(!invalid.initialize(device.Get(),queue.Get(),95));
    CHECK367(!invalid.initialize(nullptr,queue.Get(),96));
    D3D12FlverStreamV367 stream;
    CHECK367(stream.initialize(device.Get(),queue.Get(),96));
    CHECK367(!stream.initialize(device.Get(),queue.Get(),96));
    unsigned char model[kFile],expected[3][42]{};
    std::unique_ptr<UploadedModelV367> first,second,third;
    for(unsigned j=0;j<2;++j) {
        synthetic_model(model,j+1);
        std::memcpy(expected[j],model+kData+16,36);
        std::memcpy(expected[j]+36,model+kData,6);
        ShytNativeFlver2AssetV363 asset{};
        asset.flver=model;asset.flver_bytes=sizeof(model);
        std::unique_ptr<UploadedModelV367> result;
        CHECK367(stream.submit_flver(&asset,&result));
        CHECK367(result && result->gpu_buffer && result->bytes==42);
        CHECK367(result->vertices.size()==1 && result->indices.size()==1);
        CHECK367(result->draws.size()==1 && result->fence==j+1);
        CHECK367(result->indices[0].BufferLocation==
                 result->gpu_buffer->GetGPUVirtualAddress()+36);
        if (j==0) first=std::move(result);
        else second=std::move(result);
        std::memset(model,0,sizeof(model)); // owner may recycle source RAM
    }
    CHECK367(stream.used_bytes()<=96);
    CHECK367(!stream.device_lost());
    CHECK367(stream.wait_for(second->fence,30000));
    CHECK367(stream.is_complete(first->fence));
    CHECK367(stream.is_complete(second->fence));
    CHECK367(stream.pending()==0 && stream.used_bytes()==0);
    CHECK367(readback367(device.Get(),queue.Get(),first->gpu_buffer.Get(),expected[0]));
    CHECK367(readback367(device.Get(),queue.Get(),second->gpu_buffer.Get(),expected[1]));
    synthetic_model(model,3);
    std::memcpy(expected[2],model+kData+16,36);
    std::memcpy(expected[2]+36,model+kData,6);
    ShytNativeFlver2AssetV363 asset{};
    asset.flver=model;asset.flver_bytes=sizeof(model);
    CHECK367(stream.submit_flver(&asset,&third));
    CHECK367(third && third->fence==3 && third->bytes==42);
    CHECK367(stream.wait_for(third->fence,30000));
    CHECK367(readback367(device.Get(),queue.Get(),third->gpu_buffer.Get(),expected[2]));
    CHECK367(stream.pending()==0 && stream.used_bytes()==0);
    w16(model,kData+4,100);
    CHECK367(!stream.submit_flver(&asset,&third));
    CHECK367(!third);
    CHECK367(stream.pending()==0 && stream.used_bytes()==0);
    synthetic_model(model,0);
    w32(model,24,0);w32(model,32,0);w32(model,36,0);
    w32(model,0x50,0);w32(model,0x54,0);
    w32(model,12,0x80);w32(model,16,0);
    CHECK367(stream.submit_flver(&asset,&third));
    CHECK367(third && !third->gpu_buffer && third->fence==0);
    CHECK367(stream.is_complete(0));
    std::puts("NATIVE_V367_WARP_REAL_PERSISTENT_TWO_RESOURCE_FLVER_GPU_READBACK_PASS");
    return true;
}
int main(){return test367()?0:1;}
