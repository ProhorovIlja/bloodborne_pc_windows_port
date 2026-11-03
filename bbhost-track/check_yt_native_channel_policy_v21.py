#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V21: fail closed if the copied REAL YT packet channel policy drifts.

Reads only two public source files, not any game packets or retail data.
Verifies the exact pinned original YT 1.3.1 source Git blob and every one
of the 68 native channel classifications. Does NOT grant P2P permission.
"""
import argparse
import hashlib
from pathlib import Path
import re

UPSTREAM_BLOB="f732c87cd0a030751f5ed23dfa225e98bb8ffc5c"
CHANNELS=0x44
TAGS={"SameMap":"SAME_MAP","Ours":"OURS","Drop":"DROP"}
CASE=re.compile(r"\bcase\s+(0x[0-9a-fA-F]+)\s*:")

def pin(blob:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(blob)).encode()+b"\0"+blob).hexdigest()

def read(path:Path,cap:int)->str:
    if not path.is_file() or path.is_symlink() or path.stat().st_size>cap:
        raise ValueError("invalid source-only channel policy input")
    return path.read_text(encoding="utf-8")

def groups(original:str,header:str):
    if "constexpr u32 NativeChannelCount = 0x44;" not in original:
        raise ValueError("native channel range drift")
    start=original.index("constexpr ChannelPolicy NativeChannelPolicy(u32 channel)")
    stop=original.index("constexpr std::string_view ChannelPolicyName(",start)
    source=original[start:stop]
    start=header.index("shyt_yt_channel_policy_v21(uint32_t channel)")
    stop=header.index("#endif",start)
    derived=header[start:stop]
    yt=[]
    for name in TAGS:
        match=re.search(r"((?:\s*case\s+0x[0-9A-Fa-f]+:[^\n]*\n)+)"
                        r"\s*return ChannelPolicy::"+name+r"\s*;",source)
        if not match:
            raise ValueError("original YT channel policy structure drift")
        yt.append({int(x,16) for x in CASE.findall(match.group(1))})
    ours=[]
    for name in TAGS.values():
        match=re.search(r"((?:\s*case\s+0x[0-9A-Fa-f]+:\s*)+)"
                        r"return SHYT_YT_CHANNEL_"+name+r"_V21\s*;",derived)
        if not match:
            raise ValueError("BBHost C policy mapping drift")
        ours.append({int(x,16) for x in CASE.findall(match.group(1))})
    if yt!=ours or sum(len(x) for x in yt)!=len(set.union(*yt)):
        raise ValueError("BBHost and original YT native channel tables differ")
    if any(c>=CHANNELS for group in yt for c in group):
        raise ValueError("unrecognized YT channel outside native range")
    if ("default:" not in source or "return ChannelPolicy::Pass;" not in source or
        "default:" not in derived or "return SHYT_YT_CHANNEL_PASS_V21;" not in derived):
        raise ValueError("unknown original native channel default is not PASS")
    if ("if(channel>=SHYT_YT_NATIVE_CHANNEL_COUNT_V21)" not in derived or
        "return SHYT_YT_CHANNEL_DROP_V21;" not in derived):
        raise ValueError("out-of-range channels must be refused")
    return yt

def main()->None:
    a=argparse.ArgumentParser()
    a.add_argument("--yt-policy",required=True,type=Path)
    a.add_argument("--host-policy",required=True,type=Path)
    args=a.parse_args()
    try:
        original_bytes=args.yt_policy.read_bytes()
        if pin(original_bytes)!=UPSTREAM_BLOB:
            raise ValueError("original YT source version changed")
        groups(read(args.yt_policy,180000),read(args.host_policy,24000))
    except (OSError,ValueError,UnicodeError) as error:
        raise SystemExit("SHYT_V21_REAL_YT_CHANNEL_POLICY_REFUSED: "+type(error).__name__) from None
    print("SHYT_V21_REAL_YT_131_NATIVE_CHANNEL_POLICY_EXACT_MATCH_ALL_68_PASS")
    print("SOURCE CHECK ONLY; no direct P2P or authorized gameplay delivery established.")

if __name__=="__main__":
    main()
