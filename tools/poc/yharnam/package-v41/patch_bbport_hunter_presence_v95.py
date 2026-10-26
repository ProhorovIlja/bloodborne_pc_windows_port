#!/usr/bin/env python3
"""Stage V95 BL/build into the pinned ORIGINAL native GPU menu, source-only.

This does not configure Discord itself: it provides a trusted *local*
preview from BbSaveEditor::Read() (PlayerGameData), no fake presence
or leaked join credentials. Exact source pins checked before writes.
"""
from __future__ import annotations
import argparse
from pathlib import Path

OVERLAY="bbport/gpu/shim/bbport_overlay.cpp"
HEADER="bbport/gpu/shim/sh_hunter_presence_v95.hpp"
MARKER="SHYT-V95-NATIVE-HUNTER-LEVEL-BUILD"
LOCAL=Path(__file__).resolve().parent/"sh_hunter_presence_v95.hpp"

def one(data: str, old: str, new: str, what: str) -> str:
    count=data.count(old)
    if count!=1:
        raise ValueError(f"V95 original UI source drift {what}: {count}")
    return data.replace(old,new,1)

def patch_overlay(data: str) -> str:
    if MARKER in data: raise ValueError("V95 native HUD already modified")
    data=one(data,
        '#include "bbport_save_editor.h"\n',
        '#include "bbport_save_editor.h"\n'
        '#include "sh_hunter_presence_v95.hpp" // '+MARKER+'\n',
        "exact pinned native game includes")
    place='''    Note(text, Dim());

    ImGui::Spacing();
    const auto& items = BbSaveEditor::Items();'''
    inserted='''    Note(text, Dim());
    // SHYT-V95-NATIVE-HUNTER-LEVEL-BUILD: show exact in-game BL and
    // conservative weapon-scaling classification based on STR/SKL/BLT/ARC.
    // The screenshot is only a LOCAL preview, NOT sent to Discord yet.
    const SeamlessHunt::HunterPresenceV95::Hunter hunter{
        c.level, {c.attributes[BbSaveEditor::Vitality],
                  c.attributes[BbSaveEditor::Endurance],
                  c.attributes[BbSaveEditor::Strength],
                  c.attributes[BbSaveEditor::Skill],
                  c.attributes[BbSaveEditor::Bloodtinge],
                  c.attributes[BbSaveEditor::Arcane]}};
    const std::string discord_preview =
        SeamlessHunt::HunterPresenceV95::Details(hunter);
    if (!discord_preview.empty()) {
        const std::string local_line =
            std::string(T("Discord BL/build preview (local only): ",
                          "Превью BL/билда Discord (только локально): "))
            + discord_preview;
        Note(local_line.c_str(), Dim());
    }

    ImGui::Spacing();
    const auto& items = BbSaveEditor::Items();'''
    return one(data,place,inserted,"save editor local level/build preview")

def patch_team_quit(data: str) -> str:
    """Put Quit beside Close in the real in-game Co-op Team/System menu.

    Reuse the native already-confirmed quit_open + SDL_EVENT_QUIT path.
    Never call exit/terminate from the game renderer, preserve saves.
    """
    anchor='''    // The buttons: the team, Begin the hunt, the world.
    ImGui::PushFont(MenuArt::Font(), 24.0f);
    const float bw = S(260.0f), bh = S(54.0f);'''
    data=one(data,anchor,'''    // SHYT-V95-QUIT-IN-GAME: fourth button in the real System -> Co-op Team menu.
    // The menu's existing QuitBox validates the player's confirmation.
    ImGui::PushFont(MenuArt::Font(), 24.0f);
    const float bw = lobby.menu ? S(215.0f) : S(260.0f), bh = S(54.0f);''',
    "original Team button geometry")
    data=one(data,
        '''    float bx = win.x + (size.x - (3 * bw + 2 * gap)) * 0.5f;''',
        '''    const int buttons = lobby.menu ? 4 : 3;
    float bx = win.x + (size.x - (buttons * bw + (buttons - 1) * gap)) * 0.5f;''',
        "native Team four-button width")
    data=one(data,
        '''        if (Button(draw, "close", T("Close", "Закрыть"), ImVec2(bx, by), ImVec2(bw, bh))) {
            bbcoop_team_menu(0);
        }
        ImGui::PopFont();''',
        '''        if (Button(draw, "close", T("Close", "Закрыть"), ImVec2(bx, by), ImVec2(bw, bh))) {
            bbcoop_team_menu(0);
        }
        bx += bw + gap;
        if (Button(draw, "quit-desktop",
                   T("Quit to Desktop", "Выйти из игры"), ImVec2(bx, by), ImVec2(bw, bh))) {
            // Explicit game-menu action; use the existing confirmation
            // dialog and normal SDL window shutdown (not std::exit).
            bbcoop_team_menu(0);
            SetOpen(false);
            quit_open = true;
        }
        ImGui::PopFont();''',
        "real native in-game Co-op Team Quit action")
    return data


def stage(root: Path)->None:
    source=root/OVERLAY
    destination=root/HEADER
    if not source.is_file() or not LOCAL.is_file():
        raise ValueError("pinned native overlay or local V95 header missing")
    if destination.exists():
        raise ValueError("V95 header already staged; refuse overwriting vendor data")
    old=source.read_text("utf-8")
    new=patch_team_quit(patch_overlay(old))
    header=LOCAL.read_text("utf-8")
    if "MinBuildAttribute = 18;" not in header:
        raise ValueError("V95 unrecognized classifier")
    source.write_text(new,encoding="utf-8")
    destination.write_text(header,encoding="utf-8")
    print("SHYT_V95_NATIVE_BL_BUILD_LOCAL_PREVIEW_AND_IN_GAME_QUIT_STAGED")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("pinned_checkout",type=Path)
    stage(parser.parse_args().pinned_checkout)
