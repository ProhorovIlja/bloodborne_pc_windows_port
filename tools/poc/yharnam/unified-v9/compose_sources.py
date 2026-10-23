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
    for path in output:
        if path.startswith("/") or ".." in Path(path).parts:
            raise ValueError("unsafe relative path "+path)
    meta={
        "upstream_pin":PIN,
        "applied":["V3 in-game UI scale","V5 DBNO protocol 8",
                   "V7 native P2P hooks (dormant)","V8 Github update channel",
                   "V10 direct channel guard","V11 optional last-hunt title reconnect"],
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
    required=set(v5.PATCHES)|{NETWORK,COOP,LAUNCHER}
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
