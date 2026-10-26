// SPDX-License-Identifier: GPL-2.0-or-later
// V95: Yharnam Together native player's own BL+build, no account/network data.
// Pure source-only formatter; UI/Discord transport opt-in and independent.
#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <string>
#include <string_view>

namespace SeamlessHunt::HunterPresenceV95 {
struct Hunter {
    int blood_level = 0; // Read game's authoritative PlayerGameData +0x90
    // Own PlayerGameData +0x40, +0x48, +0x58, +0x60, +0x68, +0x70
    std::array<int,6> stats{}; // VIT, END, STR, SKL, BLT, ARC
};
struct Options {
    bool show_level = true;
    bool show_build = true;
};
constexpr int MinBuildAttribute = 18;
inline bool Valid(const Hunter& hunter) noexcept {
    if (hunter.blood_level < 1 || hunter.blood_level > 544) return false;
    for (int value : hunter.stats)
        if (value < 1 || value > 99) return false;
    return true;
}
inline std::string Build(const Hunter& hunter) {
    if (!Valid(hunter)) return {};
    // VIT/END are endurance/survivability, not weapon scaling. Only
    // the four offensive attributes classify the hunter's actual build.
    constexpr std::array<const char*,4> Names{
        "Strength","Skill","Bloodtinge","Arcane"};
    const std::array<int,4> values{
        hunter.stats[2],hunter.stats[3],hunter.stats[4],hunter.stats[5]};
    std::array<int,4> selected{};
    int count=0;
    for (int i=0;i<4;++i)
        if (values[i]>=MinBuildAttribute) selected[count++]=i;
    if (!count) return "Developing Hunter";
    if (count==1) return Names[selected[0]];
    if (count==2 && selected[0]==0 && selected[1]==1)
        return "Quality"; // Bloodborne STR + SKL, other combinations labelled.
    if (count>=3) return "Hybrid";
    return std::string(Names[selected[0]])+"/"+Names[selected[1]];
}
inline std::string Details(const Hunter& hunter, Options privacy={}) {
    if (!Valid(hunter))return {};
    std::string out;
    if (privacy.show_level) out="BL "+std::to_string(hunter.blood_level);
    if (privacy.show_build) {
        const std::string role=Build(hunter);
        if (!role.empty()) {
            if (!out.empty())out+=" | ";
            out+=role;
        }
    }
    // Discord's current details length is bounded; our labels max 30
    // bytes, no user names or arbitrary location appear in this field.
    return out;
}
} // namespace SeamlessHunt::HunterPresenceV95
