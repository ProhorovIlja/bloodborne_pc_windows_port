/* SPDX-License-Identifier: GPL-2.0-or-later
 * Synthetic-only allocation/fence scenarios for Native V366.
 */
#include "native_fence_upload_ring_v366.h"
#include <cassert>
#include <cstdint>
#include <cstdio>
using namespace shyt_native_v366;
static void deterministic() {
    FenceUploadRingV366 r(128);
    assert(r.valid() && r.capacity()==128 && r.pending()==0);
    RingSliceV366 one{},two{},three{},bad{};
    assert(!r.reserve(0,16,&bad));
    assert(!r.reserve(1,3,&bad));
    assert(!r.reserve(1,256,&bad));
    assert(!r.reserve(129,4,&bad));
    assert(!r.reserve(1,4,nullptr));
    assert(r.reserve(48,16,&one));
    assert(one.offset==0 && one.bytes==48 && one.token!=0);
    assert(!r.reserve(1,1,&bad) && r.has_unsubmitted());
    assert(!r.commit(one,0));
    assert(!r.commit(RingSliceV366{1,48,one.token},1));
    assert(!r.cancel(RingSliceV366{0,48,one.token+1}));
    assert(r.commit(one,1));
    assert(!r.commit(one,2) && !r.cancel(one));
    assert(r.reserve(48,16,&two));
    assert(two.offset==48 && two.bytes==48 && two.token>one.token);
    assert(!r.commit(two,1)); // distinct GPU fence after each submission
    assert(r.commit(two,2));
    assert(r.pending()==2 && r.used()==96);
    assert(!r.reserve(40,16,&bad)); // cannot wrap into pending slice
    assert(r.retire(0)==0 && r.pending()==2);
    assert(r.retire(1)==1 && r.pending()==1 && r.used()==48);
    assert(r.reserve(48,16,&three));
    assert(three.offset==0 && three.token>two.token);
    assert(r.used()==128);
    assert(!r.reserve(1,1,&bad));
    assert(r.commit(three,3));
    assert(r.retire(0)==0); // stale completed watermark
    assert(r.retire(2)==1 && r.pending()==1 && r.used()==80);
    assert(r.retire(3)==1 && r.pending()==0 && r.used()==0);
    assert(r.available()==128);
    RingSliceV366 reset{};
    assert(r.reserve(128,1,&reset));
    assert(reset.offset==0 && r.used()==128);
    assert(r.cancel(reset) && r.used()==0 && !r.has_unsubmitted());
    assert(!r.cancel(reset));
    assert(r.reserve(1,1,&reset) && reset.offset==0);
    assert(!r.commit(reset,2)); // cannot regress below completed 3
    assert(r.cancel(reset));
    assert(r.reserve(1,1,&reset));
    assert(r.commit(reset,4) && r.retire(4)==1);
}
static void wrap_alignment() {
    FenceUploadRingV366 r(100); // physical capacity intentionally not pow2
    RingSliceV366 a{},b{},c{};
    assert(r.reserve(19,16,&a) && a.offset==0 && r.commit(a,1));
    assert(r.reserve(9,16,&b) && b.offset==32 && r.commit(b,2));
    assert(r.retire(1)==1);
    assert(r.reserve(40,16,&c) && c.offset==48 && r.commit(c,3));
    assert(r.retire(3)==2);
    assert(r.reserve(16,16,&a) && a.offset==0);
    assert(r.cancel(a));
    assert(!FenceUploadRingV366(0).valid());
    assert(!FenceUploadRingV366(FenceUploadRingV366::kMaxCapacity+1).valid());
    assert(FenceUploadRingV366(1).valid());
}
static void slots_and_device_loss() {
    FenceUploadRingV366 r(1024);
    RingSliceV366 current{};
    for(uint32_t i=1;i<=FenceUploadRingV366::kMaxPending;++i) {
        assert(r.reserve(1,1,&current));
        assert(r.commit(current,i));
    }
    assert(r.pending()==FenceUploadRingV366::kMaxPending);
    assert(!r.reserve(1,1,&current));
    assert(r.retire(128)==128);
    assert(r.pending()==128);
    assert(r.reserve(32,16,&current) && r.commit(current,257));
    assert(r.retire(257)==129 && r.pending()==0);
    assert(r.retire(UINT64_MAX)==0 && r.device_lost());
    assert(!r.valid() && !r.reserve(1,1,&current));
    assert(r.retire(UINT64_MAX)==0);
}
static uint32_t rng=0x9e3779b9u;
static uint32_t next_random() {
    rng^=rng<<13; rng^=rng>>17; rng^=rng<<5;
    return rng;
}
static void simulate_many() {
    FenceUploadRingV366 r(1024);
    /* Synthetic CPU shadow: a committed ring region stays immutable until
     * its own fence has completed, even when other slices are retired. */
    struct Entry {uint64_t offset,bytes,fence;};
    Entry in_flight[256]{};
    uint32_t first=0,count=0;
    uint64_t last_fence=0,completed=0;
    for(uint32_t attempt=0;attempt<50000;++attempt) {
        if (count && (next_random()%3u)==0) {
            const uint32_t to_retire=1u+(next_random()%count);
            completed=in_flight[(first+to_retire-1u)%256u].fence;
            const uint32_t actual=r.retire(completed);
            assert(actual==to_retire);
            first=(first+to_retire)%256u;
            count-=to_retire;
        }
        const uint64_t bytes=1u+(next_random()%96u);
        const uint32_t alignment=1u<<(next_random()%7u);
        RingSliceV366 slice{};
        if (!r.reserve(bytes,alignment,&slice)) continue;
        assert(slice.offset%alignment==0);
        assert(slice.offset+slice.bytes<=r.capacity());
        assert(r.used()<=r.capacity());
        for(uint32_t i=0;i<count;++i) {
            const Entry& other=in_flight[(first+i)%256];
            assert(slice.offset+slice.bytes<=other.offset ||
                   other.offset+other.bytes<=slice.offset);
        }
        if ((next_random()%9u)==0) {
            assert(r.cancel(slice));
            continue;
        }
        ++last_fence;
        assert(r.commit(slice,last_fence));
        in_flight[(first+count)%256u]={slice.offset,slice.bytes,last_fence};
        ++count;
        assert(count==r.pending());
    }
    assert(r.retire(last_fence)==count);
    assert(r.pending()==0 && r.used()==0);
}
int main() {
    deterministic();
    wrap_alignment();
    slots_and_device_loss();
    simulate_many();
    std::puts("NATIVE_V366_SYNTHETIC_FENCE_RING_50000_SCENARIOS_PASS");
}
