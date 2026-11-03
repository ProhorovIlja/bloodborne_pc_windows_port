#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""V10: stage a custom CI-built BBHost and plugin beside the real YT GUI.

Only a NEW, verified upstream-release V7 CI bundle is accepted. The official
signed baseline supplies DXC/licenses/assets; our modified engine and DLL are
UNSIGNED CI research outputs, never represented as an official signed release.
No original game assets, account tokens, launcher settings or saves accepted.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct

UPSTREAM = "b0098e04b889e2e70b4af84be1ce809d7af3ff95"
FIELDS = {"kind", "upstream_commit", "source_commit", "workflow_run_id",
          "host_sha256", "plugin_sha256"}
KIND = "SHYT_V10_MODIFIED_BBHOST_WINDOWS_CI"
MAX_META = 4096
# RelWithDebInfo full Windows engine binaries may contain large DWARF/COFF
# debug information. The engine is streamed and SHA-pinned, never mmap/read
# in full. Limit remains bounded, far below any unbounded disk extraction.
MAX_CUSTOM_PE = 768 * 1024 * 1024

class ModdedBundleRejected(ValueError):
    pass

def digest(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1<<20), b""):
            h.update(block)
    return h.hexdigest()

def assert_real_pe(path: Path, *, dll: bool) -> None:
    if path.is_symlink() or not path.is_file() or not (1024 < path.stat().st_size <= MAX_CUSTOM_PE):
        raise ModdedBundleRejected("Missing or oversized custom Windows PE input")
    with path.open("rb") as f:
        hdr=f.read(4096)
    if len(hdr)<0x90 or hdr[:2]!=b"MZ":
        raise ModdedBundleRejected("Not a Windows PE image")
    pe=struct.unpack_from("<I",hdr,0x3c)[0]
    if pe<0x40 or pe+26>len(hdr) or hdr[pe:pe+4]!=b"PE\x00\x00":
        raise ModdedBundleRejected("Invalid PE header")
    machine,sections=struct.unpack_from("<HH",hdr,pe+4)
    characteristics=struct.unpack_from("<H",hdr,pe+22)[0]
    magic=struct.unpack_from("<H",hdr,pe+24)[0]
    if machine!=0x8664 or not (1<=sections<=128) or magic!=0x20b or bool(characteristics&0x2000)!=dll:
        raise ModdedBundleRejected("Not the expected x64 EXE/DLL type")

def safe_tree(directory: Path) -> None:
    for base,folders,files in os.walk(directory,followlinks=False):
        for name in folders+files:
            item=Path(base)/name
            if item.is_symlink():
                raise ModdedBundleRejected("Symlinks forbidden in signed baseline")

def stage_modified_v10(launcher: Path, input_dir: Path, expected_source_commit: str) -> None:
    launcher=launcher.absolute()
    input_dir=input_dir.absolute()
    if launcher.is_symlink() or input_dir.is_symlink() or not launcher.is_dir() or not input_dir.is_dir():
        raise ModdedBundleRejected("Unsafe launcher or CI artifact directory")
    if launcher==input_dir or launcher in input_dir.parents or input_dir in launcher.parents:
        raise ModdedBundleRejected("CI artifact must be separate from packaged launcher")
    runtime=launcher/"bbhost"
    marker=runtime/"SHYT-EXPERIMENTAL.txt"
    if runtime.is_symlink() or not runtime.is_dir() or marker.is_symlink() or not marker.is_file():
        raise ModdedBundleRejected("Signed V7 upstream baseline not staged")
    if not (launcher/"BLauncher.exe").is_file():
        raise ModdedBundleRejected("Actual frozen YT Windows GUI required")
    description=marker.read_text(encoding="utf-8")
    if ("Upstream BBHost v0.2.24 verified against its signed release manifest." not in description
        or "SEAMLESS MULTIPLAYER IS NOT INTEGRATED" not in description):
        raise ModdedBundleRejected("Not the exact signed upstream baseline")
    # A new CI package only. Never touch real player saves, accounts or caches.
    if (launcher/"user").exists() or (runtime/"user").exists():
        raise ModdedBundleRejected("Existing user data must never be repackaged")
    if len(expected_source_commit)!=40 or any(c not in "0123456789abcdef" for c in expected_source_commit):
        raise ModdedBundleRejected("Expected source revision must be exact SHA-1")
    metadata_file=input_dir/"shyt-modified-build-v10.json"
    if metadata_file.is_symlink() or not metadata_file.is_file() or metadata_file.stat().st_size>MAX_META:
        raise ModdedBundleRejected("Missing bounded CI build provenance")
    try:
        m=json.loads(metadata_file.read_text(encoding="utf-8"))
    except (OSError,UnicodeError,ValueError) as e:
        raise ModdedBundleRejected("Malformed CI provenance") from e
    if not isinstance(m,dict) or set(m)!=FIELDS or m["kind"]!=KIND or m["upstream_commit"]!=UPSTREAM or m["source_commit"]!=expected_source_commit or type(m["workflow_run_id"]) is not int or m["workflow_run_id"]<=0:
        raise ModdedBundleRejected("Incorrect source or CI provenance")
    host=input_dir/"bbhost.exe"
    plugin=input_dir/"shyt_bbhost_probe.dll"
    assert_real_pe(host,dll=False)
    assert_real_pe(plugin,dll=True)
    if digest(host)!=m["host_sha256"] or digest(plugin)!=m["plugin_sha256"]:
        raise ModdedBundleRejected("Modified binary does not match same-run CI inventory")
    safe_tree(runtime)
    staged=launcher/".bbhost-modified-v10.new"
    backup=launcher/".bbhost-official-v7.old"
    if staged.exists() or staged.is_symlink() or backup.exists() or backup.is_symlink():
        raise ModdedBundleRejected("Unsafe stale installation stage/backup")
    try:
        shutil.copytree(runtime,staged,symlinks=False)
        shutil.copyfile(host,staged/"bbhost.exe")
        plugins=staged/"plugins"
        plugins.mkdir(exist_ok=True)
        destination=plugins/"shyt_bbhost_probe.dll"
        if destination.exists() or destination.is_symlink():
            raise ModdedBundleRejected("Unexpected custom plugin in signed baseline")
        shutil.copyfile(plugin,destination)
        (staged/"SHYT-EXPERIMENTAL.txt").write_text(
            description+
            "\nSHYT V10: bbhost.exe and shyt_bbhost_probe.dll REPLACED with custom\n"
            "GitHub CI-built binaries, SHA-256 verified against the same-run\n"
            "build inventory. THESE TWO FILES ARE NOT SIGNED BY BBHOST.\n"
            "The other files originate from the verified upstream release.\n"
            "This does NOT enable YT seamless co-op on the BBHost engine.\n",
            encoding="utf-8")
        (staged/"SHYT-V10-UNSIGNED-BUILD.json").write_text(
            json.dumps(m,sort_keys=True,indent=2)+"\n",encoding="utf-8")
        assert_real_pe(staged/"bbhost.exe",dll=False)
        assert_real_pe(destination,dll=True)
        if digest(staged/"bbhost.exe")!=m["host_sha256"] or digest(destination)!=m["plugin_sha256"]:
            raise ModdedBundleRejected("Copied CI candidate checksum mismatch")
        runtime.rename(backup)
        try:
            staged.rename(runtime)
        except OSError:
            backup.rename(runtime)
            raise
    finally:
        if staged.exists():
            shutil.rmtree(staged)
        if backup.exists() and runtime.exists():
            shutil.rmtree(backup)
    print("SHYT_V10_YT_GUI_PLUS_MODIFIED_UNSIGNED_BBHOST_CI_ENGINE_ASSEMBLED_NO_GAME_DATA")

def main() -> None:
    p=argparse.ArgumentParser()
    p.add_argument("--launcher-folder",required=True,type=Path)
    p.add_argument("--modified-artifact",required=True,type=Path)
    p.add_argument("--source-commit",required=True)
    args=p.parse_args()
    try:
        stage_modified_v10(args.launcher_folder,args.modified_artifact,args.source_commit)
    except (OSError,ValueError,UnicodeError) as e:
        # Only our own fixed validation errors may be displayed. OS errors
        # can contain local paths, so retain class only for those.
        reason=(str(e)[:160] if isinstance(e,ModdedBundleRejected)
                else type(e).__name__)
        raise SystemExit("SHYT_V10_MODIFIED_ENGINE_PACKAGING_REFUSED: "+reason) from None

if __name__=="__main__":
    main()
