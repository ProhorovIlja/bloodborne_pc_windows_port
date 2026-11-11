/* SPDX-License-Identifier: GPL-2.0-or-later
 * First actual Windows D3D12 GPU upload backend for source-only Bloodborne
 * FLVER resource paths. No game executable, HLE, guest ABI or GPU shaders.
 */
#include "native_d3d12_flver_upload_v365.h"
#include <windows.h>
#include <cstdint>
#include <cstring>
#include <limits>
#include <new>
#include <utility>

using Microsoft::WRL::ComPtr;
namespace shyt_native_v365 {
namespace {
constexpr uint64_t kMaxStagingBytes = 256ull * 1024ull * 1024ull;
constexpr uint32_t kMaxBufferViews = 4096u;
constexpr uint32_t kMaxDrawRecords = 131072u;

static D3D12_HEAP_PROPERTIES heap_properties(D3D12_HEAP_TYPE type) noexcept {
    D3D12_HEAP_PROPERTIES p{};
    p.Type = type;
    p.CPUPageProperty = D3D12_CPU_PAGE_PROPERTY_UNKNOWN;
    p.MemoryPoolPreference = D3D12_MEMORY_POOL_UNKNOWN;
    p.CreationNodeMask = 1;
    p.VisibleNodeMask = 1;
    return p;
}
static D3D12_RESOURCE_DESC buffer_description(uint64_t bytes) noexcept {
    D3D12_RESOURCE_DESC r{};
    r.Dimension = D3D12_RESOURCE_DIMENSION_BUFFER;
    r.Width = bytes;
    r.Height = 1;
    r.DepthOrArraySize = 1;
    r.MipLevels = 1;
    r.Format = DXGI_FORMAT_UNKNOWN;
    r.SampleDesc.Count = 1;
    r.SampleDesc.Quality = 0;
    r.Layout = D3D12_TEXTURE_LAYOUT_ROW_MAJOR;
    r.Flags = D3D12_RESOURCE_FLAG_NONE;
    return r;
}
static bool in_allocation(uint64_t start,uint64_t bytes,uint64_t total) noexcept {
    return start <= total && bytes <= total-start;
}
}

UploadV365::~UploadV365() {
    if (submitted && !ready()) {
        /* A caller that destroys an incomplete ticket must still retain the
         * mapped source and allocator until the GPU is finished. This may
         * block: applications should poll and retire off the render thread. */
        (void)wait_for(INFINITE);
    }
}
bool UploadV365::ready() const noexcept {
    if (!submitted) return true;
    if (!completion_fence) return false;
    const uint64_t value=completion_fence->GetCompletedValue();
    /* UINT64_MAX is D3D12's device-removal sentinel, not completion. */
    return value!=UINT64_MAX && value>=completion_value;
}
bool UploadV365::wait_for(uint32_t timeout_milliseconds) noexcept {
    if (!submitted) return true;
    if (!completion_fence) return false;
    if (completion_fence->GetCompletedValue()==UINT64_MAX) {
        /* The device is removed. No submitted GPU commands can finish.
         * Releasing the now-dead device's staging memory is safe, but
         * report failure rather than falsely reporting a completed copy. */
        staging_upload.Reset();
        command_list.Reset();
        command_allocator.Reset();
        submitted=false;
        return false;
    }
    if (!ready()) {
        const HANDLE event_handle = CreateEventW(nullptr, FALSE, FALSE, nullptr);
        if (!event_handle) return false;
        const HRESULT hr = completion_fence->SetEventOnCompletion(
            completion_value,event_handle);
        if (FAILED(hr)) {
            CloseHandle(event_handle);
            return false;
        }
        const DWORD result = WaitForSingleObject(event_handle,timeout_milliseconds);
        CloseHandle(event_handle);
        if (result != WAIT_OBJECT_0 || !ready()) return false;
    }
    /* The queue has executed the barrier, so UPLOAD RAM and the command
     * allocator/list can now be released while the GPU DEFAULT heap lives. */
    staging_upload.Reset();
    command_list.Reset();
    command_allocator.Reset();
    completion_fence.Reset();
    submitted = false;
    return true;
}

std::unique_ptr<UploadV365> submit_flver_d3d12_v365(
    ID3D12Device* device, ID3D12CommandQueue* direct_queue,
    const ShytNativeFlver2AssetV363* model, uint64_t staging_budget_bytes) {
    if (!device || !direct_queue || !model ||
        direct_queue->GetDesc().Type != D3D12_COMMAND_LIST_TYPE_DIRECT)
        return nullptr;
    /* A queue from a different D3D12 device must never receive our
     * resources. COM IUnknown identity avoids comparing interface views. */
    ComPtr<ID3D12Device> queue_device;
    ComPtr<IUnknown> own_identity;
    ComPtr<IUnknown> queue_identity;
    if (FAILED(direct_queue->GetDevice(IID_PPV_ARGS(&queue_device))) ||
        FAILED(device->QueryInterface(IID_PPV_ARGS(&own_identity))) ||
        FAILED(queue_device->QueryInterface(IID_PPV_ARGS(&queue_identity))) ||
        own_identity.Get()!=queue_identity.Get())
        return nullptr;
    ShytNativeGpuUploadCountsV364 counts{};
    if (!shyt_native_flver2_gpu_requirements_v364(model,&counts) ||
        counts.vertex_buffers > kMaxBufferViews ||
        counts.index_buffers > kMaxBufferViews ||
        counts.draws > kMaxDrawRecords ||
        counts.staging_bytes_total > kMaxStagingBytes ||
        counts.staging_bytes_total > staging_budget_bytes)
        return nullptr;
    try {
        auto ticket = std::make_unique<UploadV365>();
        std::vector<ShytNativeGpuVertexSpanV364> vertices(counts.vertex_buffers);
        std::vector<ShytNativeGpuIndexSpanV364> indices(counts.index_buffers);
        ticket->draws.resize(counts.draws);
        ShytNativeGpuUploadCountsV364 plan{};
        if (!shyt_native_flver2_gpu_plan_v364(
                model,vertices.data(),vertices.size(),
                indices.data(),indices.size(),
                ticket->draws.data(),ticket->draws.size(),
                staging_budget_bytes,&plan)) return nullptr;
        if (counts.vertex_buffers != plan.vertex_buffers ||
            counts.index_buffers != plan.index_buffers ||
            counts.draws != plan.draws ||
            counts.staging_bytes_total != plan.staging_bytes_total)
            return nullptr;
        ticket->uploaded_bytes=plan.staging_bytes_total;
        if (!plan.staging_bytes_total) return ticket; // valid empty model

        /* D3D12 heap sizes may exceed the logical byte count because of
         * internal 64 KiB alignment. The plan's cap is a logical cap. */
        const D3D12_RESOURCE_DESC desc=buffer_description(plan.staging_bytes_total);
        const D3D12_HEAP_PROPERTIES upload_props=heap_properties(D3D12_HEAP_TYPE_UPLOAD);
        const D3D12_HEAP_PROPERTIES default_props=heap_properties(D3D12_HEAP_TYPE_DEFAULT);
        if (FAILED(device->CreateCommittedResource(
                &upload_props,D3D12_HEAP_FLAG_NONE,&desc,
                D3D12_RESOURCE_STATE_GENERIC_READ,nullptr,
                IID_PPV_ARGS(&ticket->staging_upload))) ||
            FAILED(device->CreateCommittedResource(
                &default_props,D3D12_HEAP_FLAG_NONE,&desc,
                D3D12_RESOURCE_STATE_COPY_DEST,nullptr,
                IID_PPV_ARGS(&ticket->gpu_buffer))))
            return nullptr;
        void* mapped=nullptr;
        const D3D12_RANGE no_read={0,0};
        if (FAILED(ticket->staging_upload->Map(0,&no_read,&mapped)) || !mapped)
            return nullptr;
        auto* dest=static_cast<unsigned char*>(mapped);
        std::memset(dest,0,static_cast<size_t>(plan.staging_bytes_total));
        bool copied=true;
        for (const auto& v:vertices) {
            if (!v.bytes) continue;
            if (!in_allocation(v.staging_offset,v.bytes,plan.staging_bytes_total)) {
                copied=false;break;
            }
            size_t written=0;
            if (!shyt_native_flver2_stage_bytes_v364(
                    model,v.source_offset,v.bytes,dest+v.staging_offset,
                    static_cast<size_t>(plan.staging_bytes_total-v.staging_offset),
                    &written) || written!=v.bytes) {copied=false;break;}
        }
        if (copied) for (const auto& i:indices) {
            if (!i.bytes) continue;
            if (!in_allocation(i.staging_offset,i.bytes,plan.staging_bytes_total)) {
                copied=false;break;
            }
            size_t written=0;
            if (!shyt_native_flver2_stage_bytes_v364(
                    model,i.source_offset,i.bytes,dest+i.staging_offset,
                    static_cast<size_t>(plan.staging_bytes_total-i.staging_offset),
                    &written) || written!=i.bytes) {copied=false;break;}
        }
        const D3D12_RANGE written_range={0,static_cast<SIZE_T>(plan.staging_bytes_total)};
        ticket->staging_upload->Unmap(0,&written_range);
        if (!copied) return nullptr;
        const D3D12_GPU_VIRTUAL_ADDRESS gpu=ticket->gpu_buffer->GetGPUVirtualAddress();
        if (!gpu || gpu>UINT64_MAX-plan.staging_bytes_total)
            return nullptr;
        ticket->vertex_views.reserve(vertices.size());
        for (const auto& v:vertices) {
            if (!in_allocation(v.staging_offset,v.bytes,plan.staging_bytes_total))
                return nullptr;
            D3D12_VERTEX_BUFFER_VIEW view{};
            view.BufferLocation=gpu+v.staging_offset;
            view.SizeInBytes=v.bytes;
            view.StrideInBytes=v.vertex_stride;
            ticket->vertex_views.push_back(view);
        }
        ticket->index_views.reserve(indices.size());
        for (const auto& i:indices) {
            if (!in_allocation(i.staging_offset,i.bytes,plan.staging_bytes_total) ||
                (i.index_element_bytes!=2 && i.index_element_bytes!=4))
                return nullptr;
            D3D12_INDEX_BUFFER_VIEW view{};
            view.BufferLocation=gpu+i.staging_offset;
            view.SizeInBytes=i.bytes;
            view.Format=i.index_element_bytes==2 ? DXGI_FORMAT_R16_UINT : DXGI_FORMAT_R32_UINT;
            ticket->index_views.push_back(view);
        }
        if (FAILED(device->CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_DIRECT,
                IID_PPV_ARGS(&ticket->command_allocator))) ||
            FAILED(device->CreateCommandList(0,D3D12_COMMAND_LIST_TYPE_DIRECT,
                ticket->command_allocator.Get(),nullptr,
                IID_PPV_ARGS(&ticket->command_list))) ||
            FAILED(device->CreateFence(0,D3D12_FENCE_FLAG_NONE,
                IID_PPV_ARGS(&ticket->completion_fence))))
            return nullptr;

        ticket->command_list->CopyBufferRegion(
            ticket->gpu_buffer.Get(),0,ticket->staging_upload.Get(),0,
            plan.staging_bytes_total);
        D3D12_RESOURCE_BARRIER barrier{};
        barrier.Type=D3D12_RESOURCE_BARRIER_TYPE_TRANSITION;
        barrier.Flags=D3D12_RESOURCE_BARRIER_FLAG_NONE;
        barrier.Transition.pResource=ticket->gpu_buffer.Get();
        barrier.Transition.Subresource=D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES;
        barrier.Transition.StateBefore=D3D12_RESOURCE_STATE_COPY_DEST;
        barrier.Transition.StateAfter=static_cast<D3D12_RESOURCE_STATES>(
            D3D12_RESOURCE_STATE_VERTEX_AND_CONSTANT_BUFFER |
            D3D12_RESOURCE_STATE_INDEX_BUFFER);
        ticket->command_list->ResourceBarrier(1,&barrier);
        if (FAILED(ticket->command_list->Close())) return nullptr;
        ID3D12CommandList* const lists[]={ticket->command_list.Get()};
        direct_queue->ExecuteCommandLists(1,lists);
        /* All objects referenced by the submitted list remain owned by
         * the ticket until its queue fence advances. */
        ticket->completion_value=1;
        ticket->submitted=true;
        if (FAILED(direct_queue->Signal(ticket->completion_fence.Get(),1)))
            return nullptr; // destructor waits if submission survives
        return ticket;
    } catch (const std::bad_alloc&) {
        return nullptr;
    }
}
} // namespace shyt_native_v365
