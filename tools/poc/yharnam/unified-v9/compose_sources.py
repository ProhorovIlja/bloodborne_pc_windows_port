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
SAVE_EDITOR = "bbport/gpu/shim/bbport_save_editor.cpp"
SAVE_EDITOR_H = "bbport/gpu/shim/bbport_save_editor.h"
SERVER_BOARDS = "server/src/bloodborne_party_boards.cpp"
SERVER_WORLD = "server/src/bloodborne_world.cpp"
SERVER_WORLD_H = "server/src/bloodborne_world.h"
COOP_STREAM = "server/coop/coop_stream.h"
SERVER_LINK_CPP = "server/src/server_link.cpp"
SERVER_LINK_H = "server/src/server_link.h"
LINK_SERVER_CPP = "server/src/link_server.cpp"
LINK_SERVER_H = "server/src/link_server.h"
DATABASE_CPP = "server/src/database.cpp"
DATABASE_H = "server/src/database.h"
ACCOUNT_TEST_CPP = "server/tests/test_accounts.cpp"
HTTP_CPP = "server/src/webapi_server.cpp"
HTTP_SESSION_CPP = "server/src/webapi_routes_session.cpp"
SERVER_LINK_TEST = "server/tests/test_server_link.cpp"
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
    v10_guard.__file__=str(v10_py)
    exec(compile(v10_py.read_text("utf-8"),str(v10_py),"exec"),v10_guard.__dict__)
    adapter_path="emulator/src/core/libraries/network/native_shlk_adapter.hpp"
    output[adapter_path]=v10_guard.patch_adapter(output[adapter_path].decode("utf-8")).encode("utf-8")
    output["emulator/src/core/libraries/network/native_direct_filter.hpp"]=(v10_dir/"native_direct_filter.hpp").read_bytes()
    # V11: apply title-screen last-hunt preference last, because DBNO and the
    # UI scale already touch the same native Team menu.
    v11_dir=Path(__file__).resolve().parent.parent/"last-session-v11"
    v11_patch=types.ModuleType("sh_native_resume_patch")
    v11_file=v11_dir/"patch_native_resume.py"
    v11_patch.__file__=str(v11_file)
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
    v13_module.__file__=str(v13_script)
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
    v14_module.__file__=str(v14_script)
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
    v16_module.__file__=str(v16_script)
    exec(compile(v16_script.read_text("utf-8"),str(v16_script),"exec"),v16_module.__dict__)
    output[MAP3D]=v16_module.transform(source[MAP3D]).encode("utf-8")
    if len(output)!=len(dest)+11:
        raise ValueError("V16 3D map native source is missing")
    # V17: only guard active texture attachments against eviction.
    # Stale depth reclamation remains opt-in for explicit GPU tests.
    v17_dir=Path(__file__).resolve().parent.parent/"gc-safety-v17"
    v17_module=types.ModuleType("sh_gc_safety_patch")
    v17_script=v17_dir/"patch_texture_gc.py"
    v17_module.__file__=str(v17_script)
    exec(compile(v17_script.read_text("utf-8"),str(v17_script),"exec"),v17_module.__dict__)
    output[TEXTURE_GC]=v17_module.transform(source[TEXTURE_GC]).encode("utf-8")
    if len(output)!=len(dest)+12:
        raise ValueError("V17 texture GC native source is missing")
    # V18: bound the resident CPU-side chart and mesh cache and allow
    # the asynchronous worker to shut down safely on normal process exit.
    v18_dir=Path(__file__).resolve().parent.parent/"map-cache-v18"
    v18_module=types.ModuleType("sh_map_cache_patch")
    v18_script=v18_dir/"patch_chart_cache.py"
    v18_module.__file__=str(v18_script)
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
    v19_module.__file__=str(v19_script)
    exec(compile(v19_script.read_text("utf-8"),str(v19_script),"exec"),v19_module.__dict__)
    output[MAPART]=v19_module.transform(source[MAPART]).encode("utf-8")
    if len(output)!=len(dest)+15:
        raise ValueError("V19 map data parser native source is missing")
    # V20 follows V18 on the SAME map_charts.cpp. Apply to the composed
    # V18 output, otherwise the LRU/worker fixes would be silently overwritten.
    v20_dir=Path(__file__).resolve().parent.parent/"map-range-v20"
    v20_module=types.ModuleType("sh_map_range_patch")
    v20_script=v20_dir/"patch_map_range.py"
    v20_module.__file__=str(v20_script)
    exec(compile(v20_script.read_text("utf-8"),str(v20_script),"exec"),v20_module.__dict__)
    output[MAPCHARTS]=v20_module.transform(output[MAPCHARTS].decode("utf-8")).encode("utf-8")
    output[v20_module.HEADER_PATH]=(v20_dir/"sh_map_range_io.hpp").read_bytes()
    if len(output)!=len(dest)+16:
        raise ValueError("V20 safe range-reading native header is missing")
    # V21: AFTER all UI composition, remove gameplay cheats from graphics
    # settings and put them beside character-editing tools. Enforce editing
    # permission in the queued game-thread code, not merely in the UI.
    v21_dir=Path(__file__).resolve().parent.parent/"hunter-tools-v21"
    v21_module=types.ModuleType("sh_hunter_tools_patch")
    v21_script=v21_dir/"patch_hunter_tools.py"
    v21_module.__file__=str(v21_script)
    exec(compile(v21_script.read_text("utf-8"),str(v21_script),"exec"),v21_module.__dict__)
    v21_sources={
        v21_module.OVERLAY:output[OVERLAY].decode("utf-8"),
        v21_module.EDITOR:source[SAVE_EDITOR],
        v21_module.HEADER:source[SAVE_EDITOR_H],
        # These already have V5/V11 co-op edits; patch the composed versions.
        v21_module.COOP_API:output["bbport/gpu/bbcoop.h"].decode("utf-8"),
        v21_module.COOP_IMPL:output["bbport/gpu/bbcoop/coop.cpp"].decode("utf-8"),
    }
    for path, contents in v21_module.transform(v21_sources).items():
        output[path]=contents.encode("utf-8")
    output["bbport/gpu/shim/sh_hunter_tools_policy.hpp"]=(v21_dir/"sh_hunter_tools_policy.hpp").read_bytes()
    if len(output)!=len(dest)+19:
        raise ValueError("V21 Hunter Tools editor/UI/policy outputs are missing")
    # V22: apply to the composed server source. No production daemon is deployed
    # or reconfigured by this source-only step. Cheap per-message sanity checks.
    v22_dir=Path(__file__).resolve().parent.parent/"server-trust-v22"
    v22_module=types.ModuleType("sh_server_trust_patch")
    v22_script=v22_dir/"patch_server_trust.py"
    v22_module.__file__=str(v22_script)
    exec(compile(v22_script.read_text("utf-8"),str(v22_script),"exec"),v22_module.__dict__)
    v22_paths=(v22_module.BOARDS,v22_module.WORLD,v22_module.WORLD_H)
    v22_sources={name:(output[name].decode("utf-8") if name in output else source[name]) for name in v22_paths}
    for name, contents in v22_module.transform(v22_sources).items():
        output[name]=contents.encode("utf-8")
    if v22_module.GUARD not in output or not output[v22_module.GUARD]:
        raise ValueError("V22 dedicated co-op server sanity header missing")
    # V24: cap partially-received protobuf envelopes for both game and server.
    # Stage as source only; NEVER restart or reconfigure the production daemon.
    v24_dir=Path(__file__).resolve().parent.parent/"stream-bounds-v24"
    v24_module=types.ModuleType("sh_stream_bounds_patch")
    v24_script=v24_dir/"patch_stream.py"
    v24_module.__file__=str(v24_script)
    exec(compile(v24_script.read_text("utf-8"),str(v24_script),"exec"),v24_module.__dict__)
    output[COOP_STREAM]=v24_module.transform(output[COOP_STREAM].decode("utf-8") if COOP_STREAM in output else source[COOP_STREAM]).encode("utf-8")
    output["server/coop/sh_message_bounds.hpp"]=(v24_dir/"sh_message_bounds.hpp").read_bytes()
    if "server/coop/sh_message_bounds.hpp" not in output or not output["server/coop/sh_message_bounds.hpp"]:
        raise ValueError("V24 bounded stream assembler header missing")
    # V25: strict public rooms may opt in to binding Hello.member and
    # LobbyHello.member to the separately verified network-link online ID.
    # Legacy co-op behavior stays identical while strict mode is disabled.
    v25_dir=Path(__file__).resolve().parent.parent/"member-identity-v25"
    v25_module=types.ModuleType("sh_member_identity_patch")
    v25_script=v25_dir/"patch_identity.py"
    v25_module.__file__=str(v25_script)
    exec(compile(v25_script.read_text("utf-8"),str(v25_script),"exec"),v25_module.__dict__)
    v25_sources={v25_module.WORLD:output[SERVER_WORLD].decode("utf-8"),
                 v25_module.LINK:output[SERVER_LINK_CPP].decode("utf-8") if SERVER_LINK_CPP in output else source[SERVER_LINK_CPP]}
    for name, contents in v25_module.transform(v25_sources).items():
        output[name]=contents.encode("utf-8")
    if v25_module.HEADER not in output or not output[v25_module.HEADER]:
        raise ValueError("V25 authenticated member identity header missing")
    # V26: per-connection admission of complete co-op messages before
    # protobuf deserialization; strict rooms only, old PvE unchanged.
    v26_dir=Path(__file__).resolve().parent.parent/"ingress-quota-v26"
    v26_module=types.ModuleType("sh_ingress_quota_patch")
    v26_script=v26_dir/"patch_ingress_quota.py"
    v26_module.__file__=str(v26_script)
    exec(compile(v26_script.read_text("utf-8"),str(v26_script),"exec"),v26_module.__dict__)
    v26_sources={v26_module.WORLD:output[SERVER_WORLD].decode("utf-8"),
                 v26_module.WORLD_H:output[SERVER_WORLD_H].decode("utf-8")}
    for name, contents in v26_module.transform(v26_sources).items():
        output[name]=contents.encode("utf-8")
    if v26_module.HEADER not in output or not output[v26_module.HEADER]:
        raise ValueError("V26 pre-protobuf rate-limiting header missing")
    # V27: a same-endpoint account switch must retire stale virtual-address
    # routes and notify the old game session before registering the new ID.
    v27_dir=Path(__file__).resolve().parent.parent/"endpoint-rebind-v27"
    v27_module=types.ModuleType("sh_endpoint_rebind_patch")
    v27_script=v27_dir/"patch_rebind.py"
    v27_module.__file__=str(v27_script)
    exec(compile(v27_script.read_text("utf-8"),str(v27_script),"exec"),v27_module.__dict__)
    v27_paths=(v27_module.LINK,v27_module.LINK_H,v27_module.LINK_SERVER,v27_module.TEST)
    v27_sources={p:(output[p].decode("utf-8") if p in output else source[p]) for p in v27_paths}
    for name, contents in v27_module.transform_all(v27_sources).items():
        output[name]=contents.encode("utf-8")
    if v27_module.HEADER not in output or not output[v27_module.HEADER]:
        raise ValueError("V27 endpoint rebind policy header missing")
    # V28: inexpensive admission BEFORE database/KDF login checks.
    # Must run AFTER V27, since both update server_link.cpp/h and the Qt test.
    v28_dir=Path(__file__).resolve().parent.parent/"login-admission-v28"
    v28_module=types.ModuleType("sh_login_admission_patch")
    v28_script=v28_dir/"patch_login_admission.py"
    v28_module.__file__=str(v28_script)
    exec(compile(v28_script.read_text("utf-8"),str(v28_script),"exec"),v28_module.__dict__)
    v28_paths=(v28_module.LINK_CPP,v28_module.LINK_H,v28_module.QT_TEST)
    v28_sources={p:(output[p].decode("utf-8") if p in output else source[p]) for p in v28_paths}
    for name, contents in v28_module.transform(v28_sources).items():
        output[name]=contents.encode("utf-8")
    if v28_module.HEADER not in output or not output[v28_module.HEADER]:
        raise ValueError("V28 bounded pre-database auth admission header missing")
    # V29: bound local RPC pre-connect and socket output buffers. Bound cached
    # authenticated accounts to avoid memory growth under account churn.
    v29_dir=Path(__file__).resolve().parent.parent/"rpc-budget-v29"
    v29_module=types.ModuleType("sh_rpc_budget_patch")
    v29_script=v29_dir/"patch_rpc_budget.py"
    v29_module.__file__=str(v29_script)
    exec(compile(v29_script.read_text("utf-8"),str(v29_script),"exec"),v29_module.__dict__)
    v29_sources={v29_module.LINK:output[LINK_SERVER_CPP].decode("utf-8") if LINK_SERVER_CPP in output else source[LINK_SERVER_CPP],
                 v29_module.HEADER:output[LINK_SERVER_H].decode("utf-8") if LINK_SERVER_H in output else source[LINK_SERVER_H]}
    for name, contents in v29_module.transform(v29_sources).items():
        output[name]=contents.encode("utf-8")
    if v29_module.GUARD not in output or not output[v29_module.GUARD]:
        raise ValueError("V29 bounded RPC and credential-cache header missing")
    # V30: cached login decisions must observe live database bans/deletions/
    # password rotations. Check only the indexed status query on cache hits.
    v30_dir=Path(__file__).resolve().parent.parent/"auth-revocation-v30"
    v30_module=types.ModuleType("sh_auth_revocation_patch")
    v30_script=v30_dir/"patch_auth_revocation.py"
    v30_module.__file__=str(v30_script)
    exec(compile(v30_script.read_text("utf-8"),str(v30_script),"exec"),v30_module.__dict__)
    v30_paths=(v30_module.DB_H,v30_module.DB_CPP,v30_module.LINK_H,
               v30_module.LINK_CPP,v30_module.ACCOUNT_TEST)
    v30_sources={p:(output[p].decode("utf-8") if p in output else source[p]) for p in v30_paths}
    for name, contents in v30_module.transform(v30_sources).items():
        output[name]=contents.encode("utf-8")
    if v30_module.POLICY not in output or not output[v30_module.POLICY]:
        raise ValueError("V30 auth cache revocation policy header missing")
    # CI-discovered Qt6.4 <-> Qt6.8+ WebApiServer ABI difference.
    qt_dir=Path(__file__).resolve().parent.parent/"qt-http-compat-v30"
    qt_module=types.ModuleType("sh_qt_http_compat")
    qt_script=qt_dir/"patch_http_compat.py"
    qt_module.__file__=str(qt_script)
    exec(compile(qt_script.read_text("utf-8"),str(qt_script),"exec"),qt_module.__dict__)
    qt_src=output[HTTP_CPP].decode("utf-8") if HTTP_CPP in output else source[HTTP_CPP]
    output[HTTP_CPP]=qt_module.transform(qt_src).encode("utf-8")
    utc_src=output[HTTP_SESSION_CPP].decode("utf-8") if HTTP_SESSION_CPP in output else source[HTTP_SESSION_CPP]
    output[HTTP_SESSION_CPP]=qt_module.transform_session(utc_src).encode("utf-8")
    # V31 is isolated from the production daemon: only an explicit setting
    # enables bounded active-account rechecks. Normal disconnect cleanup is
    # handled by the existing Hub::Tick -> Result.gone path.
    v31_dir=Path(__file__).resolve().parent.parent/"active-session-v31"
    v31_module=types.ModuleType("sh_active_session_patch")
    v31_script=v31_dir/"patch_active_session.py"
    v31_module.__file__=str(v31_script)
    exec(compile(v31_script.read_text("utf-8"),str(v31_script),"exec"),v31_module.__dict__)
    v31_paths=(v31_module.LINK_H,v31_module.LINK_CPP,v31_module.SERVER_CPP,v31_module.QT_TEST)
    v31_sources={p:(output[p].decode("utf-8") if p in output else source[p]) for p in v31_paths}
    for name,contents in v31_module.transform(v31_sources).items():
        output[name]=contents.encode("utf-8")
    if v31_module.POLICY not in output or not output[v31_module.POLICY]:
        raise ValueError("V31 active-account bounded status policy missing")
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
                   "V19 bounded compressed map/mesh decoding and safe archive spans",
                   "V20 bounded and exact game archive range I/O",
                   "V21 offline-only unlocked Hunter Tools and separate gameplay cheats",
                   "V22 server ingress vitals bounds, saturating revive totals and sparse audit",
                   "V24 bounded co-op protobuf reassembly (8 MiB per peer)",
                   "V25 opt-in signed-in identity binding (legacy compatible)",
                   "V26 opt-in co-op ingress quotas (pre-protobuf)",
                   "V27 stale virtual-address cleanup on changed transport identity",
                   "V28 opt-in bounded pre-database Hello admission",
                   "V29 bounded local RPC backpressure and signed-in credential cache",
                   "V30 live DB verification of cached account password and ban status",
                   "Qt 6.4 / modern WebAPI ABI compatibility from full server build",
                   "Qt 6.4 / modern WebAPI session invitation UTC timestamp compatibility",
                   "V31 staging: opt-in active account revocation and complete matchmaking departure cleanup"],
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
    v8.__file__=str(patch_path)
    exec(compile(patch_path.read_text("utf-8"),str(patch_path),"exec"),v8.__dict__)
    v5=load_zip_module(archives/ARCHIVES["dbno"],"patch_native_dbno.py","v5_dbno_init")
    required=set(v5.PATCHES)|{NETWORK,COOP,LAUNCHER,MAP3D,TEXTURE_GC,MAPCHARTS,MAPART,SAVE_EDITOR,SAVE_EDITOR_H,SERVER_BOARDS,SERVER_WORLD,SERVER_WORLD_H,COOP_STREAM,SERVER_LINK_CPP,SERVER_LINK_H,LINK_SERVER_CPP,LINK_SERVER_H,DATABASE_CPP,DATABASE_H,ACCOUNT_TEST_CPP,HTTP_CPP,HTTP_SESSION_CPP,SERVER_LINK_TEST,"bbport/src/runtime_camhook.c","bbport/src/runtime_pad.c"}
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
