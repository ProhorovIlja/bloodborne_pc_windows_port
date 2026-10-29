// SPDX-License-Identifier: GPL-2.0-or-later
// Regression for actual PR17 native Windows server build failure C2589.
// Windows headers sometimes define min/max as function macros; the V77
// code compiled on Ubuntu but failed in bloodborne_world.h on MSVC.
#include <algorithm>
#include <cstdint>
#include <limits>
#define max(a,b) WINDOWS_MACRO_MAX_WOULD_CORRUPT_THIS_CODE
#define min(a,b) WINDOWS_MACRO_MIN_WOULD_CORRUPT_THIS_CODE
using quint64=std::uint64_t;
struct Member { quint64 direct_state_serial=0; };
struct TestWorld {
    quint64 direct_next_serial=0;
    bool BumpDirectSerial(Member& member) noexcept {
        if (direct_next_serial==(std::numeric_limits<quint64>::max)()) {
            direct_next_serial=0;
            member.direct_state_serial=0;
            return false;
        }
        member.direct_state_serial=++direct_next_serial;
        return true;
    }
    quint64 Both(const Member& first,const Member& second) const noexcept {
        const auto lo=(std::min)(first.direct_state_serial,second.direct_state_serial);
        const auto hi=(std::max)(first.direct_state_serial,second.direct_state_serial);
        return lo+hi;
    }
};
int main() {
    TestWorld state{};
    Member a{},b{};
    if(!state.BumpDirectSerial(a)||!state.BumpDirectSerial(b))return 1;
    if(state.Both(a,b)!=3)return 2;
    state.direct_next_serial=(std::numeric_limits<quint64>::max)();
    if(state.BumpDirectSerial(a)||a.direct_state_serial!=0)return 3;
    return 0;
}
