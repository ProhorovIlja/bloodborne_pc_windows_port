/* SPDX-License-Identifier: GPL-2.0-or-later
 * V367: persistent native Win64 D3D12 FLVER staging, ring-fence ownership.
 * No PS4 runtime, EBOOT, ELF, Wine, Proton or game-owned bytes.
 */
#ifndef SHYT_NATIVE_D3D12_FLVER_STREAM_V367_H
#define SHYT_NATIVE_D3D12_FLVER_STREAM_V367_H
#if !defined(_WIN32)
#error V367 D3D12 backend is Windows-only
#endif
#include "native_flver2_gpu_plan_v364.h"
#include "native_fence_upload_ring_v366.h"
#include <d3d12.h>
#include <wrl/client.h>
#include <cstdint>
#include <deque>
#include <memory>
#include <vector>

namespace shyt_native_v367 {
struct UploadedModelV367 {
    Microsoft::WRL::ComPtr<ID3D12Resource> gpu_buffer;
    std::vector<D3D12_VERTEX_BUFFER_VIEW> vertices;
    std::vector<D3D12_INDEX_BUFFER_VIEW> indices;
    std::vector<ShytNativeGpuDrawV364> draws;
    uint64_t bytes=0;
    uint64_t fence=0; /* 0 for a verified model containing no geometry */
};
/* One owner thread per queue, no internal lock, no blocking inside submit.
 * Retain the stream as long as any GPU operations or output draw references
 * are in flight. Per-model GPU buffers stay alive in the caller's result.
 * Shared UPLOAD heap is mapped once and reused on GPU fence completion.
 * Caller must NOT use GPU results before is_complete(fence) is true.
 */
class D3D12FlverStreamV367 final {
public:
    D3D12FlverStreamV367()=default;
    D3D12FlverStreamV367(const D3D12FlverStreamV367&)=delete;
    D3D12FlverStreamV367& operator=(const D3D12FlverStreamV367&)=delete;
    ~D3D12FlverStreamV367();
    bool initialize(ID3D12Device* device,ID3D12CommandQueue* direct_queue,
                    uint64_t upload_capacity_bytes) noexcept;
    /* Returns false for validation, OOM or GPU backpressure, without
     * blocking. out is cleared before attempting a submission. No FLVER
     * source bytes are held after successful CPU stage copy. Never
     * concurrently mutate the source file while submit executes.
     */
    bool submit_flver(const ShytNativeFlver2AssetV363* model,
                      std::unique_ptr<UploadedModelV367>* out) noexcept;
    /* Poll only; releases staging reservations & command objects once
     * their OWN fence values have actually completed on this queue.
     * A UINT64_MAX completed value means device loss, not completion.
     */
    uint32_t retire_completed() noexcept;
    bool is_complete(uint64_t fence) noexcept;
    /* Explicit wait for shutdown or worker thread, NEVER in per-file submit.
     * Timeout preserves all pending resources.
     */
    bool wait_for(uint64_t fence,uint32_t timeout_ms) noexcept;
    uint64_t used_bytes() const noexcept;
    uint32_t pending() const noexcept;
    bool device_lost() const noexcept { return lost_; }
private:
    struct Pending {
        uint64_t fence=0;
        Microsoft::WRL::ComPtr<ID3D12CommandAllocator> allocator;
        Microsoft::WRL::ComPtr<ID3D12GraphicsCommandList> list;
        Microsoft::WRL::ComPtr<ID3D12Resource> destination;
    };
    Microsoft::WRL::ComPtr<ID3D12Device> device_;
    Microsoft::WRL::ComPtr<ID3D12CommandQueue> queue_;
    Microsoft::WRL::ComPtr<ID3D12Resource> staging_;
    Microsoft::WRL::ComPtr<ID3D12Fence> fence_;
    std::unique_ptr<shyt_native_v366::FenceUploadRingV366> ring_;
    std::deque<Pending> in_flight_;
    unsigned char* mapped_=nullptr;
    uint64_t next_fence_=0;
    bool lost_=false;
    bool submitted_without_signal_=false;
};
} // namespace shyt_native_v367
#endif
