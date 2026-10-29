// SPDX-License-Identifier: GPL-2.0-or-later
// Actual original pinned gameplay LethalCatches declaration and method
// are extracted by CI into the following two includes, not reimplemented.
#include <cassert>
#include <cstdint>
#include <iostream>
using u32=std::uint32_t;
enum class Vital {Off,Up,Down,Dead};
#include "sh_v98_extracted_class.inc"
#include "sh_v98_extracted_method.inc"

int main(){
    LethalCatches ledger;
    assert(!ledger.Take(0,Vital::Off));
    assert(ledger.Take(1,Vital::Up));
    assert(!ledger.Take(1,Vital::Up));
    assert(!ledger.Take(2,Vital::Down));
    assert(!ledger.Take(3,Vital::Dead));
    // The FIRST waking tick must not put a revived hunter down at lamp.
    assert(!ledger.Take(3,Vital::Up));
    assert(!ledger.Take(3,Vital::Up));
    // But a genuinely NEW post-revive lethal hit must put them down.
    assert(ledger.Take(4,Vital::Up));
    assert(!ledger.Take(5,Vital::Down));
    assert(!ledger.Take(6,Vital::Dead));
    assert(!ledger.Take(6,Vital::Off));
    assert(ledger.Take(7,Vital::Off));
    // Counter wrap or hook reset while dead should not enqueue a hit.
    assert(!ledger.Take(0,Vital::Dead));
    assert(!ledger.Take(0,Vital::Up));
    assert(ledger.Take(1,Vital::Up));
    std::cout<<"SHYT_V98_ORIGINAL_LETHAL_CATCH_CLEAN_RESPAWN_PASS\n";
}
