#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Generate an isolated in-game UI-scale overlay source from pinned Yharnam Together.
Does not enable fifth gameplay slot, build a binary or modify installed games.
"""
import argparse
from pathlib import Path

OLD_HEADER = """    // The four places.
    const float card_w = S(290.0f), card_h = S(270.0f), gap = S(24.0f);
    const float cards_x = win.x + (size.x - (4 * card_w + 3 * gap)) * 0.5f,
                header_y = win.y + S(MenuArt::Has(MenuArt::HeaderOrnament) ? 140.0f : 128.0f);"""
NEW_HEADER = """    // Seamless Hunt: adaptive cards; actual server/team runtime owns limits.
    const unsigned sh_columns = BBCOOP_LOBBY_TEAM;
    const float sh_natural_w = S(290.0f), sh_natural_h = S(270.0f);
    const float sh_user_scale = SeamlessHunt::InGame::GetTeamScale();
    const auto sh_strip = SeamlessHunt::InGame::TeamCards(
        size.x, win.x + size.x * 0.5f, 0.0f, sh_columns, sh_user_scale, S(1.0f));
    const float sh_scale = sh_strip.scale;
    const float card_w = sh_strip.card_w, card_h = sh_strip.card_h, gap = sh_strip.gap;
    const float cards_x = sh_strip.x,
                header_y = win.y + S(MenuArt::Has(MenuArt::HeaderOrnament) ? 140.0f : 128.0f);"""
OLD_CARD = """        Card(draw, ImVec2(cards_x + i * (card_w + gap), cards_y), ImVec2(card_w, card_h),
             taken ? &lobby.members[i] : nullptr, taken && i == 0, i);"""
NEW_CARD = """        const ImVec2 sh_at(cards_x + i * (card_w + gap), cards_y);
        // Card is art/text only, with no input widgets. Transform all vertices.
        const int sh_first_vertex = draw->VtxBuffer.Size;
        Card(draw, sh_at, ImVec2(sh_natural_w, sh_natural_h),
             taken ? &lobby.members[i] : nullptr, taken && i == 0, i);
        for (int v = sh_first_vertex; v < draw->VtxBuffer.Size; ++v) {
            ImVec2& p = draw->VtxBuffer[v].pos;
            p.x = sh_at.x + (p.x - sh_at.x) * sh_scale;
            p.y = sh_at.y + (p.y - sh_at.y) * sh_scale;
        }"""
OLD_SUBTITLE = """    // Title and the team's state.
    ImGui::PushFont(MenuArt::Font(), 40.0f);"""
NEW_SUBTITLE = """    // Controller and mouse focus use existing Team::Button. Save per BB_USER_DIR.
    const float sh_ctl_y = win.y + S(65.0f);
    const float sh_ctl_w = S(42.0f), sh_ctl_h = S(32.0f);
    const float sh_plus_x = x1 - sh_ctl_w;
    const float sh_minus_x = sh_plus_x - S(52.0f);
    ImGui::PushFont(MenuArt::Font(), 18.0f);
    const std::string sh_ui_text = std::string(T("UI scale", "Масштаб UI")) + " " +
                                   std::to_string(SeamlessHunt::InGame::TeamScalePercent()) + "%";
    draw->AddText(ImVec2(sh_minus_x - S(190.0f), sh_ctl_y + S(6.0f)), Gold(), sh_ui_text.c_str());
    if (Button(draw, "sh-scale-minus", "-", ImVec2(sh_minus_x, sh_ctl_y),
               ImVec2(sh_ctl_w, sh_ctl_h))) {
        SeamlessHunt::InGame::SetTeamScalePercent(
            SeamlessHunt::InGame::TeamScalePercent() - 5);
    }
    if (Button(draw, "sh-scale-plus", "+", ImVec2(sh_plus_x, sh_ctl_y),
               ImVec2(sh_ctl_w, sh_ctl_h))) {
        SeamlessHunt::InGame::SetTeamScalePercent(
            SeamlessHunt::InGame::TeamScalePercent() + 5);
    }
    ImGui::PopFont();

    // Title and the team's state.
    ImGui::PushFont(MenuArt::Font(), 40.0f);"""

def replace_once(source, old, new, name):
    count=source.count(old)
    if count!=1: raise ValueError(f"{name}: expected one anchored match, found {count}")
    return source.replace(old,new,1)

def transform(source):
    source=replace_once(source,'#include "bbport_settings.h"',
        '#include "bbport_settings.h"\n#include "sh_yharnam_layout.hpp"\n#include "sh_yharnam_ui_scale.hpp"','headers')
    source=replace_once(source,OLD_SUBTITLE,NEW_SUBTITLE,'in-game control')
    source=replace_once(source,OLD_HEADER,NEW_HEADER,'card geometry')
    source=replace_once(source,OLD_CARD,NEW_CARD,'card rendering')
    source=replace_once(source,'std::to_string(lobby.member_count) + T(" of 4", " из 4");',
        'std::to_string(lobby.member_count) + T(" of ", " из ") + std::to_string(BBCOOP_LOBBY_TEAM);',
        'capacity text')
    source=replace_once(source,'const ImVec2 remove_size(S(170.0f), S(38.0f));',
        'const ImVec2 remove_size(S(170.0f) * sh_scale, S(38.0f) * sh_scale);','remove button hitbox')
    source=replace_once(source,
        "    if (lobby.leader) {\n        ImGui::PushFont(MenuArt::Font(), 19.0f);\n        const ImVec2 remove_size",
        "    if (lobby.leader) {\n        ImGui::PushFont(MenuArt::Font(), 19.0f * sh_scale);\n        const ImVec2 remove_size",
        'remove button font')
    return source

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    src=args.source.resolve();out=args.out.resolve()
    if src==out:p.error("Never edit original source in place")
    if src.name!='bbport_overlay.cpp':p.error("Expected bbport_overlay.cpp")
    changed=transform(src.read_text(encoding='utf-8'))
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(changed,encoding='utf-8')
    root=Path(__file__).resolve().parent
    (out.parent/'sh_yharnam_layout.hpp').write_text((root/'hud_layout.hpp').read_text('utf-8'),encoding='utf-8')
    (out.parent/'sh_yharnam_ui_scale.hpp').write_text((root/'sh_yharnam_ui_scale.hpp').read_text('utf-8'),encoding='utf-8')
    print("PATCH_OK: generated native in-game UI source; still requires compilation and gameplay testing")

if __name__=='__main__':
    main()
