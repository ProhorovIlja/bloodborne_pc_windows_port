// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V447: opt-in BBHost guest map snapshot for original CLS YT v1.4.0.
// MemoryWindows may cache only guest mappings whose generation changes when
// the original BBHost kernel mapping table changes. Stack/host pages are NOT
// admitted here: YT's existing HostRegion asks Windows for those.
//
// This is an admission helper, NOT a proof of race-free dereference after a
// guest unmaps memory on another thread. In-game soak and crash tests required.
#include <algorithm>
#include <cstdint>
#include <limits>
#include <iterator>
#include <vector>

namespace BloodborneCoop::SHYT::MemoryV447 {
template <typename Region>
class GuestMapCache {
public:
    // Epoch reads and snapshot reads come from original BBHost APIs:
    // hle_kernel_maps_generation() and hle_kernel_snapshot_maps().
    // Region has .va, .len and .prot, the exact GuestMapInfo contract.
    template <typename Epoch, typename Snapshot>
    bool Query(std::uint64_t address, std::uintptr_t* start,
               std::uintptr_t* end, std::uint32_t* prot,
               Epoch&& epoch, Snapshot&& snapshot) {
        if (!start || !end || !prot || address == 0) return false;
        const std::uint64_t before = epoch();
        if (!before) return false;
        if (generation_ != before) {
            std::vector<Region> fresh;
            snapshot(fresh);  // original BBHost takes its map mutex
            const std::uint64_t after = epoch();
            if (after != before) {
                generation_ = 0;
                regions_.clear();
                return false;  // fail closed on concurrent remap
            }
            std::sort(fresh.begin(), fresh.end(),
                      [](const Region& a, const Region& b) {return a.va < b.va;});
            for (std::size_t i=0; i<fresh.size(); ++i) {
                const auto& r=fresh[i];
                if (r.len == 0 || r.va > std::numeric_limits<std::uint64_t>::max()-r.len ||
                    (i && fresh[i-1].va+fresh[i-1].len > r.va)) {
                    regions_.clear();
                    generation_ = 0;
                    return false;
                }
            }
            regions_.swap(fresh);
            generation_=before;
        }
        const auto it = std::upper_bound(
            regions_.begin(), regions_.end(), address,
            [](std::uint64_t at, const Region& r){return at < r.va;});
        if (it == regions_.begin()) return false;
        const Region& r = *std::prev(it);
        if (address < r.va || address-r.va >= r.len) return false;
        // BBHost GuestMapInfo.prot carries the original SCE_KERNEL_PROT flags:
        // 1: CPU read, 2: CPU write, 4: CPU exec. Readable != writable!
        const std::uint32_t flags=static_cast<std::uint32_t>(r.prot)&7u;
        if ((flags & 1u) == 0) return false;
        if (epoch() != generation_) return false;
        *start=static_cast<std::uintptr_t>(r.va);
        *end=static_cast<std::uintptr_t>(r.va+r.len);
        *prot=flags;
        return true;
    }

    std::uint64_t Generation() const {return generation_;}
    std::size_t Regions() const {return regions_.size();}
private:
    std::uint64_t generation_=0;
    std::vector<Region> regions_;
};
} // namespace BloodborneCoop::SHYT::MemoryV447
