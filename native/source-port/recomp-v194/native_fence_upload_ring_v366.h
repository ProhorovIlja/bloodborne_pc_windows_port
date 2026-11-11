/* SPDX-License-Identifier: GPL-2.0-or-later
 * V366: bounded, GPU-fence-owned ring for native Windows/Linux asset staging.
 * Public synthetic data only. No PS4 code, EBOOT, ELF, Proton or Wine runtime.
 */
#ifndef SHYT_NATIVE_FENCE_UPLOAD_RING_V366_H
#define SHYT_NATIVE_FENCE_UPLOAD_RING_V366_H
#include <cstddef>
#include <cstdint>
namespace shyt_native_v366 {

/* Offset references a caller-owned, persistently mapped upload memory arena.
 * Each reservation has exactly one active owner and must be committed after
 * queue submission or cancelled before any GPU access. Copy API uses caller
 * mapped memory; this class never allocates, maps, submits or touches bytes.
 */
struct RingSliceV366 {
    uint64_t offset = 0;
    uint64_t bytes = 0;
    uint64_t token = 0;
};

class FenceUploadRingV366 final {
public:
    static constexpr uint32_t kMaxPending = 256;
    static constexpr uint64_t kMaxCapacity = 256ull * 1024ull * 1024ull;
    explicit FenceUploadRingV366(uint64_t capacity_bytes) noexcept;
    FenceUploadRingV366(const FenceUploadRingV366&) = delete;
    FenceUploadRingV366& operator=(const FenceUploadRingV366&) = delete;

    /* No allocator or API calls; strictly one uncommitted slice at a time.
     * alignment is a power of two, 1..65536. GPU upload memory is NOT owned
     * and must remain live until completed_fence has retired the slice.
     * Returned offset never crosses the physical ring boundary.
     */
    bool reserve(uint64_t bytes, uint32_t alignment, RingSliceV366* out) noexcept;
    /* Only call after successful queue submission AND signal of the chosen
     * fence. Fence numbers are strictly increasing, owned by one D3D12
     * queue or one Vulkan timeline semaphore, never mixed or reset.
     * On failure cancel only if GPU work was NOT submitted.
     */
    bool commit(const RingSliceV366& slice, uint64_t signaled_fence) noexcept;
    bool cancel(const RingSliceV366& slice) noexcept;
    /* Call only after the GPU reports actual completed fence progress.
     * UINT64_MAX is reserved for D3D12 device removal: it marks LOST
     * instead of releasing anything. Caller must tear down device first.
     * Returns number of retired reservations.
     */
    uint32_t retire(uint64_t completed_fence) noexcept;

    bool valid() const noexcept { return capacity_ != 0 && !device_lost_; }
    bool device_lost() const noexcept { return device_lost_; }
    bool has_unsubmitted() const noexcept { return active_; }
    uint32_t pending() const noexcept { return count_; }
    uint64_t capacity() const noexcept { return capacity_; }
    uint64_t used() const noexcept { return head_ - tail_; }
    uint64_t available() const noexcept {
        return capacity_ >= used() ? capacity_ - used() : 0;
    }
private:
    struct Pending {
        uint64_t end_cursor=0;
        uint64_t fence=0;
    };
    Pending queue_[kMaxPending]{};
    uint64_t capacity_=0, head_=0, tail_=0, previous_head_=0;
    uint64_t next_token_=0, last_fence_=0, completed_=0;
    RingSliceV366 active_slice_{};
    uint32_t first_=0, count_=0;
    bool active_=false, device_lost_=false;
};
} // namespace shyt_native_v366
#endif
