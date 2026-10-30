#!/usr/bin/env python3
"""V131: backport only merged upstream YT #446 prepareFlip DLC crash guard.

Bloodborne's Old Hunters cutscene could submit a display command buffer
without the expected 64-dword prepareFlip marker. The original patch path
attempts to rewrite an absent PM4 packet and fails/crashes. Official upstream
YT #446 submits work unchanged, then requests the flip on CPU instead.
Source-exact staged original YT1.3 (Protocol8) + immutable upstream PR head.
The authoritative upstream C++ header, test and patch block are copied, not
re-created. No retail game files, saves, server or production changes.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

PIN="0645740a33ae21c56df3b4a0d9777086dbca6053"
UPSTREAM="8d106f40c90ef681adbe025c47cc75d289e0ef7b"
DRIVER="bbport/gpu/shadps4/core/libraries/gnmdriver/gnmdriver.cpp"
CMAKE="bbport/gpu/CMakeLists.txt"
HEADER="bbport/gpu/shim/bbport_flip_marker.h"
TEST="bbport/tests/test_flip_marker.cpp"
ORIGINAL={
    DRIVER:"ff422f48e837968be8a5e5f4ae7e51c2a29a0102",
    CMAKE:"026a0d7d3505b596ad2da37f9d1730726e3a0614",
}
REVIEWED={
    DRIVER:"58fd96eae617894887dc9081ef1417ba48e132c0",
    HEADER:"43c9f42d6398b7fe28273eb276c24fbee236ebd8",
    TEST:"ea99e41063116b1190ec259def484fa6f926c088",
}
BLOCK_START="    // bbport: a flip DCB without its prepareFlip packet stopped the game"
BLOCK_END="    const s32 patch_result ="
ORIGINAL_CALL="""    const s32 patch_result =
        PatchFlipRequest(cmdbuf, size_dw, vo_handle, buf_idx, flip_mode, flip_arg, nullptr /*unk*/);"""
INCLUDES=(
    ("#include \"gnmdriver.h\"","#include <atomic>\n\n#include \"gnmdriver.h\""),
    ("#include \"bbport_gnm_hooks.h\"",
     "#include \"bbport_gnm_hooks.h\"\n#include \"bbport_flip_marker.h\""),
)
CMAKE_BEFORE="""add_executable(flip-label-test EXCLUDE_FROM_ALL ../tests/test_flip_label.cpp)
target_compile_options(flip-label-test PRIVATE -UNDEBUG -Wall -Wextra -Werror)
target_include_directories(flip-label-test PRIVATE shim)
"""
CMAKE_AFTER=CMAKE_BEFORE+"""# Official upstream YT PR #446 original missing prepareFlip C++ regression.
add_executable(flip-marker-test EXCLUDE_FROM_ALL ../tests/test_flip_marker.cpp)
target_compile_options(flip-marker-test PRIVATE -UNDEBUG -Wall -Wextra -Werror)
target_include_directories(flip-marker-test PRIVATE shim)
"""


def exactly(src: str,before: str,after: str,what: str) -> str:
    if src.count(before)!=1:
        raise ValueError("Original source drift or duplicate: "+what)
    return src.replace(before,after,1)


def change(base_driver: str,base_cmake: str,upstream_driver: str,
           upstream_header: str,upstream_test: str)->dict[str,str]:
    if upstream_driver.count(BLOCK_START)!=1 or upstream_driver.count(BLOCK_END)!=1:
        raise ValueError("Reviewed PR446 renderer guard has drifted")
    start=upstream_driver.index(BLOCK_START)
    stop=upstream_driver.index(BLOCK_END,start)
    inserted=upstream_driver[start:stop]
    if ("BbFlipMarker::HasPrepareFlip(cmdbuf, size_dw)" not in inserted or
        "VideoOut::sceVideoOutSubmitFlip(" not in inserted or
        "return result != ORBIS_OK ? result : flip_result;" not in inserted):
        raise ValueError("Reviewed guard missing safe fallback")
    if base_driver.count(BLOCK_START):
        raise ValueError("DLC prepareFlip guard already present")
    for a,b in INCLUDES:
        base_driver=exactly(base_driver,a,b,"include "+a)
    base_driver=exactly(base_driver,ORIGINAL_CALL,inserted+ORIGINAL_CALL,"Gnm submit call")
    base_cmake=exactly(base_cmake,CMAKE_BEFORE,CMAKE_AFTER,"original C++ test target")
    if "inline bool HasPrepareFlip(" not in upstream_header:
        raise ValueError("Missing original marker header")
    if "FindPrepareFlip(nullptr, 300, 256)" not in upstream_test:
        raise ValueError("Missing null/tiny C++ regression")
    return {DRIVER:base_driver,CMAKE:base_cmake,HEADER:upstream_header,TEST:upstream_test}


def git(root:Path,*args:str)->str:
    return subprocess.check_output(["git","-C",str(root),*args],text=True).strip()


def apply(base:Path,reviewed:Path)->None:
    base,reviewed=base.resolve(strict=True),reviewed.resolve(strict=True)
    if base==reviewed or git(base,"rev-parse","HEAD")!=PIN or git(reviewed,"rev-parse","HEAD")!=UPSTREAM:
        raise ValueError("Wrong original pinned YT1.3 or immutable official PR446 checkout")
    for file,blob in ORIGINAL.items():
        if git(base,"rev-parse","HEAD:"+file)!=blob:
            raise ValueError("Original renderer source blob drift: "+file)
    for file,blob in REVIEWED.items():
        if git(reviewed,"rev-parse","HEAD:"+file)!=blob:
            raise ValueError("Reviewed PR446 source blob drift: "+file)
    for path in (HEADER,TEST):
        if (base/path).exists():
            raise ValueError("Unexpected original file already present: "+path)
    changed=change(
        (base/DRIVER).read_text(encoding="utf-8"),
        (base/CMAKE).read_text(encoding="utf-8"),
        (reviewed/DRIVER).read_text(encoding="utf-8"),
        (reviewed/HEADER).read_text(encoding="utf-8"),
        (reviewed/TEST).read_text(encoding="utf-8"))
    for path,body in changed.items():
        target=base/path
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(body.encode("utf-8"))
    subprocess.run(["git","-C",str(base),"diff","--check"],check=True)
    print("SHYT_V131_SOURCE_EXACT_UPSTREAM_446_DLC_PREPAREFLIP_CPU_FALLBACK_STAGED_NOT_GAMEPLAY_PASS")


if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--pinned",type=Path,required=True)
    a.add_argument("--reviewed-pr446",type=Path,required=True)
    z=a.parse_args()
    apply(z.pinned,z.reviewed_pr446)
