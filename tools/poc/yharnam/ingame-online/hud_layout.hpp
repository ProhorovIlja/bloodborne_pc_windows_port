// SPDX-License-Identifier: GPL-2.0-or-later
// Portable in-game UI geometry. Still requires a native overlay build.
#pragma once
#include <algorithm>
#include <cmath>
#include <cstddef>
#include <string_view>
namespace SeamlessHunt::InGame {
enum class HunterRole { Host, Defender, Invader };
enum class RoleTone { Gold, Bone, Blood };
inline std::string_view RoleEnglish(HunterRole r) {
    switch(r) {
    case HunterRole::Host:return "HOST";
    case HunterRole::Defender:return "ALLY";
    case HunterRole::Invader:return "INVADER";
    }
    return "HUNTER";
}
inline std::string_view RoleRussian(HunterRole r) {
    switch(r) {
    case HunterRole::Host:return "ХОСТ";
    case HunterRole::Defender:return "СОЮЗНИК";
    case HunterRole::Invader:return "ВТОРЖЕНЕЦ";
    }
    return "ОХОТНИК";
}
inline RoleTone ToneFor(HunterRole r) {
    switch(r) {
    case HunterRole::Host:return RoleTone::Gold;
    case HunterRole::Defender:return RoleTone::Bone;
    case HunterRole::Invader:return RoleTone::Blood;
    }
    return RoleTone::Bone;
}
struct TeamStrip {
    float scale{1},x{0},y{0},card_w{0},card_h{0},gap{0},strip_width{0};
    unsigned count{0};
    bool needs_horizontal_scroll{false};
};
inline TeamStrip TeamCards(float viewport_width,float center_x,float y,
    unsigned members,float user_scale=1.0f,float dpi=1.0f) {
    TeamStrip out;
    out.count=std::clamp(members,1u,5u);
    constexpr float kCardWidth=290.0f,kCardHeight=270.0f,kGap=24.0f;
    dpi=std::clamp(dpi,0.75f,3.0f);
    viewport_width=std::max(0.0f,viewport_width);
    const float baseline=(4*kCardWidth+3*kGap)*dpi;
    const float available=std::min(baseline,std::max(0.0f,viewport_width-72.0f*dpi));
    const float base=(out.count*kCardWidth+(out.count-1)*kGap)*dpi;
    const float desired=std::clamp(user_scale,0.70f,1.10f);
    out.scale=std::min(desired,base>0?available/base:1.0f);
    // At very narrow widths, preserve readable text and request a scroll
    // adapter instead of reducing all text below a usable size.
    if(out.scale<0.65f){out.scale=0.65f;out.needs_horizontal_scroll=true;}
    out.card_w=kCardWidth*dpi*out.scale;
    out.card_h=kCardHeight*dpi*out.scale;
    out.gap=kGap*dpi*out.scale;
    out.strip_width=out.count*out.card_w+(out.count-1)*out.gap;
    out.x=center_x-out.strip_width*0.5f;out.y=y;return out;
}
struct HudStrip {
    float scale{1},row_h{0},text_height{0},width{0},total_height{0};
    unsigned rows{0};
};
inline HudStrip HudRows(unsigned remote_members,float user_scale=1.0f,float dpi=1.0f){
    HudStrip out;out.rows=std::min(remote_members,4u);
    dpi=std::clamp(dpi,0.75f,3.0f);
    const float natural=50.0f*dpi;
    const float available=3.0f*natural;
    out.scale=out.rows==0?1.0f:std::min(std::clamp(user_scale,0.65f,1.10f),
                                         available/(natural*out.rows));
    out.row_h=natural*out.scale;
    out.text_height=std::max(13.0f*dpi,18.0f*dpi*out.scale);
    out.width=240.0f*dpi*out.scale;
    out.total_height=out.rows*out.row_h;
    return out;
}
} // namespace SeamlessHunt::InGame
