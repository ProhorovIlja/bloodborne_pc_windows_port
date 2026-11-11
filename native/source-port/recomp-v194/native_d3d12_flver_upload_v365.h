/* SPDX-License-Identifier: GPL-2.0-or-later
 * Windows-native D3D12 staging and GPU upload for independently validated
 * FLVER2 geometry. No PS4 runtime, EBOOT loading or game-owned bytes.
 */
#ifndef SHYT_NATIVE_D3D12_FLVER_UPLOAD_V365_H
#define SHYT_NATIVE_D3D12_FLVER_UPLOAD_V365_H
#if !defined(_WIN32)
#error Native V365 D3D12 GPU upload is a Windows-only backend
#endif
#include <cstdint>
#include <memory>
#include <vector>
#include <d3d12.h>
#include <wrl/client.h>
#include "native_flver2_gpu_plan_v364.h"

namespace shyt_native_v365 {

/* The returned default-heap resource is in VERTEX_AND_CONSTANT_BUFFER |
 * INDEX_BUFFER state after copy completion. All buffer view addresses are
 * relative to this resource; caller must keep the Upload alive while using
 * them. Draw records refer to vertex/index view arrays, not GPU commands.
 *
 * Upload staging and command allocator remain alive until the fence signals.
 * Caller should poll ready() and call wait_for() or reuse the pipeline after
 * completion. Destruction of an outstanding Upload waits for the GPU; never
 * destroy pending tickets on a latency-critical render thread.
 */
struct UploadV365 {
    Microsoft::WRL::ComPtr<ID3D12Resource> gpu_buffer;
    std::vector<D3D12_VERTEX_BUFFER_VIEW> vertex_views;
    std::vector<D3D12_INDEX_BUFFER_VIEW> index_views;
    std::vector<ShytNativeGpuDrawV364> draws;
    uint64_t uploaded_bytes = 0;

    UploadV365() = default;
    UploadV365(const UploadV365&) = delete;
    UploadV365& operator=(const UploadV365&) = delete;
    ~UploadV365();

    bool ready() const noexcept;
    /* On timeout returns false and retains upload/allocator/list memory:
     * the caller can call wait_for again. Success releases temporary GPU
     * resources, not the final draw-ready buffer. */
    bool wait_for(uint32_t timeout_milliseconds) noexcept;

    /* Private lifecycle state; owned only by the in-flight transfer. */
    Microsoft::WRL::ComPtr<ID3D12Resource> staging_upload;
    Microsoft::WRL::ComPtr<ID3D12GraphicsCommandList> command_list;
    Microsoft::WRL::ComPtr<ID3D12CommandAllocator> command_allocator;
    Microsoft::WRL::ComPtr<ID3D12Fence> completion_fence;
    uint64_t completion_value = 0;
    bool submitted = false;
    bool failed = false; /* device-lost state cannot masquerade as ready */
};

/* Enqueue an actual D3D12 GPU upload; NEVER blocks for GPU completion.
 * Requires a DIRECT command queue from the same device. Will revalidate
 * the entire owner-owned FLVER and regenerate upload spans. No game data
 * are logged or published. Hard cap is 256 MiB; additionally respects the
 * caller's lower residency budget. Null means fail without submission.
 *
 * On success, the model may be released immediately: its bytes have been
 * copied into the ticket-owned UPLOAD heap. Do NOT release the ticket's
 * staging/command resources until wait_for has confirmed the fence.
 */
std::unique_ptr<UploadV365> submit_flver_d3d12_v365(
    ID3D12Device* device, ID3D12CommandQueue* direct_queue,
    const ShytNativeFlver2AssetV363* model, uint64_t staging_budget_bytes);

} // namespace shyt_native_v365
#endif
