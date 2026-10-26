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
HTTP_STATS_CPP = "server/src/stats_server.cpp"
HTTP_BACKEND_CPP = "server/src/bloodborne_backend_server.cpp"
HTTP_BLOODBORNE_CPP = "server/src/webapi_routes_bloodborne.cpp"
WEB_AUTH_CPP = "server/src/webapi_auth.cpp"
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
    # Native Linux CI on Qt6.4 revealed another modern-only Qt API in
    # invitation timestamp serialization, separate from WebApiServer.
    utc_src=output[HTTP_SESSION_CPP].decode("utf-8") if HTTP_SESSION_CPP in output else source[HTTP_SESSION_CPP]
    output[HTTP_SESSION_CPP]=qt_module.transform_session(utc_src).encode("utf-8")
    stats_src=output[HTTP_STATS_CPP].decode("utf-8") if HTTP_STATS_CPP in output else source[HTTP_STATS_CPP]
    output[HTTP_STATS_CPP]=qt_module.transform_stats(stats_src).encode("utf-8")
    backend_src=output[HTTP_BACKEND_CPP].decode("utf-8") if HTTP_BACKEND_CPP in output else source[HTTP_BACKEND_CPP]
    output[HTTP_BACKEND_CPP]=qt_module.transform_backend(backend_src).encode("utf-8")
    # Qt 6.4 also lacks QHttpHeaders in the Bloodborne summon messenger.
    # Its placement header is required for cross-area joins: never drop it.
    summon_src=output[HTTP_BLOODBORNE_CPP].decode("utf-8") if HTTP_BLOODBORNE_CPP in output else source[HTTP_BLOODBORNE_CPP]
    output[HTTP_BLOODBORNE_CPP]=qt_module.transform_bloodborne(summon_src).encode("utf-8")
    # V32: existing WebAPI bearer tokens must not bypass account bans.
    # Account website/device login remains UNIMPLEMENTED, not implicitly
    # treated as this legacy bearer credential.
    v32_dir=Path(__file__).resolve().parent.parent/"account-gateway-v32"
    v32_module=types.ModuleType("sh_account_gateway_v32")
    v32_script=v32_dir/"patch_bearer_auth.py"
    v32_module.__file__=str(v32_script)
    exec(compile(v32_script.read_text("utf-8"),str(v32_script),"exec"),v32_module.__dict__)
    v32_src={v32_module.WEB_AUTH:output[WEB_AUTH_CPP].decode("utf-8") if WEB_AUTH_CPP in output else source[WEB_AUTH_CPP],
             v32_module.DATABASE:output[DATABASE_CPP].decode("utf-8") if DATABASE_CPP in output else source[DATABASE_CPP]}
    for name, contents in v32_module.transform(v32_src).items():
        output[name]=contents.encode("utf-8")
    # V46: Yharnam Together BLauncher remains the *only* launcher.
    # Opt-in remote GUEST profiles can use separate staging Fornex ports
    # (UDP 32314, WebAPI 32315, game backend 21443). Ordinary/local host
    # clients remain on the original 31314/31315/20443 defaults.
    v46_script=Path(__file__).resolve().parent.parent/"remote-profile-v46/patch_remote_ports.py"
    v46_module=types.ModuleType("sh_v46_launcher_remote_ports")
    v46_module.__file__=str(v46_script)
    exec(compile(v46_script.read_text("utf-8"),str(v46_script),"exec"),v46_module.__dict__)
    remote_source={v46_module.COOP:output[COOP].decode("utf-8"),
                   v46_module.LAUNCHER:output[LAUNCHER].decode("utf-8")}
    for name,body in v46_module.transform(remote_source).items():
        output[name]=body.encode("utf-8")
    # V66: actual pinned Qt shadNet Hub read-only authenticated pair gate.
    # Requires signed-in current same-team game links and a server-authoritative
    # mutual opt-in callback. The callback is intentionally NOT installed:
    # without a secure server-issued grant/control channel, runtime stays relay.
    v66_script=Path(__file__).resolve().parent.parent/"hybrid-transport-v52/patch_authenticated_pair.py"
    v66_module=types.ModuleType("sh_v66_authenticated_pair")
    v66_module.__file__=str(v66_script)
    exec(compile(v66_script.read_text("utf-8"),str(v66_script),"exec"),v66_module.__dict__)
    v66_paths=(v66_module.HEADER,v66_module.SOURCE,v66_module.TEST)
    v66_sources={p:output[p].decode("utf-8") for p in v66_paths}
    for p, contents in v66_module.transform(v66_sources).items():
        output[p]=contents.encode("utf-8")
    # V67: server-internal ephemeral pair snapshots, validated against
    # re-hello generation, same party and current authoritative world epoch.
    # Never serialize snapshots as client grants or distribute keys over SHLK.
    v67_script=Path(__file__).resolve().parent.parent/"hybrid-transport-v52/patch_pair_snapshot.py"
    v67_module=types.ModuleType("sh_v67_pair_snapshot")
    v67_module.__file__=str(v67_script)
    exec(compile(v67_script.read_text("utf-8"),str(v67_script),"exec"),v67_module.__dict__)
    v67_paths=(v67_module.HEADER,v67_module.SOURCE,v67_module.TEST)
    v67_sources={p:output[p].decode("utf-8") for p in v67_paths}
    for p, contents in v67_module.transform(v67_sources).items():
        output[p]=contents.encode("utf-8")
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
                   "V66 signed-in same-party, build, liveness and bidirectional consent gate (default deny)",
                   "V67 ephemeral Qt Hub pair snapshot revoked by re-hello, world epoch and consent",
                   "Qt 6.4 / modern WebAPI ABI compatibility from full server build",
                   "Qt 6.4 / modern WebAPI session invitation UTC timestamp compatibility",
                   "Qt 6.4 / modern StatsServer and BloodborneBackendServer HTTP API compatibility",
                   "Qt 6.4 / modern Bloodborne cross-area summon HTTP header compatibility",
                   "V32 WebAPI bearer rejects banned users, indexed SQLite token lookup; no web login yet",
                    "V46 explicit guest-only remote staging UDP/WebAPI/backend ports in original BLauncher"],
        "protocol":8,
        "direct_udp":"NOT ENABLED: authenticated server candidates/keys missing",
        "matchmaking":"V4 not wired to Qt or actual game UI",
        "remote_fornex_staging_ports":"OPT-IN guest-only profile; defaults untouched; no game connection tested",
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
    required=set(v5.PATCHES)|{NETWORK,COOP,LAUNCHER,MAP3D,TEXTURE_GC,MAPCHARTS,MAPART,SAVE_EDITOR,SAVE_EDITOR_H,SERVER_BOARDS,SERVER_WORLD,SERVER_WORLD_H,COOP_STREAM,SERVER_LINK_CPP,SERVER_LINK_H,LINK_SERVER_CPP,LINK_SERVER_H,DATABASE_CPP,DATABASE_H,ACCOUNT_TEST_CPP,HTTP_CPP,HTTP_SESSION_CPP,HTTP_STATS_CPP,HTTP_BACKEND_CPP,HTTP_BLOODBORNE_CPP,WEB_AUTH_CPP,SERVER_LINK_TEST,"bbport/src/runtime_camhook.c","bbport/src/runtime_pad.c"}
    sources={name:(checkout/name).read_text(encoding="utf-8") for name in required}
    files,meta=compose(sources,archives,v8)
    # V69: apply runtime-only optional byte/packet counters to the ENTIRE
    # original p2p_sockets.cpp after the pinned source has been composed.
    # Strict anchor matching ensures a changed V7 transport is never silently
    # patched. The source-only synthetic unit fixtures intentionally do not
    # approximate the whole 1,600-line native game socket translation unit.
    metrics_dir=repo/"tools/poc/yharnam/hybrid-transport-v52"
    metrics_script=metrics_dir/"patch_native_route_metrics.py"
    metrics=types.ModuleType("sh_v69_native_metrics")
    metrics.__file__=str(metrics_script)
    exec(compile(metrics_script.read_text("utf-8"),str(metrics_script),"exec"),metrics.__dict__)
    files[NETWORK]=metrics.patch(files[NETWORK].decode("utf-8")).encode("utf-8")
    files[metrics.HEADER]=(metrics_dir/"sh_route_metrics.hpp").read_bytes()
    meta["applied"].append("V69 opt-in real native P2PTransport relay volume counters")
    # V70: REAL physical UDP ReceiveMain can now recognize a MAC-authenticated
    # SHP1 peer payload and restore the server-attested virtual game endpoint.
    # No trusted install/Arm exists yet: every peer SHP1 packet drops by default.
    # The legacy SHLK server relay path and default user settings are unchanged.
    ingress_script=metrics_dir/"patch_native_direct_rx.py"
    v70=types.ModuleType("sh_v70_native_direct_rx")
    v70.__file__=str(ingress_script)
    exec(compile(ingress_script.read_text("utf-8"),str(ingress_script),"exec"),v70.__dict__)
    files[NETWORK]=v70.patch(files[NETWORK].decode("utf-8")).encode("utf-8")
    for filename in v70.DIRECT_HEADERS:
        path="emulator/src/core/libraries/network/"+filename
        files[path]=(metrics_dir/filename).read_bytes()
    meta["applied"].append("V70 fail-closed HMAC direct RX hook in native P2PTransport socket")
    # V71: Direct-first SEND boundary in actual native P2PTransport::SendFrame.
    # The trusted server-grant installer does not exist, so it remains RELAY.
    tx_script=metrics_dir/"patch_native_direct_tx.py"
    v71=types.ModuleType("sh_v71_native_direct_tx")
    v71.__file__=str(tx_script)
    exec(compile(tx_script.read_text("utf-8"),str(tx_script),"exec"),v71.__dict__)
    files[NETWORK]=v71.patch(files[NETWORK].decode("utf-8")).encode("utf-8")
    files["emulator/src/core/libraries/network/sh_native_direct_tx.hpp"]=(metrics_dir/"sh_native_direct_tx.hpp").read_bytes()
    meta["applied"].append("V71 fail-closed native SendFrame Direct/Relay TX hook")
    # V72: LinkServer's snapshot epoch must read the real BloodborneWorld
    # party/map/area/owner revision, not client-supplied booleans. Mutual
    # P2P consent remains unconfigured => still no live direct grants.
    v72_script=metrics_dir/"patch_live_world_epoch.py"
    v72=types.ModuleType("sh_v72_authoritative_world_epoch")
    v72.__file__=str(v72_script)
    exec(compile(v72_script.read_text("utf-8"),str(v72_script),"exec"),v72.__dict__)
    affected={p:files[p].decode("utf-8") for p in (v72.WORLD_H,v72.WORLD_CPP,v72.LINK_CPP)}
    for path,body in v72.transform(affected).items():
        files[path]=body.encode("utf-8")
    files[v72.REVISION_H]=(metrics_dir/"sh_world_revision.hpp").read_bytes()
    # Extend the ORIGINAL server world tests; do not rely solely on a toy
    # revision helper. These tests compile/run against actual Qt+protobuf
    # when the entire server candidate is built.
    original_world_tests=(checkout/v72.WORLD_TEST).read_text(encoding="utf-8")
    files[v72.WORLD_TEST]=v72.transform_test(original_world_tests).encode("utf-8")
    meta["applied"].append("V72 server-derived party/map/owner world epoch for P2P candidate revocation")
    # V73: even if a future caller claims reliable-stream authority, the
    # REAL native TX/RX header hardcodes the handover gate to false until the
    # original GameLink ACK/sequence/retransmit lane has genuinely migrated.
    # Header bytes are already staged by V70/V71; record exactly what ships.
    meta["applied"].append("V73 native Direct allows only ACK-free unreliable game frames until reliable GameLink migration")
    # V74: a newer native client may explicitly opt in using an optional
    # protobuf Hello field. ORIGINAL legacy clients emit no field => DENY.
    # The shadNet Qt world holds each client's consent from its signed-in
    # link, and the real Hub checks BOTH directions. Crucially this neither
    # distributes addresses/keys nor Arm()s client Direct sockets yet.
    v74_script=metrics_dir/"patch_mutual_p2p_consent.py"
    v74=types.ModuleType("sh_v74_mutual_p2p_consent")
    v74.__file__=str(v74_script)
    exec(compile(v74_script.read_text("utf-8"),str(v74_script),"exec"),v74.__dict__)
    v74_paths=(v74.PROTO,v74.WORLD_H,v74.WORLD_CPP,v74.LINK_CPP,
               v74.CLIENT_WORLD,v74.WORLD_TEST)
    v74_sources={p:(files[p] if p in files else (checkout/p).read_bytes()).decode("utf-8")
                 for p in v74_paths}
    for path,body in v74.transform(v74_sources).items():
        files[path]=body.encode("utf-8")
    meta["applied"].append("V74 opt-in protobuf native client Hello + game-world mutual consent, legacy DENY")
    # V75: stage the same AES-256-GCM sealed-offer codec on BOTH game and
    # original Qt server. Not included/called by any production transport yet:
    # TLS-exporter keying, mutual TLS identities and grant issuance still
    # require their authenticated control-plane integration.
    sealed_header=(metrics_dir/"sh_secure_grant.hpp").read_bytes()
    files["emulator/src/core/libraries/network/sh_secure_grant.hpp"]=sealed_header
    files["server/src/sh_secure_grant.hpp"]=sealed_header
    # The server-side codec's header imports the primitive from the same
    # source tree, not via the game's include search path.
    for shared in ("sh_direct_crypto.hpp","sh_direct_datagram.hpp"):
        files["server/src/"+shared]=(metrics_dir/shared).read_bytes()
    meta["applied"].append("V75 AES-GCM peer grant offer codec staged; no unencrypted SHLK grant delivery and no game Arm")
    # V76: gather peer addresses/virtual IDs and world revision atomically
    # from the REAL single Qt server game-world state, and require both
    # current account-bound game Hello consents, before future TLS grants.
    # No public/shadNet plaintext endpoint exposes this sensitive snapshot.
    v76_script=metrics_dir/"patch_authoritative_pair_scope.py"
    v76=types.ModuleType("sh_v76_direct_pair_scope")
    v76.__file__=str(v76_script)
    exec(compile(v76_script.read_text("utf-8"),str(v76_script),"exec"),v76.__dict__)
    v76_files={p:files[p].decode("utf-8") for p in (
        v76.WORLD_H,v76.WORLD_CPP,v76.WORLD_TEST)}
    for path,body in v76.patch(v76_files).items():
        files[path]=body.encode("utf-8")
    meta["applied"].append("V76 single authoritative Qt peer scope, two consents, real/virtual endpoints, no key disclosure")
    # V77: a pair can return to the exact same map/team/owner after
    # leaving or a link restart. Include server-only monotonically
    # allocated per-member generations to avoid an old grant matching
    # this apparent same-world (ABA) state. No network/user DB updates.
    v77_script=metrics_dir/"patch_p2p_session_generation.py"
    v77=types.ModuleType("sh_v77_game_link_generation")
    v77.__file__=str(v77_script)
    exec(compile(v77_script.read_text("utf-8"),str(v77_script),"exec"),v77.__dict__)
    for path,body in v77.patch({p:files[p].decode("utf-8") for p in
                               (v77.H,v77.CPP,v77.TEST)}).items():
        files[path]=body.encode("utf-8")
    meta["applied"].append("V77 server-only game link epoch rejects old grants after same-map/owner rejoin")
    # V78: OPTIONAL mutual TLS 1.3 readiness check inside the SAME Qt daemon,
    # localhost-only even when explicitly enabled, otherwise zero listener.
    # It intentionally issues NO grants/peer IPs; cannot fall back to SHLK.
    v78_script=metrics_dir/"patch_tls_local_listener.py"
    v78=types.ModuleType("sh_v78_mtls_local_listener")
    v78.__file__=str(v78_script)
    exec(compile(v78_script.read_text("utf-8"),str(v78_script),"exec"),v78.__dict__)
    main_path=v78.MAIN
    files[main_path]=v78.patch(
        (files[main_path] if main_path in files else (checkout/main_path).read_bytes())
        .decode("utf-8")).encode("utf-8")
    files[v78.HEADER]=(metrics_dir/"sh_p2p_tls_listener.hpp").read_bytes()
    meta["applied"].append("V78 disabled-by-default loopback-only mTLS 1.3 Qt readiness, NO grants")
    # V79: local, operator-pinned SHA256 X.509 certificate -> signed-in
    # current game account and server-owned live link generation. CN/SAN
    # and arbitrary client-provided ID are NEVER accepted as identity.
    # No grants/keys/IPs issued even after a valid V79 BIND.
    v79_script=metrics_dir/"patch_tls_account_binding.py"
    v79=types.ModuleType("sh_v79_live_tls_game_identity")
    v79.__file__=str(v79_script)
    exec(compile(v79_script.read_text("utf-8"),str(v79_script),"exec"),v79.__dict__)
    v79_paths=(v79.MAIN,v79.SERVER_H,v79.SERVER_CPP,v79.LINK_H,
               v79.LINK_CPP,v79.WORLD_H,v79.WORLD_CPP,v79.WORLD_TEST)
    v79_sources={p:(files[p] if p in files else (checkout/p).read_bytes())
                 .decode("utf-8") for p in v79_paths}
    for path,body in v79.patch(v79_sources).items():
        files[path]=body.encode("utf-8")
    files[v79.IDENTITY_H]=(metrics_dir/"sh_p2p_tls_identity.hpp").read_bytes()
    # listener is included in main and now depends on the pinned identity.
    files[v78.HEADER]=(metrics_dir/"sh_p2p_tls_listener.hpp").read_bytes()
    meta["applied"].append("V79 operator X509 SHA256 pin plus LIVE authenticated Qt game epoch, no grants")
    # V80: a uniquely generated wrapping key is sent only INSIDE the
    # verified TLS 1.3 connection to the operator-pinned current game account.
    # A later command on the SAME socket must revalidate V77 link epoch.
    # This is not the future V75 grant-issuance path and offers no peer IPs.
    files["server/src/sh_p2p_tls_key_session.hpp"]=(metrics_dir/"sh_p2p_tls_key_session.hpp").read_bytes()
    files[v78.HEADER]=(metrics_dir/"sh_p2p_tls_listener.hpp").read_bytes()
    meta["applied"].append("V80 per mTLS connection fresh wrapping key and live epoch recheck, NO peer offers")
    # V81: the first (local/dev ONLY) real offer must be minted from
    # server-owned CURRENT signed-in game links and mutual consent, then
    # sealed with V80's one-time TLS application key using V75 AES-GCM.
    # The destination peer is selected by the local server operator, NOT
    # by a user-supplied plaintext SHLK/HTTP/TLS peer identifier.
    v81_script=metrics_dir/"patch_tls_local_offer.py"
    v81=types.ModuleType("sh_v81_tls_local_grant")
    v81.__file__=str(v81_script)
    exec(compile(v81_script.read_text("utf-8"),str(v81_script),"exec"),v81.__dict__)
    v81_paths=(v81.MAIN,v81.SERVER_H,v81.SERVER_CPP,v81.LINK_H,v81.LINK_CPP)
    v81_input={p:files[p].decode("utf-8") for p in v81_paths}
    for path,body in v81.patch(v81_input).items():
        files[path]=body.encode("utf-8")
    cmake_source=(files[v81.CMAKE] if v81.CMAKE in files
                  else (checkout/v81.CMAKE).read_bytes()).decode("utf-8")
    files[v81.CMAKE]=v81.patch_cmake(cmake_source).encode("utf-8")
    files[v81.OFFER_H]=(metrics_dir/"sh_p2p_tls_offer_issuer.hpp").read_bytes()
    files["server/src/sh_p2p_tls_key_session.hpp"]=(metrics_dir/"sh_p2p_tls_key_session.hpp").read_bytes()
    files[v78.HEADER]=(metrics_dir/"sh_p2p_tls_listener.hpp").read_bytes()
    meta["applied"].append("V81 loopback mTLS peer offer from current mutually consenting Qt links, sealed SHG1 once")
    # V82: the ACTUAL native game's P2PTransport now OWNS a fail-closed
    # SHG1 receiver. It is only staged; no native client TLS adapter exists,
    # no public grant installer and NO direct TX/RX Arm calls. Native socket
    # stop / account-reconfigure clear pending secrets, leaving SHLK intact.
    v82_script=metrics_dir/"patch_native_grant_inbox.py"
    v82=types.ModuleType("sh_v82_native_offer_inbox")
    v82.__file__=str(v82_script)
    exec(compile(v82_script.read_text("utf-8"),str(v82_script),"exec"),v82.__dict__)
    files[v82.NETWORK]=v82.patch_game(files[v82.NETWORK].decode("utf-8")).encode("utf-8")
    files[v82.HEADER]=(metrics_dir/"sh_native_grant_inbox.hpp").read_bytes()
    meta["applied"].append("V82 actual native game owns unarmed, replay-protected TLS SHG1 inbox, revoked with account/socket")
    # V83: real non-Qt OpenSSL/LibreSSL TLS 1.3 client, pinned server
    # certificate chain + loopback IP SAN, mutual X509, 1-use V80 key,
    # actual V81 SHG1 -> V82 game-owned inbox. Only a dedicated native
    # developer CMake opt-in exposes its callable entry point. DEFAULT OFF;
    # NO autoconnect, remote endpoint, NAT or Direct Arm call.
    v83_script=metrics_dir/"patch_native_tls_local_client.py"
    v83=types.ModuleType("sh_v83_native_local_mtls")
    v83.__file__=str(v83_script)
    exec(compile(v83_script.read_text("utf-8"),str(v83_script),"exec"),v83.__dict__)
    files[v83.NETWORK]=v83.patch_game(files[v83.NETWORK].decode("utf-8")).encode("utf-8")
    cmake_game=(files[v83.CMAKE] if v83.CMAKE in files
                 else (checkout/v83.CMAKE).read_bytes()).decode("utf-8")
    files[v83.CMAKE]=v83.patch_cmake(cmake_game).encode("utf-8")
    files[v83.HEADER]=(metrics_dir/"sh_native_tls_local_client.hpp").read_bytes()
    meta["applied"].append("V83 real native LibreSSL TLS1.3 client callable DEV-only; default OFF, no Direct Arm")
    # V84/V85: SAME original Qt loopback-only listener now offers an
    # explicit SHG2 version, with full SHA256 IDs and a non-Qt recipient.
    # Keep the production game call site UNWIRED and Direct disabled.
    # These headers are staged to ensure the Qt server and native game
    # have exactly the same audited protocol sources in the combined tree.
    for name in ("sh_secure_grant_v84.hpp",):
        blob=(metrics_dir/name).read_bytes()
        files["server/src/"+name]=blob
        files["emulator/src/core/libraries/network/"+name]=blob
    files["server/src/sh_p2p_tls_offer_v84.hpp"]=(
        metrics_dir/"sh_p2p_tls_offer_v84.hpp").read_bytes()
    for name in ("sh_native_grant_inbox_v84.hpp",
                 "sh_native_tls_local_client_v85.hpp"):
        files["emulator/src/core/libraries/network/"+name]=(
            metrics_dir/name).read_bytes()
    meta["applied"].append(
        "V84-V85 SHG2 256-bit recipient and peer identity, actual Qt/native local TLS source; no production P2P Arm")
    # V86: the *same* original native game P2PTransport stores a SECOND
    # sealed inbox while the dev-only TLS compile flag is enabled. Both
    # account/reconfigure and socket shutdown revoke its pending secrets.
    # No runtime caller, automatic connect, NAT probes, or Direct Arm here.
    v86_script=metrics_dir/"patch_native_shg2_owner_v86.py"
    v86=types.ModuleType("sh_v86_native_fullid_owner")
    v86.__file__=str(v86_script)
    exec(compile(v86_script.read_text("utf-8"),str(v86_script),"exec"),v86.__dict__)
    files[v86.NETWORK]=v86.patch_game(files[v86.NETWORK].decode("utf-8")).encode("utf-8")
    meta["applied"].append("V86 native P2PTransport owns SHG2 inbox, DEV-only OFF and revoked at logout/socket stop; Direct OFF")
    # V87: only the original game P2PTransport's server-welcomed link
    # online_id may become the local SHG2 ID; a link reconnect/build
    # change/quiet epoch must fail closed even for the same account name.
    v87_script=metrics_dir/"patch_native_link_identity_v87.py"
    v87=types.ModuleType("sh_v87_native_accepted_server_link")
    v87.__file__=str(v87_script)
    exec(compile(v87_script.read_text("utf-8"),str(v87_script),"exec"),v87.__dict__)
    files[v87.NETWORK]=v87.patch_game(files[v87.NETWORK].decode("utf-8")).encode("utf-8")
    files[v87.HEADER]=(metrics_dir/"sh_native_game_identity_v87.hpp").read_bytes()
    meta["applied"].append("V87 SHA256 game-self identity requires server Welcome, stable link epoch, Direct OFF")
    # V88: stage full 2-way SHG2 reciprocal pair helper inside original
    # SINGLE Qt shadNet, and add internal server-only capture API.
    # It obtains two current mutually consenting LinkServer snapshots,
    # refuses mismatch, generates a common pair binding and two distinct
    # directional keys. NOT delivered on public TLS / NAT / UDP yet.
    v88_script=metrics_dir/"patch_qt_reciprocal_pair_v88.py"
    v88=types.ModuleType("sh_v88_qt_recipient_pair")
    v88.__file__=str(v88_script)
    exec(compile(v88_script.read_text("utf-8"),str(v88_script),"exec"),v88.__dict__)
    files[v88.HEADER]=(metrics_dir/"sh_p2p_reciprocal_pair_v88.hpp").read_bytes()
    v88_paths=(v88.SERVER_H,v88.SERVER_CPP,v88.LINK_H,v88.LINK_CPP)
    v88_input={p:files[p].decode("utf-8") for p in v88_paths}
    for name,body in v88.patch(v88_input).items():
        files[name]=body.encode("utf-8")
    # V89: shared pair master is delivered to BOTH native clients using
    # separate authenticated TLS keys. Derive direction- and purpose-
    # separated HMAC keys locally; never install the raw master on UDP.
    files["emulator/src/core/libraries/network/sh_pair_key_schedule_v89.hpp"]=(
        metrics_dir/"sh_pair_key_schedule_v89.hpp").read_bytes()
    meta["applied"].append("V88-V89 Qt original LinkServer reciprocal pair, shared SHG2 secret, native directional probe/game KDF (no UDP Arm)")
    # V90: same Qt shadNet loopback TLS listener owns one short-lived
    # server-generated two-recipient pair lease. Each independently pinned
    # TLS session consumes its half ONCE, always after fresh world checks.
    # The separate native client is DEV-only and never auto-connects.
    files["server/src/sh_p2p_pair_lease_v90.hpp"]=(
        metrics_dir/"sh_p2p_pair_lease_v90.hpp").read_bytes()
    files["emulator/src/core/libraries/network/sh_native_tls_local_client_v90.hpp"]=(
        metrics_dir/"sh_native_tls_local_client_v90.hpp").read_bytes()
    meta["applied"].append("V90 original Qt loopback mTLS two-client one-use paired SHG2 lease; game UDP remains relay")
    # V91 staged ONLY: signed NAT reverse challenges using V89 derived probe
    # keys, full 256-bit identities, strict server-authorized endpoints,
    # replay-protected wire + four-step key possession proof. No game
    # socket read/write hook, no Direct Arm, no ACK/routing change.
    files["emulator/src/core/libraries/network/sh_nat_probe_v91.hpp"]=(
        metrics_dir/"sh_nat_probe_v91.hpp").read_bytes()
    meta["applied"].append("V91 native CNG/OpenSSL signed NAT probe source, still UNWIRED from game UDP socket, Direct OFF")
    # V91 server and native recipient must use exact same purpose-isolated
    # READY HMAC header. Server checks two TLS receipts; this is *only*
    # possession of pair master, never proof of completed UDP/GameLink.
    ready_header=(metrics_dir/"sh_pair_ready_v91.hpp").read_bytes()
    files["server/src/sh_pair_ready_v91.hpp"]=ready_header
    files["emulator/src/core/libraries/network/sh_pair_ready_v91.hpp"]=ready_header
    files["emulator/src/core/libraries/network/sh_native_tls_local_client_v91.hpp"]=(
        metrics_dir/"sh_native_tls_local_client_v91.hpp").read_bytes()
    # Stage the revised KDF on BOTH platforms; both need ReadyProof=3.
    kdf_header=(metrics_dir/"sh_pair_key_schedule_v89.hpp").read_bytes()
    files["server/src/sh_pair_key_schedule_v89.hpp"]=kdf_header
    files["emulator/src/core/libraries/network/sh_pair_key_schedule_v89.hpp"]=kdf_header
    meta["applied"].append("V91 original Qt TLS client READY HMAC requires both recipients, native V91 proof; all Direct game routes OFF")
    # V92: native ORIGINALLY bound host_socket probes. This is under the
    # existing SHYT_ENABLE_TEST_LOCAL_MTLS default-OFF build opt-in. It
    # sends only HMAC-SHA256 SHN1 control probes, NEVER game payload,
    # and never creates a new socket or touches GameLink ACK routing.
    v92_file=metrics_dir/"patch_native_same_socket_probe_v92.py"
    v92=types.ModuleType("sh_v92_native_original_socket")
    v92.__file__=str(v92_file)
    exec(compile(v92_file.read_text("utf-8"),str(v92_file),"exec"),v92.__dict__)
    files[v92.NETWORK]=v92.patch_game(files[v92.NETWORK].decode("utf-8")).encode("utf-8")
    meta["applied"].append("V92-V93 original UDP host_socket SHN1 probe dev-only; worker-local V91 TLS grant verification and short game-owned inbox handoff, relay unchanged")
    # V94: backport real upstream Yharnam Together PR365 pre-auth
    # 2GB blob-size parser crash fix. Original pinned source still has
    # the cast to int; this changes only the unsafe bounds checks.
    v94_path=metrics_dir/"patch_upstream_stream_bounds_v94.py"
    v94=types.ModuleType("sh_v94_upstream_parser_bounds")
    v94.__file__=str(v94_path)
    exec(compile(v94_path.read_text("utf-8"),str(v94_path),"exec"),v94.__dict__)
    files[v94.SERVER]=v94.patch_header(files[v94.SERVER].decode("utf-8")).encode("utf-8")
    meta["applied"].append("V94 upstream PR365 shadNet pre-auth 2GB blob signed-overflow bounds fix, default enabled")
    # V97 upstream Kaniel PR407: Doll talk/menu flag 6700 must remain
    # PER PLAYER; stale host-world flag makes every guest unable to level
    # up. Only scrub at party map loads, never during live Doll dialogue.
    v97_path=metrics_dir/"patch_upstream_doll_flag_v97.py"
    v97=types.ModuleType("sh_v97_doll_per_player")
    v97.__file__=str(v97_path)
    exec(compile(v97_path.read_text("utf-8"),str(v97_path),"exec"),v97.__dict__)
    files.update(v97.patch(files))
    meta["applied"].append("V97 upstream PR407 Doll level-up flag 6700 per-player and stale-on-map-load clearing, solo unaffected")
    meta["sha256"]={k:sha(v) for k,v in sorted(files.items())}
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
