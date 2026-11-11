/* SPDX-License-Identifier: GPL-2.0-or-later
 * V366: platform-neutral ring offset and fence scheduler (no allocations).
 */
#include "native_fence_upload_ring_v366.h"
#include <cstdint>
#include <limits>
namespace shyt_native_v366 {
FenceUploadRingV366::FenceUploadRingV366(uint64_t bytes) noexcept {
    if (bytes > 0 && bytes <= kMaxCapacity) capacity_=bytes;
}
bool FenceUploadRingV366::reserve(
    uint64_t bytes, uint32_t alignment, RingSliceV366* out) noexcept {
    if (!out) return false;
    *out=RingSliceV366{};
    if (!valid() || active_ || count_==kMaxPending || !bytes ||
        bytes>capacity_ || !alignment || alignment>65536u ||
        (alignment & (alignment-1u)) || alignment>capacity_ ||
        next_token_==UINT64_MAX) return false;
    /* Normalize monotonic cursors only after every GPU slice retires.
     * Prevents uint64 wrap without ever altering a live reservation. */
    if (!count_ && head_==tail_) {
        head_=0;
        tail_=0;
    }
    const uint64_t physical=head_%capacity_;
    const uint64_t mask=static_cast<uint64_t>(alignment)-1u;
    if (physical>UINT64_MAX-mask) return false;
    uint64_t aligned=(physical+mask)&~mask;
    uint64_t padding=aligned-physical;
    if (aligned>capacity_ || bytes>capacity_-aligned) {
        padding=capacity_-physical;
        aligned=0;
    }
    /* Verify occupancy before adding padded bytes, without overflow. */
    if (head_<tail_ || head_-tail_>capacity_ ||
        padding>capacity_-(head_-tail_) ||
        bytes>capacity_-(head_-tail_)-padding ||
        head_>UINT64_MAX-padding ||
        head_+padding>UINT64_MAX-bytes)
        return false;
    previous_head_=head_;
    head_+=padding+bytes;
    active_slice_={aligned,bytes,++next_token_};
    active_=true;
    *out=active_slice_;
    return true;
}
bool FenceUploadRingV366::commit(
    const RingSliceV366& slice, uint64_t signaled_fence) noexcept {
    if (!valid() || !active_ || count_==kMaxPending ||
        slice.token!=active_slice_.token ||
        slice.offset!=active_slice_.offset ||
        slice.bytes!=active_slice_.bytes ||
        signaled_fence==UINT64_MAX ||
        signaled_fence<=last_fence_ ||
        signaled_fence<=completed_)
        return false;
    const uint32_t index=(first_+count_)%kMaxPending;
    queue_[index]={head_,signaled_fence};
    ++count_;
    active_=false;
    active_slice_={};
    last_fence_=signaled_fence;
    return true;
}
bool FenceUploadRingV366::cancel(const RingSliceV366& slice) noexcept {
    if (!valid() || !active_ ||
        slice.token!=active_slice_.token ||
        slice.offset!=active_slice_.offset ||
        slice.bytes!=active_slice_.bytes)
        return false;
    head_=previous_head_;
    active_=false;
    active_slice_={};
    return true;
}
uint32_t FenceUploadRingV366::retire(uint64_t completed) noexcept {
    if (!valid()) return 0;
    if (completed==UINT64_MAX) {
        device_lost_=true;
        return 0; /* Never confuse a removed GPU with completed work. */
    }
    if (completed<completed_) return 0;
    completed_=completed;
    uint32_t released=0;
    while(count_) {
        const Pending& current=queue_[first_];
        if (current.fence>completed) break;
        tail_=current.end_cursor;
        queue_[first_]={};
        first_=(first_+1u)%kMaxPending;
        --count_;
        ++released;
    }
    return released;
}
} // namespace shyt_native_v366
