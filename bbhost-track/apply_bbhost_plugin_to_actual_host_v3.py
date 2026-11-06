#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""V3: build the actual official BBHost executable WITH the Seamless Hunt
read-only plugin and V2 STUN source patch, not a synthetic substitute.

Only a disposable SHA-pinned upstream checkout can be patched. All game
files remain private outside GitHub. This is a BBHost game host, NOT
Yharnam Together game logic yet.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import shutil
import subprocess

UPSTREAM="b0098e04b889e2e70b4af84be1ce809d7af3ff95"
# Released BBHost 0.2.25 is a distinct, explicitly approved upstream source.
# Candidate builds must never silently replace the proven 0.2.24 baseline.
UPSTREAM_V025="7dbe6f60f33fff45ea1bcbf6c6e61a6b35466e13"
BBHOST_CMAKE_BLOBS={
    UPSTREAM:"672a3c1c3b9264cf3cc34d4606b844e5cba87717",
    UPSTREAM_V025:"c881ca32c838eb7a8162c45558cfdac135967f53",
}
BBHOST_PLUGIN_ABI_BLOB="b437a16204a7a439d709054b8fa592034d42f990"
YT_UPSTREAM="5d2305ee611ef1e03be39ff925f0da75c9a70393"
YT_NET_BLOBS={
    "emulator/src/core/libraries/network/net_link.h":"7f56fd1a5215eddb9edd9f13c91b216c16bc1651",
    "emulator/src/common/types.h":"c2b7bd35ea2767287a80b84dc756394c72a7af03"
}
YT_CRYPTO_BLOBS={
    "coop/coop_types.h":"457f7c7126868d81052fb492dea772ffbf6a18b1",
    "coop/game_link.h":"5029581251bfe5decf562c19a10bdd079150cdad",
    "coop/coop_stream.h":"3f488861bd94ab1cdba8a07a9324267bab7a76a8",
    "coop/link_auth.h":"589b823ae0733e9104fcc0140726c8080ade20db",
    "coop/link_crypto.cpp":"b91b3affaca7e2da0a357f1a747a90246b167b79",
    "coop/monocypher/monocypher.c":"fe5bbdc8bde356ae80fe0b136d8c8e9212c15db8",
    "coop/monocypher/monocypher.h":"291b8b9e6f9187e4df715227047c83ee88c95959"
}
CMAKE_BLOB=BBHOST_CMAKE_BLOBS[UPSTREAM]  # retained 0.2.24 baseline constant
CMAKE_ANCHOR="""set_target_properties(bb_plugin_hello PROPERTIES OUTPUT_NAME hello PREFIX ""
  LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/plugins)"""
# BBHost's Windows package-win target has explicit dependencies. Merely
# adding a MODULE target leaves our DLL OUT of the package build graph.
PACKAGE_ANCHOR = ("    DEPENDS bbhost bb_plugin_randomizer bb_plugin_boss_rush "
                  "bb_plugin_mutators bb_plugin_quake bb_plugin_lohit bb_plugin_debug_menu")

CMAKE_APPEND="""
# SHYT V3: build an opt-in, source-only real BBHost plugin beside hello.
# It performs no network injection or game writes and cannot load into
# a host that doesn't expose the exact verified plugin API.
# V401 adds real original YT SHLK4 session crypto as a dormant in-process
# library; sockets, credentials, P2P and game hooks are NOT connected.
add_library(bb_plugin_shyt MODULE
  plugins/shyt_probe/shyt_bbhost_probe_v1.c
  plugins/shyt_probe/shyt_yt_game_frame_v362.c
  plugins/shyt_probe/shyt_yt_shlk_client_v401.cpp
  plugins/shyt_probe/shyt_yt_link_wire_v403.cpp
  plugins/shyt_probe/shyt_yt_secure_game_data_v405.cpp
  plugins/shyt_probe/shyt_yt_udp_endpoint_v406.cpp
  plugins/shyt_probe/shyt_yt_server_session_v408.cpp
  plugins/shyt_probe/shyt_yt_signup_work_v409.cpp
  plugins/shyt_probe/yt_original/coop/link_crypto.cpp)
target_include_directories(bb_plugin_shyt PRIVATE
  include plugins/shyt_probe/yt_original
  plugins/shyt_probe/yt_original/emu)
# Match upstream's real C++ Windows plugin runtime packaging. Do not ship
# a custom DLL that secretly depends on a missing MinGW libstdc++ DLL.
if(WIN32)
  target_link_options(bb_plugin_shyt PRIVATE
    -static -static-libgcc -static-libstdc++)
  target_link_libraries(bb_plugin_shyt PRIVATE ws2_32 bcrypt)
else()
  find_package(Threads REQUIRED)
  target_link_libraries(bb_plugin_shyt PRIVATE Threads::Threads)
endif()
set_target_properties(bb_plugin_shyt PROPERTIES
  OUTPUT_NAME shyt_bbhost_probe PREFIX ""
  LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/plugins)
"""

def git(root:Path,*args:str)->str:
    result=subprocess.run(["git","-C",str(root),*args],
        capture_output=True,text=True,timeout=12)
    if result.returncode:raise ValueError("unverified BBHost checkout")
    return result.stdout.strip()

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout",required=True,type=Path)
    p.add_argument("--original-yt-checkout",required=True,type=Path)
    p.add_argument("--mode",choices=("check","apply"),default="check")
    a=p.parse_args()
    root=a.upstream_checkout.resolve(strict=True)
    yt=a.original_yt_checkout.resolve(strict=True)
    if git(yt,"rev-parse","HEAD")!=YT_UPSTREAM:
        raise ValueError("unverified original YT 1.3.1 source")
    for file,expected_blob in YT_CRYPTO_BLOBS.items():
        item=yt/"server"/file
        if (not item.is_file() or item.is_symlink() or
            git(yt,"rev-parse","HEAD:server/"+file)!=expected_blob or
            git(yt,"hash-object","server/"+file)!=expected_blob):
            raise ValueError("original YT crypto source pin drift")
    for file,expected_blob in YT_NET_BLOBS.items():
        item=yt/file
        if (not item.is_file() or item.is_symlink() or
            git(yt,"rev-parse","HEAD:"+file)!=expected_blob or
            git(yt,"hash-object",file)!=expected_blob):
            raise ValueError("original YT outer link source pin drift")
    actual_upstream=git(root,"rev-parse","HEAD")
    expected_cmake_blob=BBHOST_CMAKE_BLOBS.get(actual_upstream)
    if not expected_cmake_blob:
        raise ValueError("unverified BBHost release")
    plugin_abi="include/bbhost_plugin.h"
    if (git(root,"rev-parse","HEAD:"+plugin_abi)!=BBHOST_PLUGIN_ABI_BLOB or
        git(root,"hash-object",plugin_abi)!=BBHOST_PLUGIN_ABI_BLOB):
        raise ValueError("BBHost plugin ABI differs from validated v16")
    cmake=root/"CMakeLists.txt"
    plugin_root=root/"plugins/shyt_probe"
    plugin=plugin_root/"shyt_bbhost_probe_v1.c"
    source=Path(__file__).resolve().parent/"shyt_bbhost_probe_v1.c"
    world_header=Path(__file__).resolve().parent/"yt_world_event_ledger_v4.h"
    yt_policy_header=Path(__file__).resolve().parent/"shyt_yt_native_channel_policy_v21.h"
    yt_routes_header=Path(__file__).resolve().parent/"shyt_yt_packet_routes_v358.h"
    yt_codec_header=Path(__file__).resolve().parent/"shyt_yt_game_frame_v362.h"
    yt_codec_source=Path(__file__).resolve().parent/"shyt_yt_game_frame_v362.c"
    yt_shlk_source=Path(__file__).resolve().parent/"shyt_yt_shlk_client_v401.cpp"
    yt_shlk_header=Path(__file__).resolve().parent/"shyt_yt_shlk_client_v401.h"
    yt_wire_source=Path(__file__).resolve().parent/"shyt_yt_link_wire_v403.cpp"
    yt_wire_header=Path(__file__).resolve().parent/"shyt_yt_link_wire_v403.h"
    yt_secure_source=Path(__file__).resolve().parent/"shyt_yt_secure_game_data_v405.cpp"
    yt_secure_header=Path(__file__).resolve().parent/"shyt_yt_secure_game_data_v405.h"
    yt_udp_source=Path(__file__).resolve().parent/"shyt_yt_udp_endpoint_v406.cpp"
    yt_udp_header=Path(__file__).resolve().parent/"shyt_yt_udp_endpoint_v406.h"
    yt_session_source=Path(__file__).resolve().parent/"shyt_yt_server_session_v408.cpp"
    yt_session_header=Path(__file__).resolve().parent/"shyt_yt_server_session_v408.h"
    yt_coop_transport_header=Path(__file__).resolve().parent/"shyt_yt_coop_transport_v413.h"
    yt_work_source=Path(__file__).resolve().parent/"shyt_yt_signup_work_v409.cpp"
    yt_work_header=Path(__file__).resolve().parent/"shyt_yt_signup_work_v409.h"
    if (cmake.is_symlink() or not cmake.is_file() or
        git(root,"rev-parse","HEAD:CMakeLists.txt")!=expected_cmake_blob or
        git(root,"hash-object","CMakeLists.txt")!=expected_cmake_blob or
        not source.is_file() or source.is_symlink() or
        not world_header.is_file() or world_header.is_symlink() or
        not yt_policy_header.is_file() or yt_policy_header.is_symlink() or
        not yt_routes_header.is_file() or yt_routes_header.is_symlink() or
        not yt_codec_header.is_file() or yt_codec_header.is_symlink() or
        not yt_codec_source.is_file() or yt_codec_source.is_symlink() or
        not yt_shlk_source.is_file() or yt_shlk_source.is_symlink() or
        not yt_shlk_header.is_file() or yt_shlk_header.is_symlink() or
        not yt_wire_source.is_file() or yt_wire_source.is_symlink() or
        not yt_wire_header.is_file() or yt_wire_header.is_symlink() or
        not yt_secure_source.is_file() or yt_secure_source.is_symlink() or
        not yt_secure_header.is_file() or yt_secure_header.is_symlink() or
        not yt_udp_source.is_file() or yt_udp_source.is_symlink() or
        not yt_udp_header.is_file() or yt_udp_header.is_symlink() or
        not yt_session_source.is_file() or yt_session_source.is_symlink() or
        not yt_session_header.is_file() or yt_session_header.is_symlink() or
        not yt_coop_transport_header.is_file() or yt_coop_transport_header.is_symlink() or
        not yt_work_source.is_file() or yt_work_source.is_symlink() or
        not yt_work_header.is_file() or yt_work_header.is_symlink() or
        plugin_root.exists() or plugin_root.is_symlink()):
        raise ValueError("CMake or plugin input not clean and source pinned")
    original=cmake.read_text(encoding="utf-8")
    if original.count(CMAKE_ANCHOR)!=1 or original.count(PACKAGE_ANCHOR)!=1:
        raise ValueError("original BBHost CMake plugin/package anchor drift")
    if a.mode=="apply":
        plugin_root.mkdir()
        shutil.copyfile(source,plugin)
        shutil.copyfile(world_header,plugin_root/world_header.name)
        shutil.copyfile(yt_policy_header,plugin_root/yt_policy_header.name)
        shutil.copyfile(yt_routes_header,plugin_root/yt_routes_header.name)
        shutil.copyfile(yt_codec_header,plugin_root/yt_codec_header.name)
        shutil.copyfile(yt_codec_source,plugin_root/yt_codec_source.name)
        shutil.copyfile(yt_shlk_source,plugin_root/yt_shlk_source.name)
        shutil.copyfile(yt_shlk_header,plugin_root/yt_shlk_header.name)
        shutil.copyfile(yt_wire_source,plugin_root/yt_wire_source.name)
        shutil.copyfile(yt_wire_header,plugin_root/yt_wire_header.name)
        shutil.copyfile(yt_secure_source,plugin_root/yt_secure_source.name)
        shutil.copyfile(yt_secure_header,plugin_root/yt_secure_header.name)
        shutil.copyfile(yt_udp_source,plugin_root/yt_udp_source.name)
        shutil.copyfile(yt_udp_header,plugin_root/yt_udp_header.name)
        shutil.copyfile(yt_session_source,plugin_root/yt_session_source.name)
        shutil.copyfile(yt_session_header,plugin_root/yt_session_header.name)
        shutil.copyfile(yt_coop_transport_header,plugin_root/yt_coop_transport_header.name)
        shutil.copyfile(yt_work_source,plugin_root/yt_work_source.name)
        shutil.copyfile(yt_work_header,plugin_root/yt_work_header.name)
        vendored=plugin_root/"yt_original"/"coop"
        (vendored/"monocypher").mkdir(parents=True)
        for file in YT_CRYPTO_BLOBS:
            original_src=yt/"server"/file
            copy_dest=plugin_root/"yt_original"/file
            shutil.copyfile(original_src,copy_dest)
        emu_root=plugin_root/"yt_original"/"emu"
        for file in YT_NET_BLOBS:
            relative=Path(file).relative_to("emulator/src")
            copy_dest=emu_root/relative
            copy_dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(yt/file,copy_dest)
        updated=original.replace(CMAKE_ANCHOR,CMAKE_ANCHOR+CMAKE_APPEND)
        updated=updated.replace(PACKAGE_ANCHOR,
                                PACKAGE_ANCHOR+" bb_plugin_shyt")
        cmake.write_text(updated,encoding="utf-8")
    print("SHYT_BBHOST_V3_REAL_HOST_PLUGIN_CMAKE_"+("APPLIED" if a.mode=="apply" else "PINNED"))

if __name__=="__main__":
    try:main()
    except (OSError,ValueError,subprocess.TimeoutExpired):
        raise SystemExit("SHYT_BBHOST_V3_REFUSED_UNVERIFIED_HOST_SOURCE") from None
