#!/usr/bin/env python3
"""V198: incremental, private-only Windows AMD64 COFF builder for full bbrecomp.

Compiles *actual original-generator* recomp.c and recomp_<window>.c C files
into native Windows .obj modules. Handles hundreds of shards, bounded memory
and resumable object cache; no interpreter, game ELF, loader or eboot at game
runtime. Game-generated C and objects MUST be kept PRIVATE and OFF-GitHub.

No copyrighted game-derived code is produced by this script itself. The CI
uses invented ELF/functions produced by V197. An actual Bloodborne game host,
imports, renderer, audio, threads and save system are NOT included here.
"""
from __future__ import annotations
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

UPSTREAM="8f31ec7c41f252730c6325d52647046baef7549f"
FORMAT=1
CFLAGS=("/nologo","/std:c11","/O2","/W0","/c")
MAX_WORKERS=8
MAX_FILE_BYTES=64*1024*1024

def digest(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for piece in iter(lambda:f.read(1<<20),b""):
            h.update(piece)
    return h.hexdigest()

def is_inside(path:Path,parent:Path)->bool:
    try:path.relative_to(parent);return True
    except ValueError:return False

def read_json(path:Path)->dict:
    try:return json.loads(path.read_text(encoding="utf-8"))
    except (OSError,ValueError):return {}

def validate(root:Path,generated:Path,objects:Path,host:Path|None)->list[Path]:
    if not root.is_dir() or not (root/"src/recomp/rc.h").is_file():
        raise ValueError("public source-pinned bbrecomp header missing")
    git=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],
                                text=True,stderr=subprocess.DEVNULL).strip()
    if git!=UPSTREAM:
        raise ValueError("bbrecomp original upstream HEAD changed")
    if "SHYT_NATIVE_V195_WIN32_MONOTONIC_GUEST_TSC" not in (
        root/"src/recomp/rc.h").read_text(encoding="utf-8"
    ):
        raise ValueError("native Windows upstream rc.h adaptation missing")
    if generated.is_symlink() or objects.is_symlink() or not generated.is_dir():
        raise ValueError("invalid private generated C or COFF working directories")
    if generated==objects or is_inside(objects,generated) or is_inside(generated,objects):
        raise ValueError("generated C and compiled COFF cache must be separate")
    if not (root/"deps/include/Zydis/Zydis.h").is_file():
        raise ValueError("real pinned Zydis headers missing")
    sources=sorted(generated.glob("recomp*.c"))
    if not sources or sources[0].name!="recomp.c" or len(sources)<2:
        raise ValueError("original full bbrecomp function table/shards missing")
    for source in sources:
        if (source.is_symlink() or not source.is_file() or
            not source.name.replace("_","").replace(".","").isalnum() or
            source.stat().st_size>MAX_FILE_BYTES):
            raise ValueError("invalid bbrecomp-generated C shard or unexpected size")
    if host is not None and (not host.is_file() or host.is_symlink()):
        raise ValueError("native test entry source invalid")
    # Block game-derived C/.obj in public repos, the most important privacy
    # boundary. Source code for this builder itself may live in our GitHub.
    for location in (generated,objects):
        for parent in (location,*location.parents):
            if (parent/".git").exists():
                raise ValueError("private generated game code/COFF cannot live in Git")
    return sources

def check_coff(path:Path)->None:
    # Standard x86-64 COFF: Machine=0x8664. Archive/object formats with other
    # machine types cannot satisfy the build's native Windows ABI guarantee.
    with path.open("rb") as f:
        if f.read(2)!=b"\x64\x86":
            raise ValueError("compiler did not emit native AMD64 COFF object")

def build(root:Path,generated:Path,objects:Path,host:Path|None,jobs:int,
          exe:Path|None)->dict:
    root=root.resolve(strict=True)
    generated=generated.resolve(strict=True)
    objects=objects.absolute()
    if not 1<=jobs<=MAX_WORKERS:raise ValueError("workers must be 1..8")
    sources=validate(root,generated,objects,host)
    if exe is not None and host is None:
        raise ValueError("linking a runnable host requires its explicit native C entry source")
    if exe is not None and (exe.exists() or exe.suffix.lower()!=".exe" or
                            exe.is_symlink() or not exe.parent.is_dir()):
        raise ValueError("new private native Win64 EXE output required")
    compiler=shutil.which("clang-cl")
    if not compiler:raise ValueError("clang-cl (LLVM Windows target) is required")
    version=subprocess.check_output([compiler,"--version"],text=True,
                                    stderr=subprocess.DEVNULL,timeout=15).splitlines()[0]
    include=(root/"src",root/"deps/include")
    flags=[*CFLAGS,*("/I"+str(p.resolve()) for p in include)]
    salt="\n".join((version,*flags,UPSTREAM,
                    digest(root/"src/recomp/rc.h"),
                    digest(root/"src/cpu/cpu_internal.h"),
                    digest(root/"deps/include/Zydis/Zydis.h")))
    objects.mkdir(parents=True,exist_ok=True)
    if objects.is_symlink():
        raise ValueError("refusing symlink COFF cache")
    expected={}
    for source in sources:
        blob=hashlib.sha256((salt+"\n"+digest(source)).encode()).hexdigest()
        expected[source.name]=blob
    stamp=objects/"native-coff-v198.json"
    previous=read_json(stamp).get("fingerprints",{})
    tasks=[]
    for source in sources:
        target=objects/(source.name+".obj")
        if previous.get(source.name)==expected[source.name] and target.is_file():
            check_coff(target)
        else:
            tasks.append((source,target))
    def compile_one(task:tuple[Path,Path])->str:
        src,dest=task
        partial=objects/(dest.name+".partial")
        partial.unlink(missing_ok=True)
        cmd=[compiler,*flags,"/Fo"+str(partial),str(src)]
        p=subprocess.run(cmd,capture_output=True,timeout=900)
        if p.returncode:
            partial.unlink(missing_ok=True)
            # Never print compiler diagnostics: these may quote proprietary
            # game code. The source label is generic and contains no bytes.
            raise RuntimeError("native AMD64 compilation failed for "+src.name)
        check_coff(partial)
        os.replace(partial,dest)
        return src.name
    with concurrent.futures.ThreadPoolExecutor(max_workers=jobs) as pool:
        results=list(pool.map(compile_one,tasks))
    manifest={
        "format":FORMAT,"upstream":UPSTREAM,"target":"windows-amd64-coff",
        "compiler":version,"source_count":len(sources),
        "fingerprints":expected,
        "objects":{source.name:digest(objects/(source.name+".obj")) for source in sources},
    }
    temporary=objects/"native-coff-v198.json.partial"
    temporary.write_text(json.dumps(manifest,sort_keys=True,indent=2)+"\n",
                         encoding="utf-8")
    os.replace(temporary,stamp)
    result={"source_count":len(sources),"compiled":len(results),
            "reused":len(sources)-len(results),
            "native_amd64_coff":True,"game_boot_proven":False}
    if exe is not None:
        host_object=objects/"v198-host.obj"
        hrun=subprocess.run([compiler,*flags,"/Fo"+str(host_object),
                             str(host.resolve(strict=True))],
                            capture_output=True,timeout=90)
        if hrun.returncode:
            raise RuntimeError("native host entry compile failed")
        check_coff(host_object)
        link=[compiler,"/nologo",str(host_object),
              *(str(objects/(s.name+".obj")) for s in sources),
              "/Fe"+str(exe),"/link","kernel32.lib"]
        linked=subprocess.run(link,capture_output=True,timeout=120)
        if linked.returncode:
            raise RuntimeError("compiled original AOT modules failed Win64 PE link")
        if exe.read_bytes()[:2]!=b"MZ":
            raise RuntimeError("output is not a real Windows PE executable")
        result["native_pe_exe_built"]=True
    return result

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--upstream-checkout",type=Path,required=True)
    a.add_argument("--generated-dir",type=Path,required=True)
    a.add_argument("--objects-dir",type=Path,required=True)
    a.add_argument("--jobs",type=int,default=2)
    a.add_argument("--synthetic-test-host",type=Path)
    a.add_argument("--synthetic-exe",type=Path)
    args=a.parse_args()
    try:
        result=build(args.upstream_checkout,args.generated_dir,args.objects_dir,
                     args.synthetic_test_host,args.jobs,args.synthetic_exe)
    except (ValueError,RuntimeError,OSError,subprocess.CalledProcessError) as e:
        print(str(e)[:270],file=sys.stderr)
        raise SystemExit(2)
    print("SHYT_NATIVE_V198_PRIVATE_INCREMENTAL_WIN64_COFF_BUILD_PASS")
    print(json.dumps(result,sort_keys=True))
