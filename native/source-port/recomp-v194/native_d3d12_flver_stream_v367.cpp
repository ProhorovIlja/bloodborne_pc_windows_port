/* SPDX-License-Identifier: GPL-2.0-or-later
 * V367: persistent Win64 D3D12 UPLOAD memory, shared fence + FLVER stream.
 * No original game data, PS4 EBOOT/ELF, emulator or runtime translation.
 */
#include "native_d3d12_flver_stream_v367.h"
#include <windows.h>
#include <cstdint>
#include <cstring>
#include <new>
#include <utility>
using Microsoft::WRL::ComPtr;
namespace shyt_native_v367 {
namespace {
constexpr uint32_t kMaxViews=4096;
constexpr uint32_t kMaxDraws=131072;
D3D12_HEAP_PROPERTIES heap_v367(D3D12_HEAP_TYPE type) noexcept {
    D3D12_HEAP_PROPERTIES h{};
    h.Type=type;
    h.CPUPageProperty=D3D12_CPU_PAGE_PROPERTY_UNKNOWN;
    h.MemoryPoolPreference=D3D12_MEMORY_POOL_UNKNOWN;
    h.CreationNodeMask=1;
    h.VisibleNodeMask=1;
    return h;
}
D3D12_RESOURCE_DESC desc_v367(uint64_t bytes) noexcept {
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
bool bounded_v367(uint64_t start,uint64_t bytes,uint64_t limit) noexcept {
    return start<=limit && bytes<=limit-start;
}
bool same_device_v367(ID3D12Device* device,ID3D12CommandQueue* queue) noexcept {
    if (!device || !queue ||
        queue->GetDesc().Type!=D3D12_COMMAND_LIST_TYPE_DIRECT)
        return false;
    ComPtr<ID3D12Device> from_queue;
    ComPtr<IUnknown> a,b;
    return SUCCEEDED(queue->GetDevice(IID_PPV_ARGS(&from_queue))) &&
           SUCCEEDED(device->QueryInterface(IID_PPV_ARGS(&a))) &&
           SUCCEEDED(from_queue->QueryInterface(IID_PPV_ARGS(&b))) &&
           a.Get()==b.Get();
}
}
D3D12FlverStreamV367::~D3D12FlverStreamV367() {
    if (!lost_ && !in_flight_.empty()) {
        /* Intentionally blocking destructor: call retire_completed from
         * an asset worker or explicit wait_for before releasing stream.
         * Never destroy a live stream on a latency-critical frame thread. */
        (void)wait_for(in_flight_.back().fence,INFINITE);
    }
    if (mapped_ && staging_) {
        const D3D12_RANGE no_write={0,0};
        staging_->Unmap(0,&no_write);
    }
}
bool D3D12FlverStreamV367::initialize(
    ID3D12Device* device,ID3D12CommandQueue* direct_queue,
    uint64_t capacity) noexcept {
    if (device_ || ring_ || !same_device_v367(device,direct_queue) ||
        capacity<4 || capacity>shyt_native_v366::FenceUploadRingV366::kMaxCapacity ||
        (capacity&3u))
        return false;
    try {
        auto ring=std::make_unique<shyt_native_v366::FenceUploadRingV366>(capacity);
        if (!ring->valid()) return false;
        const auto props=heap_v367(D3D12_HEAP_TYPE_UPLOAD);
        const auto desc=desc_v367(capacity);
        ComPtr<ID3D12Resource> upload;
        ComPtr<ID3D12Fence> fence;
        if (FAILED(device->CreateCommittedResource(
                &props,D3D12_HEAP_FLAG_NONE,&desc,
                D3D12_RESOURCE_STATE_GENERIC_READ,nullptr,
                IID_PPV_ARGS(&upload))) ||
            FAILED(device->CreateFence(0,D3D12_FENCE_FLAG_NONE,
                IID_PPV_ARGS(&fence))))
            return false;
        void* mapped=nullptr;
        const D3D12_RANGE no_read={0,0};
        if (FAILED(upload->Map(0,&no_read,&mapped)) || !mapped)
            return false;
        device_=device;
        queue_=direct_queue;
        staging_=std::move(upload);
        fence_=std::move(fence);
        ring_=std::move(ring);
        mapped_=static_cast<unsigned char*>(mapped);
        return true;
    } catch (const std::bad_alloc&) {
        return false;
    }
}
uint64_t D3D12FlverStreamV367::used_bytes() const noexcept {
    return ring_?ring_->used():0;
}
uint32_t D3D12FlverStreamV367::pending() const noexcept {
    return static_cast<uint32_t>(in_flight_.size());
}
uint32_t D3D12FlverStreamV367::retire_completed() noexcept {
    if (!ring_ || !fence_ || lost_ || submitted_without_signal_) return 0;
    const uint64_t value=fence_->GetCompletedValue();
    if (value==UINT64_MAX) {
        lost_=true;
        ring_->retire(UINT64_MAX);
        return 0;
    }
    const uint32_t n=ring_->retire(value);
    while (!in_flight_.empty() && in_flight_.front().fence<=value)
        in_flight_.pop_front();
    return n;
}
bool D3D12FlverStreamV367::is_complete(uint64_t value) noexcept {
    if (!ring_ || lost_) return false;
    if (value==0) return true; // empty model
    if (value>next_fence_ || !fence_) return false;
    const uint64_t completed=fence_->GetCompletedValue();
    if (completed==UINT64_MAX) {
        retire_completed(); // mark device lost
        return false;
    }
    return completed>=value;
}
bool D3D12FlverStreamV367::wait_for(uint64_t value,uint32_t timeout) noexcept {
    if (!ring_ || lost_ || submitted_without_signal_ || value>next_fence_)
        return false;
    if (value==0) return true;
    if (is_complete(value)) {
        retire_completed();
        return !lost_;
    }
    HANDLE event_handle=CreateEventW(nullptr,FALSE,FALSE,nullptr);
    if (!event_handle) return false;
    const HRESULT hr=fence_->SetEventOnCompletion(value,event_handle);
    const DWORD result=SUCCEEDED(hr)?
        WaitForSingleObject(event_handle,timeout):WAIT_FAILED;
    CloseHandle(event_handle);
    if (result!=WAIT_OBJECT_0 || !is_complete(value)) return false;
    retire_completed();
    return !lost_;
}
bool D3D12FlverStreamV367::submit_flver(
    const ShytNativeFlver2AssetV363* model,
    std::unique_ptr<UploadedModelV367>* out) noexcept {
    if (!out) return false;
    out->reset();
    if (!ring_ || !model || lost_ || submitted_without_signal_ ||
        !mapped_ || !device_ || !queue_ || !fence_) return false;
    retire_completed();
    if (lost_ || next_fence_>=UINT64_MAX-1) return false;
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
        auto result=std::make_unique<UploadedModelV367>();
        std::vector<ShytNativeGpuVertexSpanV364> vertices(counts.vertex_buffers);
        std::vector<ShytNativeGpuIndexSpanV364> indices(counts.index_buffers);
        result->draws.resize(counts.draws);
        ShytNativeGpuUploadCountsV364 plan{};
        if (!shyt_native_flver2_gpu_plan_v364(
                model,vertices.data(),vertices.size(),
                indices.data(),indices.size(),
                result->draws.data(),result->draws.size(),
                ring_->capacity(),&plan) ||
            plan.staging_bytes_total!=counts.staging_bytes_total)
            return false;
        result->bytes=plan.staging_bytes_total;
        if (!plan.staging_bytes_total) {
            *out=std::move(result);
            return true;
        }
        if (!ring_->reserve(plan.staging_bytes_total,4,&slice)) return false;
        reserved=true;
        /* Every failure before ExecuteCommandLists may undo reservation.
         * Do not use ring.cancel once GPU execution has been enqueued. */
        bool staged=true;
        std::memset(mapped_+slice.offset,0,static_cast<size_t>(slice.bytes));
        for (const auto& v:vertices) {
            if (!v.bytes) continue;
            size_t written=0;
            if (!bounded_v367(v.staging_offset,v.bytes,slice.bytes) ||
                !shyt_native_flver2_stage_bytes_v364(
                    model,v.source_offset,v.bytes,
                    mapped_+slice.offset+v.staging_offset,
                    static_cast<size_t>(slice.bytes-v.staging_offset),
                    &written) || written!=v.bytes) {
                staged=false;break;
            }
        }
        if (staged) for (const auto& i:indices) {
            if (!i.bytes) continue;
            size_t written=0;
            if (!bounded_v367(i.staging_offset,i.bytes,slice.bytes) ||
                !shyt_native_flver2_stage_bytes_v364(
                    model,i.source_offset,i.bytes,
                    mapped_+slice.offset+i.staging_offset,
                    static_cast<size_t>(slice.bytes-i.staging_offset),
                    &written) || written!=i.bytes) {
                staged=false;break;
            }
        }
        if (!staged) {
            ring_->cancel(slice);
            reserved=false;
            return false;
        }
        const auto default_props=heap_v367(D3D12_HEAP_TYPE_DEFAULT);
        const auto desc=desc_v367(plan.staging_bytes_total);
        Pending pending{};
        pending.fence=next_fence_+1;
        if (FAILED(device_->CreateCommittedResource(
                &default_props,D3D12_HEAP_FLAG_NONE,&desc,
                D3D12_RESOURCE_STATE_COPY_DEST,nullptr,
                IID_PPV_ARGS(&result->gpu_buffer))) ||
            FAILED(device_->CreateCommandAllocator(
                D3D12_COMMAND_LIST_TYPE_DIRECT,
                IID_PPV_ARGS(&pending.allocator))) ||
            FAILED(device_->CreateCommandList(
                0,D3D12_COMMAND_LIST_TYPE_DIRECT,pending.allocator.Get(),
                nullptr,IID_PPV_ARGS(&pending.list)))) {
            ring_->cancel(slice);
            reserved=false;
            return false;
        }
        const auto gpu=result->gpu_buffer->GetGPUVirtualAddress();
        if (!gpu || gpu>UINT64_MAX-plan.staging_bytes_total) {
            ring_->cancel(slice);
            reserved=false;
            return false;
        }
        result->vertices.reserve(vertices.size());
        result->indices.reserve(indices.size());
        for (const auto& v:vertices) {
            if (!bounded_v367(v.staging_offset,v.bytes,plan.staging_bytes_total)) {
                ring_->cancel(slice);reserved=false;return false;
            }
            D3D12_VERTEX_BUFFER_VIEW view{};
            view.BufferLocation=gpu+v.staging_offset;
            view.SizeInBytes=v.bytes;
            view.StrideInBytes=v.vertex_stride;
            result->vertices.push_back(view);
        }
        for (const auto& i:indices) {
            if (!bounded_v367(i.staging_offset,i.bytes,plan.staging_bytes_total) ||
                (i.index_element_bytes!=2 && i.index_element_bytes!=4)) {
                ring_->cancel(slice);reserved=false;return false;
            }
            D3D12_INDEX_BUFFER_VIEW view{};
            view.BufferLocation=gpu+i.staging_offset;
            view.SizeInBytes=i.bytes;
            view.Format=i.index_element_bytes==2?
                DXGI_FORMAT_R16_UINT:DXGI_FORMAT_R32_UINT;
            result->indices.push_back(view);
        }
        pending.list->CopyBufferRegion(result->gpu_buffer.Get(),0,
            staging_.Get(),slice.offset,plan.staging_bytes_total);
        D3D12_RESOURCE_BARRIER barrier{};
        barrier.Type=D3D12_RESOURCE_BARRIER_TYPE_TRANSITION;
        barrier.Transition.pResource=result->gpu_buffer.Get();
        barrier.Transition.Subresource=D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES;
        barrier.Transition.StateBefore=D3D12_RESOURCE_STATE_COPY_DEST;
        barrier.Transition.StateAfter=static_cast<D3D12_RESOURCE_STATES>(
            D3D12_RESOURCE_STATE_VERTEX_AND_CONSTANT_BUFFER|
            D3D12_RESOURCE_STATE_INDEX_BUFFER);
        pending.list->ResourceBarrier(1,&barrier);
        if (FAILED(pending.list->Close())) {
            ring_->cancel(slice);
            reserved=false;
            return false;
        }
        pending.destination=result->gpu_buffer;
        /* No heap operations may follow ExecuteCommandLists, except
         * publishing a fully preallocated result. */
        in_flight_.push_back(std::move(pending));
        ID3D12CommandList* lists[]={in_flight_.back().list.Get()};
        queue_->ExecuteCommandLists(1,lists);
        const uint64_t signal_value=next_fence_+1;
        if (FAILED(queue_->Signal(fence_.Get(),signal_value))) {
            /* GPU may still be using memory. Never cancel or reuse the
             * unsignaled reservation; force explicit device teardown. */
            lost_=true;
            submitted_without_signal_=true;
            return false;
        }
        if (!ring_->commit(slice,signal_value)) {
            lost_=true;  // fail closed: an enqueued slice cannot be cancelled
            return false;
        }
        reserved=false;
        next_fence_=signal_value;
        result->fence=signal_value;
        *out=std::move(result);
        return true;
    } catch (const std::bad_alloc&) {
        /* In normal OOM paths no commands were submitted. See docs:
         * pending-container insertion is the final allocating operation
         * before ExecuteCommandLists. */
        return false;
    }
}
} // namespace shyt_native_v367
