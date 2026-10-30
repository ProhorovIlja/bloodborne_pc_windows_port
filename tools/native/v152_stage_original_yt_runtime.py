#!/usr/bin/env python3
"""Developer-only native YT1.3 Windows input kit from verified original sources.

Stage the ORIGINAL YT Protocol8 run.py/scripts/patches and three previously
compiled ORIGINAL Windows executables. Never include any game data, keys,
accounts, saves, PS4 modules, or private settings. This is a source-provenance
and packaging smoke kit, NOT an independently playable launcher: system/MSYS2
runtime DLLs and a local legal game copy are NOT included. No networking.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

PIN="0645740a33ae21c56df3b4a0d9777086dbca6053"
RUN_BLOB="1880007c0359de018bc61f46bc2a71902afe129b"
BUILD_RUN_ID=41051781140
BUILD_SHA="ebcda70997b483f1a9144c8c92d0fc6339a5eab5"
SCHEMA="SHYT_V152_NATIVE_WINDOWS_DEVELOPER_INPUT_KIT"
EXPECTED_EXES=("bb-probe.exe","bb-play.exe","bb-gpu-capabilities.exe")
REQUIRED_SOURCE=(
    "run.py","LICENSE","packaging/windows/README-Windows.txt",
    "scripts/prepare.py","scripts/link_modules.py",
    "scripts/patches.py","scripts/mods.py","scripts/content_profile.py",
    "scripts/game_check.py",
    "patches/Bloodborne.xml","patches/coop-sites.json",
    "patches/redzone.json",
)
FORBIDDEN_NAMES={
    "eboot.bin","param.sfo","libc.prx","boot-linked.bin","content.bin",
    "save","save.dat","savegame","account.db","secrets.json"
}
ALLOWED_EXT={".py",".json",".xml",".txt",".bin",".exe",".md"}
MAX_SOURCE=3*1024*1024
MAX_PE=160*1024*1024

class StageError(ValueError):
    pass

def git(repo:Path,*args:str)->str:
    return subprocess.check_output(["git","-C",str(repo),*args],
                                   text=True,stderr=subprocess.DEVNULL).strip()

def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as src:
        for buf in iter(lambda:src.read(1024*1024),b""):
            h.update(buf)
    return h.hexdigest()

def blob_sha(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+bytes([0])+raw).hexdigest()

def safe_file(root:Path,relative:Path,limit:int)->Path:
    if relative.is_absolute() or ".." in relative.parts or any(
            part.lower() in ("user","mods","out","dvdroot_ps4","sce_sys","sce_module")
            for part in relative.parts):
        raise StageError("unexpected folder in developer runtime kit")
    p=root/relative
    if not p.is_file() or p.is_symlink() or p.stat().st_size>limit:
        raise StageError("unverified or unsafe runtime source item")
    if p.name.lower() in FORBIDDEN_NAMES:
        raise StageError("forbidden game/account file in developer runtime kit")
    return p

def validate_pe(path:Path)->None:
    if not path.is_file() or path.is_symlink():
        raise StageError("compiled YT Windows executable missing")
    size=path.stat().st_size
    if size<1024 or size>MAX_PE:
        raise StageError("invalid native Windows exe size")
    with path.open("rb") as fp:
        header=fp.read(64)
        if len(header)!=64 or header[:2]!=b"MZ":
            raise StageError("not a Windows PE executable")
        offset=int.from_bytes(header[0x3c:0x40],"little")
        if offset<64 or offset>4096 or offset+4>size:
            raise StageError("invalid PE header offset")
        fp.seek(offset)
        if fp.read(4)!=b"PE\x00\x00":
            raise StageError("invalid PE signature")

def copy_native(src:Path,dst:Path)->None:
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(src,dst)

def gather(original:Path,compiled:Path,dest:Path)->dict:
    original=original.resolve()
    compiled=compiled.resolve()
    dest=dest.resolve(strict=False)
    if not original.is_dir() or not compiled.is_dir():
        raise StageError("original YT source and compiled output directory required")
    if git(original,"rev-parse","HEAD")!=PIN:
        raise StageError("expected pinned ORIGINAL YT1.3 Git revision")
    if git(original,"status","--porcelain","--untracked-files=no"):
        raise StageError("original YT1.3 tracked source was modified")
    port=original/"bbport"
    for raw in REQUIRED_SOURCE:
        safe_file(port,Path(raw),MAX_SOURCE)
    run=safe_file(port,Path("run.py"),MAX_SOURCE)
    if blob_sha(run.read_bytes().replace(b"\r\n",b"\n"))!=RUN_BLOB:
        raise StageError("original YT1.3 Windows launcher Git blob drift")
    if dest.exists():
        raise StageError("never overwrite an existing destination or saves")
    for stem in (original,compiled):
        if stem==dest or stem in dest.parents or dest in stem.parents:
            raise StageError("destination overlaps verified inputs")
    binaries={}
    for executable in EXPECTED_EXES:
        found=[p for p in compiled.rglob(executable) if p.is_file() and not p.is_symlink()]
        if len(found)!=1:
            raise StageError("expected one unambiguous pinned native Windows exe")
        validate_pe(found[0])
        binaries[executable]=found[0]
    staged=dest/"YT-native-dev-kit"
    copied=[]
    try:
        staged.mkdir(parents=True,exist_ok=False)
        for raw in REQUIRED_SOURCE:
            relative=Path(raw)
            target=staged/relative
            copy_native(safe_file(port,relative,MAX_SOURCE),target)
            copied.append(relative.as_posix())
        for item in sorted((port/"scripts").iterdir()):
            if item.is_file() and not item.is_symlink() and (
                    item.suffix.lower()==".py" or item.name=="party_hud_icons.bin"):
                rel=Path("scripts")/item.name
                if rel.as_posix() not in copied:
                    copy_native(safe_file(port,rel,MAX_SOURCE),staged/rel)
                    copied.append(rel.as_posix())
        # Release build used out/*.exe. Original run.py finds executable
        # under bin/ first, as in upstream's own package.sh.
        for name,path in sorted(binaries.items()):
            rel=Path("bin")/name
            copy_native(path,staged/rel)
            copied.append(rel.as_posix())
        # Fail closed if any prohibited private/game file found.
        for file in staged.rglob("*"):
            if file.is_symlink() or (file.is_file() and (
                    file.name.lower() in FORBIDDEN_NAMES or
                    (file.suffix.lower() not in ALLOWED_EXT and file.name!="LICENSE"))):
                raise StageError("unsafe file introduced in staged kit")
        inventory={}
        for rel in sorted(copied):
            path=staged/rel
            inventory[rel]={"sha256":sha256(path),"bytes":path.stat().st_size}
        manifest={
            "schema":SCHEMA,
            "source_original_revision":PIN,
            "native_compiler_run_id":BUILD_RUN_ID,
            "native_compiler_head_sha":BUILD_SHA,
            "source_launcher_git_blob":RUN_BLOB,
            "files":inventory,
            "game_files_included":False,
            "private_settings_or_keys_included":False,
            "runtime_dlls_included":False,
            "bundled_python_included":False,
            "validated_game_boot":False,
            "validated_multiplayer":False,
            "developer_kit_not_public_release":True,
        }
        (staged/"MANIFEST.json").write_text(json.dumps(manifest,sort_keys=True,indent=2)+"\n",
                                           encoding="utf-8")
        (staged/"NOT_A_PUBLIC_RELEASE.txt").write_text(
            "SOURCE-CHECKED YT1.3 NATIVE WINDOWS INPUT KIT.\n"
            "For source/provenance and local smoke tests only. NOT PLAYABLE AS-IS.\n"
            "Python and the native CLANG64 DLL dependency closure are NOT included.\n"
            "Requires your own legal Bloodborne 1.09 data, private local settings,\n"
            "a compatible graphics/runtime environment and an approved online server.\n"
            "Never place proprietary game files, account credentials or saves in CI.\n",
            encoding="utf-8")
        return manifest
    except BaseException:
        if dest.exists():
            shutil.rmtree(dest)
        raise

def zip_kit(dest:Path,output:Path)->None:
    dest=dest.resolve()
    output=output.resolve(strict=False)
    if output.exists() or output==dest or dest in output.parents:
        raise StageError("refuse overwrite/zip inside staging directory")
    if not (dest/"YT-native-dev-kit"/"MANIFEST.json").is_file():
        raise StageError("developer kit has no source manifest")
    with zipfile.ZipFile(output,"x",zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for path in sorted((dest/"YT-native-dev-kit").rglob("*")):
            if path.is_file() and not path.is_symlink():
                archive.write(path,path.relative_to(dest).as_posix())

def main(argv=None)->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original",required=True,type=Path)
    parser.add_argument("--compiled",required=True,type=Path)
    parser.add_argument("--stage",required=True,type=Path)
    parser.add_argument("--zip",type=Path)
    options=parser.parse_args(argv)
    try:
        result=gather(options.original,options.compiled,options.stage)
        if options.zip:
            zip_kit(options.stage,options.zip)
        print("SHYT_V152_ORIGINAL_YT130_NATIVE_DEV_ONLY_INPUT_KIT_NO_GAME_ASSETS",
              len(result["files"]))
        return 0
    except StageError as exc:
        print("V152 staging refused: "+str(exc),file=sys.stderr)
        return 2
    except (OSError,subprocess.CalledProcessError):
        print("V152 staging refused invalid files or Git checkout",file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
