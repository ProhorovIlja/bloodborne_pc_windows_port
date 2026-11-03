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

def parse_switch(text:str, cls:str)->dict[str,set[int]]:
    """Single-pass scanner: source comments/whitespace cannot induce regex backtracking."""
    if cls=="yt":
        targets={"SameMap":"SameMap","Ours":"Ours","Drop":"Drop"}
        marker="return ChannelPolicy::"
    else:
        targets={"SAME_MAP":"SameMap","OURS":"Ours","DROP":"Drop"}
        marker="return SHYT_YT_CHANNEL_"
    mapping={"SameMap":set(),"Ours":set(),"Drop":set()}
    pending:list[int]=[]
    for line in text.splitlines():
        # The original C++ uses one case per line; C shim has several.
        pending.extend(int(t,16) for t in CASE.findall(line))
        if marker not in line:
            continue
        for tag,bucket in targets.items():
            suffix=("" if cls=="yt" else "_V21")
            if marker+tag+suffix+";" in line:
                if not pending:
                    raise ValueError("channel cases missing before return")
                mapping[bucket].update(pending)
                pending=[]
                break
    if pending:
        raise ValueError("unmapped YT native channel cases")
    return mapping

def groups(original:str,header:str):
    if "constexpr u32 NativeChannelCount = 0x44;" not in original:
        raise ValueError("native channel range drift")
    start=original.index("constexpr ChannelPolicy NativeChannelPolicy(u32 channel)")
    stop=original.index("constexpr std::string_view ChannelPolicyName(",start)
    source=original[start:stop]
    begin=header.index("switch(channel) {",header.index("shyt_yt_channel_policy_v21(uint32_t channel)"))
    derived=header[begin:header.index("default:",begin)]
    yt=parse_switch(source,"yt")
    ours=parse_switch(derived,"c")
    if yt!=ours:
        raise ValueError("BBHost and original YT native channel tables differ")
    every=[n for group in yt.values() for n in group]
    if len(every)!=len(set(every)) or any(c>=CHANNELS for c in every):
        raise ValueError("invalid duplicate or out-of-range channel")
    if ("default:" not in source or "return ChannelPolicy::Pass;" not in source or
        "default:" not in header[begin:] or
        "return SHYT_YT_CHANNEL_PASS_V21;" not in header[begin:]):
        raise ValueError("unrecognized original native channel default")
    if ("if(channel>=SHYT_YT_NATIVE_CHANNEL_COUNT_V21)" not in header or
        "return SHYT_YT_CHANNEL_DROP_V21;" not in header):
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
