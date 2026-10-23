#!/usr/bin/env python3
"""V14: F10 Quit to Desktop on title/team, F9 long-session performance diagnostics.
Apply after V13 to the pinned BBPort 1.09 source. Never uses force exit.
"""
from pathlib import Path
PATH="bbport/gpu/shim/bbport_overlay.cpp"
HERE=Path(__file__).resolve().parent
def one(s,old,new,label):
    n=s.count(old)
    if n!=1:raise ValueError(f"V14 {label}: expected one anchor, found {n}")
    return s.replace(old,new,1)
def transform(text,perf_header=None,perf_overlay=None):
    if perf_header is None:perf_header=(HERE/"perf_watch.hpp").read_text("utf-8")
    if perf_overlay is None:perf_overlay=(HERE/"perf_overlay.inc").read_text("utf-8")
    if "namespace ShPerformance" in text:raise ValueError("V14 already applied")
    text=one(text,'#include "bbport_settings.h"',
      '#include "bbport_settings.h"\n#include "bbport_toggles.h"\n#include "sh_perf_watch.hpp"\n#include <fstream>\n#ifdef _WIN32\n#include <windows.h>\n#include <psapi.h>\n#else\n#include <unistd.h>\n#endif',"include")
    text=one(text,"// Hold L3 + R3, or the menu's Quit row:",
      perf_overlay+"\n// Hold L3 + R3, or the menu's Quit row:","diagnostics")
    text=one(text,
      "        const bool down = event.type == SDL_EVENT_KEY_DOWN;\n        // bbport: numpad 0",
      '''        const bool down = event.type == SDL_EVENT_KEY_DOWN;
        // Available both at the title screen and while playing. Respect text input.
        if(down && !event.key.repeat && !prompt_active && event.key.key==SDLK_F9){
            ShPerformance::enabled=!ShPerformance::enabled;
            return true;
        }
        if(down && !event.key.repeat && !prompt_active && event.key.key==SDLK_F10){
            SetOpen(false);
            quit_open=true;
            return true;
        }
        // bbport: numpad 0''',"keyboard")
    text=one(text,
      "    // Title and the team's state.\n    ImGui::PushFont(MenuArt::Font(), 40.0f);",
      '''    // Prominent menu exit; opens the existing confirmed SDL quit path.
    ImGui::PushFont(MenuArt::Font(),19.0f);
    if(Button(draw,"sh-quit-desktop",T("Quit to Desktop","Выйти из игры"),
              ImVec2(win.x+size.x-S(250.0f),win.y+S(26.0f)),
              ImVec2(S(222.0f),S(40.0f))))quit_open=true;
    ImGui::PopFont();
    // Title and the team's state.
    ImGui::PushFont(MenuArt::Font(), 40.0f);''',"title button")
    text=one(text,
      "if (Team::open && !menu_open) {\n        Team::Screen();",
      "if (Team::open && !menu_open && !quit_open) {\n        Team::Screen();",
      "quit modal suppresses Team buttons")
    text=one(text,
      "return initialized && (menu_open || quit_open || prompt_active || BbSettings::Get().show_fps || party || compass ||",
      "return initialized && (menu_open || quit_open || prompt_active || ShPerformance::enabled || BbSettings::Get().show_fps || party || compass ||",
      "diagnostics visibility")
    text=one(text,
      "    if (BbSettings::Get().show_fps && !menu_open) {\n        FpsCounter();\n    }",
      '''    if (BbSettings::Get().show_fps && !menu_open) {
        FpsCounter();
    }
    if(ShPerformance::enabled && !menu_open && !quit_open && !Joining::open){
        ShPerformance::Draw(Map::view.map,frame_ms_avg,ImGui::GetPlatformIO().Textures.Size);
    }''',"diagnostics draw")
    return {PATH:text,"bbport/gpu/shim/sh_perf_watch.hpp":perf_header}
