#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""V2: harden REAL BBHost STUN Binding transaction IDs in a pinned checkout.

BBHost v0.2.24/v0.2.25 uses steady-clock-seeded mt19937_64 for a 96-bit STUN
transaction ID. Replace ONLY that non-cryptographic transaction source with
the operating system CSPRNG; refuse STUN (and relay negotiation) when entropy
is unavailable. This neither authorizes YT game movement nor claims
authenticated peers. Source-locked to the official BBHost release.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import subprocess

PIN="b0098e04b889e2e70b4af84be1ce809d7af3ff95"
PIN_V025="7dbe6f60f33fff45ea1bcbf6c6e61a6b35466e13"
ALLOWED_RELEASE_HEADS=(PIN,PIN_V025)  # explicit source pins only
FILES={
    "src/net/stun.cpp":"d4c950d9ce321ddc01134778b326017b1f282d86",
    "src/hle/net.cpp":"476fd20eb8acf1acbb5ca45cbb4e03af6b6da4a2",
}

def once(data:str,old:str,new:str)->str:
    if data.count(old)!=1:
        raise ValueError("verified BBHost socket seam changed")
    return data.replace(old,new,1)

def patched_stun(data:str)->str:
    data=once(data,"#include <chrono>\n#include <cstring>\n#include <random>\n",
      """#include <cerrno>
#include <cstring>
#if defined(_WIN32)
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#elif defined(__linux__)
#include <sys/random.h>
#endif
""")
    inject="""// V2: STUN transaction IDs must be unpredictable to an off-path sender.
// No time-seeded PRNG, and no weak random fallback. The relay token
// and STUN response remain advisory data, NOT YT peer authorization.
bool fill_system_transaction_entropy(std::uint8_t* dst,std::size_t count) {
#if defined(BBHOST_V2_TEST_ENTROPY_FAIL)
    (void)dst; (void)count;
    return false;
#elif defined(_WIN32)
    HMODULE module=::LoadLibraryW(L"advapi32.dll");
    if (!module) return false;
    using Rng=BOOLEAN (WINAPI*)(void*,ULONG);
    auto* fn=reinterpret_cast<Rng>(::GetProcAddress(module,"SystemFunction036"));
    const bool ok=fn && count<=0xffffffffu &&
                  fn(dst,static_cast<ULONG>(count))!=0;
    ::FreeLibrary(module);
    return ok;
#elif defined(__linux__)
    std::size_t done=0;
    while(done<count) {
        const ssize_t n=::getrandom(dst+done,count-done,0);
        if(n<0 && errno==EINTR)continue;
        if(n<=0)return false;
        done+=static_cast<std::size_t>(n);
    }
    return true;
#else
    (void)dst;(void)count;
    return false;
#endif
}

"""
    data=once(data,"std::uint16_t rd16(const std::uint8_t* p)",
              inject+"std::uint16_t rd16(const std::uint8_t* p)")
    data=once(data,
"""    static thread_local std::mt19937_64 rng(
        static_cast<std::uint64_t>(std::chrono::steady_clock::now().time_since_epoch().count()) ^ 0x5bd1e995u);
    wr32(txid, kCookie);
    for (std::size_t i = 4; i < kTxid; i += 4) wr32(txid + i, static_cast<std::uint32_t>(rng()));
""",
"""    // 96 bits of OS entropy, matching RFC 5389's 12-byte random portion.
    // A zero-length return is fail-closed; the real caller won't send UDP.
    wr32(txid,kCookie);
    if (!fill_system_transaction_entropy(txid+4,kTxid-4)) {
        std::memset(txid,0,kTxid);
        return 0;
    }
""")
    return data

def patched_hle(data:str)->str:
    return once(data,
"""    const std::size_t req_len =
        net::stun::build_binding_request(req, port->stun_txid, relay != nullptr, have_token ? token : nullptr);
    port->stun_pending = true;
""",
"""    const std::size_t req_len =
        net::stun::build_binding_request(req, port->stun_txid, relay != nullptr, have_token ? token : nullptr);
    // V2: if system entropy is unavailable, leave no pending STUN or
    // relay state and never send an uninitialized request over UDP.
    if (req_len == 0) return false;
    port->stun_pending = true;
""")

def git(root:Path,*args:str)->str:
    r=subprocess.run(["git","-C",str(root),*args],capture_output=True,text=True,timeout=15)
    if r.returncode:raise ValueError("git source pin failed")
    return r.stdout.strip()

def main()->None:
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout",type=Path,required=True)
    p.add_argument("--mode",choices=("check","apply"),default="check")
    a=p.parse_args()
    root=a.upstream_checkout.resolve(strict=True)
    if git(root,"rev-parse","HEAD") not in ALLOWED_RELEASE_HEADS:
        raise ValueError("expected official BBHost v0.2.24/v0.2.25 commit")
    patches={}
    for path,expected in FILES.items():
        file=root/path
        if (file.is_symlink() or not file.is_file() or
            git(root,"rev-parse","HEAD:"+path)!=expected or
            git(root,"hash-object",path)!=expected):
            raise ValueError("BBHost source blob changed")
        text=file.read_text(encoding="utf-8")
        patches[file]=patched_stun(text) if path.endswith("stun.cpp") else patched_hle(text)
    if a.mode=="apply":
        for file,changed in patches.items():
            file.write_text(changed,encoding="utf-8")
    print("SHYT_BBHOST_V2_REAL_STUN_OS_ENTROPY_"+("APPLIED" if a.mode=="apply" else "PINNED"))

if __name__=="__main__":
    try:main()
    except (ValueError,OSError,subprocess.TimeoutExpired) as e:
        raise SystemExit("BBHost V2 refused unverified STUN overlay: "+
                         type(e).__name__) from None
