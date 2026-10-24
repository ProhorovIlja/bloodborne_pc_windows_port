#!/usr/bin/env python3
"""V13 actual native source patch. Apply AFTER the V11 Team-menu patch.
No game binaries or server changes; pinned 1.09 and verified x64 camera hook only.
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
CAM="bbport/src/runtime_camhook.c"
PAD="bbport/src/runtime_pad.c"
PANEL="bbport/gpu/bbcoop.h"
BRIDGE="bbport/gpu/bbcoop/coop.cpp"
OVERLAY="bbport/gpu/shim/bbport_overlay.cpp"
PATHS={CAM,PAD,PANEL,BRIDGE,OVERLAY}

def exactly_one(s,old,new,label):
    count=s.count(old)
    if count!=1: raise ValueError(f"V13 {label}: expected one pinned anchor, found {count}")
    return s.replace(old,new,1)

def transform(originals:dict[str,str])->dict[str,str]:
    if PATHS-originals.keys():raise ValueError("V13 missing actual native BBPort source files")
    out=dict(originals)
    fragment=(ROOT/"spectator_camera.inc").read_text("utf-8")
    policy=(ROOT/"spectator_policy.hpp").read_text("utf-8")
    ui=(ROOT/"spectator_overlay.inc").read_text("utf-8")
    out[CAM]=exactly_one(out[CAM],
        "static float *field(unsigned char *camera, unsigned offset) { return (float *)(camera+offset); }",
        "static float *field(unsigned char *camera, unsigned offset) { return (float *)(camera+offset); }\n"+fragment,
        "camera fragment")
    out[CAM]=exactly_one(out[CAM],
        "    return pitch;\n}\n\n#ifdef _WIN32",
        "    sh_spectator_frame(camera);\n    return pitch;\n}\n\n#ifdef _WIN32",
        "camera update")
    out[PAD]=exactly_one(out[PAD],
        'if (!kbm.mouse_camera) { puts("Runtime: Mouse camera: off (mouse_camera=0)"); return; }',
        '''if (!kbm.mouse_camera) {
        const char *why="";
        /* Install the verified hook BEFORE game rendering even for pad-only users. */
        if(!runtime_camhook_install(0,&why))
            printf("Runtime: spectator camera disabled: %s\\n",why);
        puts("Runtime: Mouse camera: off (mouse_camera=0)"); return;
    }''',
        "gamepad-only hook")
    out[PANEL]=exactly_one(out[PANEL],
        "    uint32_t vials, bullets; /* Kaniel 2026-10-18: beside the name */",
        '''    uint32_t vials, bullets; /* Kaniel 2026-10-18: beside the name */
    int has_at; /* current-map teammate position for camera-only observation */
    float x, y, z;''',
        "panel ABI")
    out[BRIDGE]=exactly_one(out[BRIDGE],
        "        out.bullets = member.bullets;",
        '''        out.bullets = member.bullets;
        if(member.here && member.at){
            out.has_at=1;
            out.x=(*member.at)[0];out.y=(*member.at)[1];out.z=(*member.at)[2];
        }''',
        "party HUD position")
    out[OVERLAY]=exactly_one(out[OVERLAY],
        '#include "bbport_settings.h"',
        '#include "bbport_settings.h"\n#include "spectator_policy.hpp"\n'
        'extern "C" void runtime_camhook_spectator(int,float,float,float,float,float,float);',
        "overlay include")
    out[OVERLAY]=exactly_one(out[OVERLAY],
        "} // namespace Party\n\n/// Kaniel 2026-10-17: the teammate compass",
        "} // namespace Party\n\n"+ui+"\n/// Kaniel 2026-10-17: the teammate compass",
        "spectator UI, after Party")
    redraw="""    if (Party::shown && !menu_open) {
        Party::game = {float(game.offset.x), float(game.offset.y), float(game.extent.width),
                       float(game.extent.height)};
        Party::Draw();
    }"""
    out[OVERLAY]=exactly_one(out[OVERLAY],redraw,
        redraw+"""\n    if(Party::shown) Spectator::Tick();
    else runtime_camhook_spectator(0,0,0,0,0,0,0);""","game frame render")
    out["bbport/gpu/shim/spectator_policy.hpp"]=policy
    return out
