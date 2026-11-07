// SPDX-License-Identifier: GPL-2.0-or-later
// V447: original BBHost's GuestMapInfo shape, no proprietary game content.
#include "shyt_yt_bbhost_guest_memory_v447.h"
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <limits>
#include <vector>

struct GuestMapInfo {
    std::uint64_t va, len;
    std::int64_t phys;
    bool dmem;
    int prot;
};
using BloodborneCoop::SHYT::MemoryV447::GuestMapCache;

int main() {
    std::uint64_t epoch=7;
    std::vector<GuestMapInfo> maps{
        {0x4000,0x1000,-1,false,1}, // readable but not writable
        {0x8000,0x1000,-1,false,3}, // read and write
        {0xA000,0x1000,-1,false,4}, // exec-only
    };
    std::size_t snapshots=0;
    auto generation=[&](){return epoch;};
    auto snapshot=[&](std::vector<GuestMapInfo>& out){out=maps;++snapshots;};
    GuestMapCache<GuestMapInfo> cache;
    std::uintptr_t lo=0, hi=0;
    std::uint32_t prot=0;
    assert(cache.Query(0x4001,&lo,&hi,&prot,generation,snapshot));
    assert(lo==0x4000 && hi==0x5000 && prot==1);
    assert(cache.Query(0x4fff,&lo,&hi,&prot,generation,snapshot));
    assert(snapshots==1); // thousands of same-epoch reads do not rebuild it
    assert(!cache.Query(0x5000,&lo,&hi,&prot,generation,snapshot));
    assert(cache.Query(0x8000,&lo,&hi,&prot,generation,snapshot) && prot==3);
    assert(!cache.Query(0xA001,&lo,&hi,&prot,generation,snapshot));
    assert(!cache.Query(0x1111,&lo,&hi,&prot,generation,snapshot));
    assert(!cache.Query(0,&lo,&hi,&prot,generation,snapshot));
    assert(!cache.Query(0x4000,nullptr,&hi,&prot,generation,snapshot));
    assert(snapshots==1);

    // An unmap invalidates all cached reader decisions.
    maps.erase(maps.begin());
    ++epoch;
    assert(!cache.Query(0x4001,&lo,&hi,&prot,generation,snapshot));
    assert(snapshots==2 && cache.Generation()==epoch);
    assert(cache.Query(0x8001,&lo,&hi,&prot,generation,snapshot));

    // Rights changes also move the original BBHost mapping epoch.
    maps[0].prot=1;
    ++epoch;
    assert(cache.Query(0x8001,&lo,&hi,&prot,generation,snapshot) && prot==1);
    assert(snapshots==3);

    // If a remap happens during snapshotting, do not cache an incoherent view.
    ++epoch;
    const auto unstable=[&](std::vector<GuestMapInfo>& out){
        out=maps; ++epoch; ++snapshots;
    };
    assert(!cache.Query(0x8001,&lo,&hi,&prot,generation,unstable));
    assert(cache.Generation()==0 && cache.Regions()==0);
    assert(cache.Query(0x8001,&lo,&hi,&prot,generation,snapshot));

    // Malformed, overlapping and overflowing snapshots are refused.
    maps={{0x1000,0x2000,-1,false,3},{0x2000,0x1000,-1,false,3}};
    ++epoch;
    assert(!cache.Query(0x2001,&lo,&hi,&prot,generation,snapshot));
    maps={{std::numeric_limits<std::uint64_t>::max()-4,16,-1,false,3}};
    ++epoch;
    assert(!cache.Query(std::numeric_limits<std::uint64_t>::max()-2,
                        &lo,&hi,&prot,generation,snapshot));
    // On host stack, answer "unknown" rather than return fabricated guest RW.
    maps={{0x4000,0x1000,-1,false,1}};
    ++epoch;
    assert(!cache.Query(0x10000000,&lo,&hi,&prot,generation,snapshot));

    std::puts("SHYT_V447_BBHOST_ACCURATE_PERMISSION_MAP_EPOCH_CACHE_PASS");
}
