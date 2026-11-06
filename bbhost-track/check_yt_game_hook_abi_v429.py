#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""V429: original YT/BBHost exact-source ABI parity gate, no EBOOT.
A repo update to either caller or hook dispatcher must fail closed.
Never enable gameplay packet capture or guest memory writes in this tool.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

YT_BLOB="5e698a5bcd714f41ab40782a0838d63055d84d62"
BBHOST_BLOB="b6c31dd2a263429b20a920f90e414ef5b82eb862"

def check(repo:Path,path:str,expected_blob:str)->str:
    if repo.is_symlink() or not repo.is_dir():
        raise ValueError("expected checked-out repository")
    blob=subprocess.check_output(
        ["git","-C",str(repo),"rev-parse",f"HEAD:{path}"],
        text=True,timeout=10).strip()
    if blob!=expected_blob:
        raise ValueError("source Git object changed: "+path)
    file=repo/path
    if not file.is_file() or file.is_symlink() or file.stat().st_size>220000:
        raise ValueError("source unavailable or unexpectedly large")
    return file.read_text(encoding="utf-8")

def must(source:str,tokens:tuple[str,...],name:str)->None:
    if any(token not in source for token in tokens):
        raise ValueError("source ABI drift: "+name)

def main(yt:Path,bbhost:Path,probe:Path,plugin:Path)->None:
    upstream=check(yt,"emulator/src/core/bloodborne_patches.cpp",YT_BLOB)
    host=check(bbhost,"src/host/plugins.cpp",BBHOST_BLOB)
    for path in (probe,plugin):
        if not path.is_file() or path.is_symlink() or path.stat().st_size>90000:
            raise ValueError("missing or untrusted V429 plugin source")
    c=probe.read_text(encoding="utf-8")
    p=plugin.read_text(encoding="utf-8")
    must(upstream,(
        "bool PS4_SYSV_ABI TakeGamePacket",
        "const u64 packet = registers->rcx;",
        "const u32 size = static_cast<u32>(registers->r8);",
        "OnlineIdOfMember(registers->rdx)",
        "static_cast<u32>(registers->rsi) != 0",
        "void PS4_SYSV_ABI DeliverAtNetSyncUpdate",
        "net_sync_updated_ms.store",
    ),"original YT send/update handler")
    must(host,(
        "GUEST_ABI std::int64_t hook_dispatch",
        "for (int i = 0; i < 6; ++i) c.arg[i] = regs[5 - i];",
        "const int skip = h.fn2(&c, h.user);",
        "if (skip) regs[-1] = c.ret;",
        "return skip ? 1 : 0;",
        "int api_hook2(",
        "engine_prologue_hook(g_image, at, have, n",
    ),"BBHost hook2 SysV register bridge")
    must(c,(
        "const uint64_t packet=ctx->arg[3]",
        "const uint64_t member=ctx->arg[2]",
        "const uint32_t reliability=(uint32_t)ctx->arg[1]",
        "const uint32_t size=(uint32_t)ctx->arg[4]",
        "static inline int shyt_yt_v429_observe_send",
        "static inline int shyt_yt_v429_observe_update",
        "return 0;",
    ),"V429 passive BBHost call-site ABI")
    must(p,(
        '#include "shyt_yt_game_link_observer_v429.h"',
        'api->config("shyt_bbhost_probe.observe_yt_game_link_calls")',
        'api->hook2(send,yt_send_prologue_v429,',
        'api->hook2(update,yt_update_prologue_v429,',
        "shyt_yt_full_guest_preflight_v428(",
        "shyt_yt_v429_observe_send",
        "shyt_yt_v429_observe_update",
        '"false", 0, 0, 0}',
    ),"BBHost V429 source-only opt-in")
    for forbidden in ("api->write(","api->patch(","socket(","sendto(",
                      "api->read(","ctx->arg[") :
        # The callback must inspect ctx->arg[] registers, but never
        # dereference them; only these literal operations are forbidden.
        if forbidden=="ctx->arg[":
            continue
        if forbidden in c:
            raise ValueError("V429 observer gained non-passive operation")
    print("SHYT_V429_ORIGINAL_YT_BBHOST_GAME_REGISTERS_AND_PASS_THROUGH_ABI_PASS")

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--yt",type=Path,required=True)
    ap.add_argument("--bbhost",type=Path,required=True)
    ap.add_argument("--observer",type=Path,required=True)
    ap.add_argument("--plugin",type=Path,required=True)
    a=ap.parse_args()
    try:main(a.yt,a.bbhost,a.observer,a.plugin)
    except (ValueError,UnicodeError,OSError,subprocess.CalledProcessError,
            subprocess.TimeoutExpired) as e:
        raise SystemExit("SHYT_V429_ABI_SOURCE_GATE_REFUSED: "+type(e).__name__) from None
