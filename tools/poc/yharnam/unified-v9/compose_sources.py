#!/usr/bin/env python3
"""Compose pinned native Yharnam Together V3/V5/V7/V8 source patches atomically.
Developer source override only: NOT a deployable or player-ready game.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import types
import zipfile

PIN = "77e350743a7cb4524cfcc1782fb6e3af64e25b15"
ARCHIVES = {
    "ui": "SH-YT-INGAME-UI-P2P-V3-20261023.zip",
    "dbno": "SH-YT-NATIVE-DBNO-ENDTOEND-V5-20261023.zip",
    "direct": "SH-YT-NATIVE-DIRECT-P2P-V7-20261023.zip",
}
DIGESTS = {
    "ui": "c099dd631c90dc4d1ac4ff9b72ce6d72ea203e099948f77054f0374e6053b2af",
    "dbno": "2daf3f3a3ab9bf8127d98d392f62bb5c9e2554871ca01279af237df542b167e5",
    "direct": "e2818139c1001cd61ab10c4e6aef70c67b131be00ea1f7fb0fb3aefef1985559",
}
OVERLAY = "bbport/gpu/shim/bbport_overlay.cpp"
MAP3D = "bbport/gpu/shim/bbport_map_3d.cpp"
TEXTURE_GC = "bbport/gpu/shadps4/video_core/texture_cache/texture_cache.cpp"
MAPCHARTS = "bbport/gpu/shim/bbport_map_charts.cpp"
MAPART = "bbport/gpu/shim/bbport_map_art.cpp"
NETWORK = "emulator/src/core/libraries/network/p2p_sockets.cpp"
COOP = "bbport/launcher/bbport_coop.py"
LAUNCHER = "bbport/launcher/bbport_launcher_win.py"

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def load_zip_module(path: Path, member: str, name: str):
    with zipfile.ZipFile(path) as z:
        source = z.read(member).decode("utf-8")
    mod = types.ModuleType(name)
    mod.__file__ = str(path)+":"+member
    exec(compile(source, mod.__file__, "exec"), mod.__dict__)
    return mod

def compose(source: dict[str,str], archives: Path, v8patch, *, verify_files=True):
    by_kind={}
    for kind, filename in ARCHIVES.items():
        p=archives/filename
        if verify_files and sha(p.read_bytes()) != DIGESTS[kind]:
            raise ValueError("archive SHA-256 mismatch: "+filename)
        by_kind[kind]=p
    v5=load_zip_module(by_kind["dbno"],"patch_native_dbno.py","v5_dbno")
    v3=load_zip_module(by_kind["ui"],"PATCH-YHARNAM-TEAM-UI.py","v3_layout")
    v7=load_zip_module(by_kind["direct"],"PATCH-BBPORT-NATIVE-DIRECT-V7.py","v7_direct")
    dest={}
    if len(v5.PATCHES)!=8:
        raise ValueError("expected eight DBNO source changes")
    for path, patch in v5.PATCHES.items():
        if path not in source:
            raise FileNotFoundError("missing pinned source "+path)
        dest[path]=patch(source[path])
    # Both DBNO and UI scale patch the game's Team menu: apply V5, then V3.
    dest[OVERLAY]=v3.transform(dest[OVERLAY])
    # The V7 runtime path stays relay-only until AUTHENTICATED candidate
    # exchange and server-side game-channel authorization are implemented.
    dest[NETWORK]=v7.patch(source[NETWORK])
    dest[COOP]=v8patch.patch_coop(source[COOP])
    dest[LAUNCHER]=v8patch.patch_launcher(source[LAUNCHER])
    extra={
        "bbport/gpu/shim/sh_yharnam_layout.hpp":(by_kind["ui"],"hud_layout.hpp"),
        "bbport/gpu/shim/sh_yharnam_ui_scale.hpp":(by_kind["ui"],"sh_yharnam_ui_scale.hpp"),
        "emulator/src/core/libraries/network/native_shlk_direct.hpp":(by_kind["direct"],"native_shlk_direct.hpp"),
        "emulator/src/core/libraries/network/native_shlk_adapter.hpp":(by_kind["direct"],"native_shlk_adapter.hpp"),
    }
    output={k:v.encode("utf-8") for k,v in dest.items()}
    for path,(archive,member) in extra.items():
        with zipfile.ZipFile(archive) as z:
            output[path]=z.read(member)
    if len(output)!=len(dest)+4: raise ValueError("missing header outputs")
    # V10: patch V7 adapter in BOTH directions. Never deliver map/owner-sensitive
    # gameplay channels directly, even if a pairwise MAC is otherwise valid.
    v10_dir=Path(__file__).resolve().parent.parent/"direct-channel-v10"
    v10_guard=types.ModuleType("sh_direct_channel_guard")
    v10_py=v10_dir/"guard_adapter.py"
    exec(compile(v10_py.read_text("utf-8"),str(v10_py),"exec"),v10_guard.__dict__)
    adapter_path="emulator/src/core/libraries/network/native_shlk_adapter.hpp"
    output[adapter_path]=v10_guard.patch_adapter(output[adapter_path].decode("utf-8")).encode("utf-8")
    output["emulator/src/core/libraries/network/native_direct_filter.hpp"]=(v10_dir/"native_direct_filter.hpp").read_bytes()
    # V11: apply title-screen last-hunt preference last, because DBNO and the
    # UI scale already touch the same native Team menu.
    v11_dir=Path(__file__).resolve().parent.parent/"last-session-v11"
    v11_patch=types.ModuleType("sh_native_resume_patch")
    v11_file=v11_dir/"patch_native_resume.py"
    exec(compile(v11_file.read_text("utf-8"),str(v11_file),"exec"),v11_patch.__dict__)
    resume_paths={
        "emulator/src/core/bloodborne_server_world.cpp",
        "emulator/src/core/bloodborne_re_internal.h",
        "bbport/gpu/bbcoop.h",
        "bbport/gpu/bbcoop/coop.cpp",
        "bbport/gpu/shim/bbport_overlay.cpp",
    }
    resume_sources={name:output[name].decode("utf-8") for name in resume_paths}
    resume_header=(v11_dir/"last_session_policy.hpp").read_text("utf-8")
    guarded_resume=v11_patch.transform(resume_sources,resume_header)
    for name,body in guarded_resume.items():
        if name not in resume_paths and name!="emulator/src/core/last_session_policy.hpp":
            raise ValueError("unexpected V11 output "+name)
        output[name]=body.encode("utf-8")
    if len(output)!=len(dest)+6:
        raise ValueError("missing V10 or V11 headers")
    # V13: AFTER DBNO+UI scale+V11, add the existing native v1.09
    # camera hook and a passive, down-only camera observer.
    v13_dir=Path(__file__).resolve().parent.parent/"spectator-v13"
    v13_module=types.ModuleType("sh_native_spectator_patch")
    v13_script=v13_dir/"patch_spectator.py"
    exec(compile(v13_script.read_text("utf-8"),str(v13_script),"exec"),v13_module.__dict__)
    v13_sources={}
    for name in v13_module.PATHS:
        v13_sources[name]=(
            output[name] if name in output else source[name].encode("utf-8")
        ).decode("utf-8")
    for name,contents in v13_module.transform(v13_sources).items():
        output[name]=contents.encode("utf-8")
    if len(output)!=len(dest)+9:
        raise ValueError("missing V13 runtime or policy outputs")
    # V14: confirmed Quit to Desktop from title/Team/keyboard, plus passive
    # performance telemetry. Applied AFTER V13, which modifies the same overlay.
    v14_dir=Path(__file__).resolve().parent.parent/"quit-perf-v14"
    v14_module=types.ModuleType("sh_quit_perf_patch")
    v14_script=v14_dir/"patch_quit_perf.py"
    exec(compile(v14_script.read_text("utf-8"),str(v14_script),"exec"),v14_module.__dict__)
    v14_path="bbport/gpu/shim/bbport_overlay.cpp"
    v14_result=v14_module.transform(output[v14_path].decode("utf-8"))
    for name,contents in v14_result.items():
        output[name]=contents.encode("utf-8")
    if len(output)!=len(dest)+10:
        raise ValueError("V14 quit/perf generated header is missing")
    # V16: fix 3D map GPU buffer and descriptor ownership only. No changes
    # to gameplay textures, overlay menus, network or the production server.
    v16_dir=Path(__file__).resolve().parent.parent/"map-safety-v16"
    v16_module=types.ModuleType("sh_map_safety_patch")
    v16_script=v16_dir/"patch_map.py"
    exec(compile(v16_script.read_text("utf-8"),str(v16_script),"exec"),v16_module.__dict__)
    output[MAP3D]=v16_module.transform(source[MAP3D]).encode("utf-8")
    if len(output)!=len(dest)+11:
        raise ValueError("V16 3D map native source is missing")
    # V17: only guard active texture attachments against eviction.
    # Stale depth reclamation remains opt-in for explicit GPU tests.
    v17_dir=Path(__file__).resolve().parent.parent/"gc-safety-v17"
    v17_module=types.ModuleType("sh_gc_safety_patch")
    v17_script=v17_dir/"patch_texture_gc.py"
    exec(compile(v17_script.read_text("utf-8"),str(v17_script),"exec"),v17_module.__dict__)
    output[TEXTURE_GC]=v17_module.transform(source[TEXTURE_GC]).encode("utf-8")
    if len(output)!=len(dest)+12:
        raise ValueError("V17 texture GC native source is missing")
    # V18: bound the resident CPU-side chart and mesh cache and allow
    # the asynchronous worker to shut down safely on normal process exit.
    v18_dir=Path(__file__).resolve().parent.parent/"map-cache-v18"
    v18_module=types.ModuleType("sh_map_cache_patch")
    v18_script=v18_dir/"patch_chart_cache.py"
    exec(compile(v18_script.read_text("utf-8"),str(v18_script),"exec"),v18_module.__dict__)
    output[MAPCHARTS]=v18_module.transform(source[MAPCHARTS]).encode("utf-8")
    output[v18_module.HEADER_PATH]=(v18_dir/"sh_map_cache.hpp").read_bytes()
    if len(output)!=len(dest)+14:
        raise ValueError("V18 map worker/cache source or header missing")
    # V19: defend compressed, persisted map and mesh input decoding against
    # oversized headers and corrupted archive spans before allocating RAM.
    v19_dir=Path(__file__).resolve().parent.parent/"map-data-v19"
    v19_module=types.ModuleType("sh_map_data_patch")
    v19_script=v19_dir/"patch_map_data.py"
    exec(compile(v19_script.read_text("utf-8"),str(v19_script),"exec"),v19_module.__dict__)
    output[MAPART]=v19_module.transform(source[MAPART]).encode("utf-8")
    if len(output)!=len(dest)+15:
        raise ValueError("V19 map data parser native source is missing")
    for path in output:
        if path.startswith("/") or ".." in Path(path).parts:
            raise ValueError("unsafe relative path "+path)
    meta={
        "upstream_pin":PIN,
        "applied":["V3 in-game UI scale","V5 DBNO protocol 8",
                   "V7 native P2P hooks (dormant)","V8 Github update channel",
                   "V10 direct channel guard","V11 optional last-hunt title reconnect",
                   "V13 down-only Follow/Free spectator camera",
                   "V14 confirmed quit and opt-in long-session performance diagnostics",
                   "V16 defensive Vulkan map allocation, descriptor and input guards",
                   "V17 active GPU resource GC protection (opt-in stale depth)",
                   "V18 bounded CPU map cache and stop-aware map worker",
                   "V19 bounded compressed map/mesh decoding and safe archive spans"],
        "protocol":8,
        "direct_udp":"NOT ENABLED: authenticated server candidates/keys missing",
        "matchmaking":"V4 not wired to Qt or actual game UI",
        "public_release_ready":False,
        "sha256":{k:sha(v) for k,v in sorted(output.items())},
    }
    return output,meta

def run(checkout:Path, repo:Path, out:Path):
    checkout=checkout.resolve();repo=repo.resolve();out=out.resolve()
    if out==checkout or checkout in out.parents or out==repo or repo in out.parents:
        raise ValueError("output must be outside upstream and Git repository")
    actual=subprocess.check_output(["git","-C",str(checkout),"rev-parse","HEAD"],text=True).strip()
    if actual!=PIN:raise ValueError("wrong upstream SHA "+actual)
    if out.exists() and any(out.iterdir()):
        raise FileExistsError("destination is not empty")
    archives=repo/"tools/poc/yharnam/pinned-archives"
    patch_path=repo/"tools/poc/yharnam/release-v8/patch_update_channel.py"
    v8=types.ModuleType("sh_v8")
    exec(compile(patch_path.read_text("utf-8"),str(patch_path),"exec"),v8.__dict__)
    v5=load_zip_module(archives/ARCHIVES["dbno"],"patch_native_dbno.py","v5_dbno_init")
    required=set(v5.PATCHES)|{NETWORK,COOP,LAUNCHER,MAP3D,TEXTURE_GC,MAPCHARTS,MAPART,"bbport/src/runtime_camhook.c","bbport/src/runtime_pad.c"}
    sources={name:(checkout/name).read_text(encoding="utf-8") for name in required}
    files,meta=compose(sources,archives,v8)
    # All source anchors and input hashes are checked before writing anything.
    out.mkdir(parents=True,exist_ok=True)
    for path, data in files.items():
        destination=out/path
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_bytes(data)
    (out/"SEAMLESS-HUNT-COMPOSE-MANIFEST.json").write_text(
        json.dumps(meta,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("COMPOSE_PASS",len(files),"files; pinned source",PIN)
    print("NOT A GAME BUILD. Server-side authenticated P2P and Qt lobby are missing.")
    return meta

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--upstream",required=True,type=Path)
    parser.add_argument("--repo",default=".",type=Path)
    parser.add_argument("--out",required=True,type=Path)
    args=parser.parse_args()
    run(args.upstream,args.repo,args.out)
