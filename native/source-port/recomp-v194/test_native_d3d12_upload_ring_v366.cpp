/* SPDX-License-Identifier: GPL-2.0-or-later
 * V366: actual Windows D3D12 WARP copy/readback with a bounded fence ring.
 * Uses invented bytes only, no original assets or game executable.
 */
#if !defined(_WIN32)
#error This V366 integration test needs Windows and D3D12 WARP
#endif
#include "native_fence_upload_ring_v366.h"
#include <d3d12.h>
#include <dxgi1_4.h>
#include <windows.h>
#include <wrl/client.h>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>
using Microsoft::WRL::ComPtr;
using shyt_native_v366::FenceUploadRingV366;
using shyt_native_v366::RingSliceV366;
#define REQUIRE_V366(expr) do { if (!(expr)) { \
    std::fprintf(stderr,"NATIVE_V366_WARP_FAILURE_AT_LINE_%d\n",__LINE__); \
    return false; } } while(0)

static D3D12_HEAP_PROPERTIES heap_v366(D3D12_HEAP_TYPE type) {
    D3D12_HEAP_PROPERTIES h{};
    h.Type=type;
    h.CPUPageProperty=D3D12_CPU_PAGE_PROPERTY_UNKNOWN;
    h.MemoryPoolPreference=D3D12_MEMORY_POOL_UNKNOWN;
    h.CreationNodeMask=1;
    h.VisibleNodeMask=1;
    return h;
}
static D3D12_RESOURCE_DESC buffer_v366(uint64_t bytes) {
    D3D12_RESOURCE_DESC d{};
    d.Dimension=D3D12_RESOURCE_DIMENSION_BUFFER;
    d.Width=bytes;
    d.Height=1;
    d.DepthOrArraySize=1;
    d.MipLevels=1;
    d.Format=DXGI_FORMAT_UNKNOWN;
    d.SampleDesc.Count=1;
    d.Layout=D3D12_TEXTURE_LAYOUT_ROW_MAJOR;
    return d;
}
static bool wait_v366(ID3D12Fence* fence,uint64_t value) {
    if (fence->GetCompletedValue()==UINT64_MAX) return false;
    if (fence->GetCompletedValue()>=value) return true;
    HANDLE evt=CreateEventW(nullptr,FALSE,FALSE,nullptr);
    if (!evt) return false;
    const HRESULT result=fence->SetEventOnCompletion(value,evt);
    const DWORD wait=SUCCEEDED(result)?WaitForSingleObject(evt,30000):WAIT_FAILED;
    CloseHandle(evt);
    return wait==WAIT_OBJECT_0 &&
           fence->GetCompletedValue()!=UINT64_MAX &&
           fence->GetCompletedValue()>=value;
}
static bool test_d3d12_ring_v366() {
    ComPtr<IDXGIFactory4> factory;
    ComPtr<IDXGIAdapter> adapter;
    ComPtr<ID3D12Device> device;
    ComPtr<ID3D12CommandQueue> queue;
    ComPtr<ID3D12Resource> upload,gpu,readback;
    ComPtr<ID3D12Fence> fence;
    REQUIRE_V366(SUCCEEDED(CreateDXGIFactory1(IID_PPV_ARGS(&factory))));
    REQUIRE_V366(SUCCEEDED(factory->EnumWarpAdapter(IID_PPV_ARGS(&adapter))));
    REQUIRE_V366(SUCCEEDED(D3D12CreateDevice(adapter.Get(),
        D3D_FEATURE_LEVEL_11_0,IID_PPV_ARGS(&device))));
    D3D12_COMMAND_QUEUE_DESC qdesc{};
    qdesc.Type=D3D12_COMMAND_LIST_TYPE_DIRECT;
    REQUIRE_V366(SUCCEEDED(device->CreateCommandQueue(&qdesc,
        IID_PPV_ARGS(&queue))));
    const D3D12_RESOURCE_DESC desc=buffer_v366(96);
    const auto up=heap_v366(D3D12_HEAP_TYPE_UPLOAD);
    const auto normal=heap_v366(D3D12_HEAP_TYPE_DEFAULT);
    const auto rb=heap_v366(D3D12_HEAP_TYPE_READBACK);
    REQUIRE_V366(SUCCEEDED(device->CreateCommittedResource(
        &up,D3D12_HEAP_FLAG_NONE,&desc,D3D12_RESOURCE_STATE_GENERIC_READ,
        nullptr,IID_PPV_ARGS(&upload))));
    REQUIRE_V366(SUCCEEDED(device->CreateCommittedResource(
        &normal,D3D12_HEAP_FLAG_NONE,&desc,D3D12_RESOURCE_STATE_COPY_DEST,
        nullptr,IID_PPV_ARGS(&gpu))));
    REQUIRE_V366(SUCCEEDED(device->CreateCommittedResource(
        &rb,D3D12_HEAP_FLAG_NONE,&desc,D3D12_RESOURCE_STATE_COPY_DEST,
        nullptr,IID_PPV_ARGS(&readback))));
    REQUIRE_V366(SUCCEEDED(device->CreateFence(
        0,D3D12_FENCE_FLAG_NONE,IID_PPV_ARGS(&fence))));
    void* mapped=nullptr;
    const D3D12_RANGE no_read={0,0};
    REQUIRE_V366(SUCCEEDED(upload->Map(0,&no_read,&mapped)) && mapped);
    auto* host=static_cast<unsigned char*>(mapped);
    std::memset(host,0,96);
    FenceUploadRingV366 ring(96);
    std::vector<ComPtr<ID3D12CommandAllocator>> allocators;
    std::vector<ComPtr<ID3D12GraphicsCommandList>> lists;
    /* Retain allocators and command lists until their fences have run.
     * In a production renderer they would be retired with the same ticket. */
    auto copy_and_signal=[&](uint64_t source,uint64_t destination,
                             uint64_t bytes,uint64_t value)->bool {
        ComPtr<ID3D12CommandAllocator> a;
        ComPtr<ID3D12GraphicsCommandList> l;
        if (FAILED(device->CreateCommandAllocator(
                D3D12_COMMAND_LIST_TYPE_DIRECT,IID_PPV_ARGS(&a))) ||
            FAILED(device->CreateCommandList(
                0,D3D12_COMMAND_LIST_TYPE_DIRECT,a.Get(),nullptr,
                IID_PPV_ARGS(&l))))
            return false;
        l->CopyBufferRegion(gpu.Get(),destination,upload.Get(),source,bytes);
        if (FAILED(l->Close())) return false;
        ID3D12CommandList* cmd[]={l.Get()};
        queue->ExecuteCommandLists(1,cmd);
        if (FAILED(queue->Signal(fence.Get(),value))) return false;
        allocators.push_back(a);
        lists.push_back(l);
        return true;
    };
    RingSliceV366 one{},two{},three{},denied{};
    REQUIRE_V366(ring.reserve(48,16,&one) && one.offset==0);
    std::memset(host+one.offset,0x31,48);
    REQUIRE_V366(copy_and_signal(one.offset,0,48,1));
    REQUIRE_V366(ring.commit(one,1));
    REQUIRE_V366(ring.reserve(48,16,&two) && two.offset==48);
    std::memset(host+two.offset,0x52,48);
    REQUIRE_V366(copy_and_signal(two.offset,48,48,2));
    REQUIRE_V366(ring.commit(two,2));
    REQUIRE_V366(ring.used()==96 && ring.pending()==2);
    REQUIRE_V366(!ring.reserve(48,16,&denied));
    /* Confirm fence 1; only then may the first region be reused.
     * The second region remains reserved even if the GPU raced ahead. */
    REQUIRE_V366(wait_v366(fence.Get(),1));
    REQUIRE_V366(ring.retire(1)==1 && ring.pending()==1);
    REQUIRE_V366(ring.reserve(48,16,&three) && three.offset==0);
    std::memset(host+three.offset,0x63,48);
    REQUIRE_V366(copy_and_signal(three.offset,0,48,3));
    REQUIRE_V366(ring.commit(three,3));
    REQUIRE_V366(wait_v366(fence.Get(),3));
    REQUIRE_V366(ring.retire(fence->GetCompletedValue())==2);
    REQUIRE_V366(ring.pending()==0 && ring.used()==0);
    /* Copy final GPU contents back via a real WARP command submission. */
    ComPtr<ID3D12CommandAllocator> read_alloc;
    ComPtr<ID3D12GraphicsCommandList> read_list;
    REQUIRE_V366(SUCCEEDED(device->CreateCommandAllocator(
        D3D12_COMMAND_LIST_TYPE_DIRECT,IID_PPV_ARGS(&read_alloc))));
    REQUIRE_V366(SUCCEEDED(device->CreateCommandList(
        0,D3D12_COMMAND_LIST_TYPE_DIRECT,read_alloc.Get(),nullptr,
        IID_PPV_ARGS(&read_list))));
    D3D12_RESOURCE_BARRIER barrier{};
    barrier.Type=D3D12_RESOURCE_BARRIER_TYPE_TRANSITION;
    barrier.Transition.pResource=gpu.Get();
    barrier.Transition.Subresource=D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES;
    barrier.Transition.StateBefore=D3D12_RESOURCE_STATE_COPY_DEST;
    barrier.Transition.StateAfter=D3D12_RESOURCE_STATE_COPY_SOURCE;
    read_list->ResourceBarrier(1,&barrier);
    read_list->CopyBufferRegion(readback.Get(),0,gpu.Get(),0,96);
    REQUIRE_V366(SUCCEEDED(read_list->Close()));
    ID3D12CommandList* cmd[]={read_list.Get()};
    queue->ExecuteCommandLists(1,cmd);
    REQUIRE_V366(SUCCEEDED(queue->Signal(fence.Get(),4)));
    REQUIRE_V366(wait_v366(fence.Get(),4));
    void* result=nullptr;
    const D3D12_RANGE valid_bytes={0,96};
    REQUIRE_V366(SUCCEEDED(readback->Map(0,&valid_bytes,&result)) && result);
    unsigned char reference[96];
    std::memset(reference,0x63,48);
    std::memset(reference+48,0x52,48);
    const bool identical=std::memcmp(result,reference,96)==0;
    readback->Unmap(0,&no_read);
    upload->Unmap(0,&no_read);
    REQUIRE_V366(identical);
    std::puts("NATIVE_V366_D3D12_WARP_REAL_TWO_FLIGHTS_REUSE_AND_READBACK_PASS");
    return true;
}
int main() {
    return test_d3d12_ring_v366()?0:1;
}
