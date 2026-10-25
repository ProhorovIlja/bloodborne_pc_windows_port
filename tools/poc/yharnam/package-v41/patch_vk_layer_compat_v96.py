#!/usr/bin/env python3
"""V96: source-checked native Windows launcher Vulkan layer crash fix.

Backports lKaniel/bloodborne-server PR #418 to the pinned 77e3507
bbport/launcher/bbport_launcher_win.py. HudSight implicit layers were
implicated in ten consecutive real device-creation crashes. Restrict this
to the game subprocess environment, respect preexisting disabled layers,
and let advanced launcher extra_env explicitly override this default.
"""
from __future__ import annotations
import argparse
from pathlib import Path

TARGET="bbport/launcher/bbport_launcher_win.py"
MARKER="SHYT-V96-HUDSIGHT-CRASHING-VULKAN-LAYER"

def one(content: str, old: str, new: str, where: str) -> str:
    count=content.count(old)
    if count!=1:
        raise ValueError(f"V96 pinned launcher source drift at {where}: {count}")
    return content.replace(old,new,1)

def patch_launcher(content: str) -> str:
    if MARKER in content:
        raise ValueError("V96 Vulkan layer guard already applied")
    content=one(content,
        "RESHADE_LAYER = 'VK_LAYER_bbport_reshade'\n",
        "RESHADE_LAYER = 'VK_LAYER_bbport_reshade'\n"
        "# "+MARKER+": original Kaniel PR418, known real GPU crashes.\n"
        "CRASHING_VK_LAYERS = ('*HudSight*',)\n"
        "\n"
        "def add_crashing_vk_layer_guard(env):\n"
        "    \"\"\"A per-game Vulkan loader denylist; never mutate os.environ.\"\"\"\n"
        "    key = 'VK_LOADER_LAYERS_DISABLE'\n"
        "    disabled = [item for item in env.get(key, '').split(',') if item]\n"
        "    env[key] = ','.join(disabled + [layer for layer in CRASHING_VK_LAYERS\n"
        "                                 if layer not in disabled])\n"
        "\n",
        "launcher constants and isolated helper")
    content=one(content,
        """    else:
        env.pop('BB_FSR4VK', None)  # the switch decides: an inherited 0 would leave the dropdown on and the game off
    for item in str(s['extra_env']).split():""",
        """    else:
        env.pop('BB_FSR4VK', None)  # the switch decides: an inherited 0 would leave the dropdown on and the game off
    # Per-game layer denylist, before user extra_env (explicit opt-out).
    # Known HudSight Vulkan device crashes; never touch the user's OS.
    add_crashing_vk_layer_guard(env)
    for item in str(s['extra_env']).split():""",
        "game_environment before explicit advanced extra_env")
    return content

def stage(root: Path)->None:
    dest=root/TARGET
    if not dest.is_file():
        raise ValueError("pinned original Windows native game launcher missing")
    before=dest.read_text("utf-8")
    after=patch_launcher(before)
    dest.write_text(after,encoding="utf-8")
    print("SHYT_V96_NATIVE_WINDOWS_GAME_HUDSIGHT_CRASH_LAYER_GUARD_STAGED")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("pinned_checkout",type=Path)
    stage(parser.parse_args().pinned_checkout)
