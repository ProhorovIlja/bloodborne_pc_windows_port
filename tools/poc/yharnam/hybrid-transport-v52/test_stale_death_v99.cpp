// SPDX-License-Identifier: GPL-2.0-or-later
// V99 uses ACTUAL class and method extracted from patched original
// Yharnam Together pinned native game, NOT a duplicated mock algorithm.
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <iostream>
#include <ranges>
#include <span>
#include <utility>
#include <vector>
using u32=std::uint32_t;
using u64=std::uint64_t;
using s64=std::int64_t;
#include "sh_v99_extracted_class.inc"
#include "sh_v99_extracted_method.inc"

static StaleDeathMarks::Body Body(u32 h,u64 info,bool dead=false,
                                   bool down=false,bool invader=false,
                                   bool marked=true) {
    return {h,info,marked,dead,down,invader};
}
int main(){
    StaleDeathMarks target;
    auto tick=[&](std::initializer_list<StaleDeathMarks::Body> bodies,
                  s64 ms,u64 visit) {
        return target.Tick(bodies,ms,visit);
    };
    assert(tick({Body(7,0x50000)},1000,10).empty());
    assert(tick({Body(7,0x50000)},3999,10).empty());
    assert((tick({Body(7,0x50000)},4000,10)==std::vector<u32>{7}));
    assert(tick({Body(7,0x50000)},4001,10).empty());
    // A reclaimed game handle cannot reuse an old body's timer.
    assert(tick({Body(7,0x60000)},4100,10).empty());
    assert(tick({Body(7,0x60000)},7099,10).empty());
    assert((tick({Body(7,0x60000)},7100,10)==std::vector<u32>{7}));
    // Changed world visit invalidates observations even with same pointer.
    assert(tick({Body(7,0x60000)},7200,11).empty());
    assert(tick({Body(7,0x60000)},10199,11).empty());
    assert((tick({Body(7,0x60000)},10200,11)==std::vector<u32>{7}));
    // Truly dead / downed / invader / unmarked reset the timer.
    assert(tick({Body(7,0x60000,true)},10300,11).empty());
    assert(tick({Body(7,0x60000)},10400,11).empty());
    assert(tick({Body(7,0x60000)},13399,11).empty());
    assert((tick({Body(7,0x60000)},13400,11)==std::vector<u32>{7}));
    for(auto masked:{Body(7,0x60000,false,true),
                     Body(7,0x60000,false,false,true),
                     Body(7,0x60000,false,false,false,false)})
        assert(tick({masked},13500,11).empty());
    assert(tick({Body(7,0x60000)},13600,11).empty());
    // Dropping out of the party clears pending identifiers.
    assert(tick({},14000,0).empty());
    assert(tick({Body(7,0x60000)},16000,11).empty());
    assert(tick({Body(7,0x60000)},18999,11).empty());
    assert((tick({Body(7,0x60000)},19000,11)==std::vector<u32>{7}));
    // Non-monotonic clock must not authorize a write.
    assert(tick({Body(7,0x60000)},20000,11).empty());
    assert(tick({Body(7,0x60000)},19999,11).empty());
    std::cout<<"SHYT_V99_ORIGINAL_GAME_AI_RESURRECTION_GUARDS_PASS\n";
}
