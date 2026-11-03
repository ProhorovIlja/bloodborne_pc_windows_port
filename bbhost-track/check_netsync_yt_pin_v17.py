#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""V17: tie observe-only BBHost NetSync hook to exact ORIGINAL YT 1.3.1 site.

Cross-project verification only. Never reads an EBOOT, injects code or
sends packets. A 6-byte publicly documented game site is not enough to
justify patching a prologue; the plugin has its own strict 17-byte live
instruction-boundary check and defaults OFF.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re

YT_SITE="bbport/patches/coop-sites.json"
EXPECTED_BLOB="c181487f1b00fde76d7950d3e314204ae703c44a"
EXPECTED_SITE=0x017894E0
EXPECTED_BYTES=bytes.fromhex("55 48 89 E5 41 57")
EXPECTED_SLOTS=68
PREF_BASE=0x400000

def verify(site_file:Path,probe_file:Path)->None:
    if any(p.is_symlink() or not p.is_file() or p.stat().st_size>200000 for p in
           (site_file,probe_file)):
        raise ValueError("untrusted source-only hook contract inputs")
    import hashlib
    # This is the exact YT source blob's Git SHA-1, not game-derived bytes.
    raw=site_file.read_bytes()
    blob=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
    if blob!=EXPECTED_BLOB:
        raise ValueError("YT native packet site metadata drift")
    data=json.loads(raw)
    sites=data.get("sites")
    if not isinstance(sites,list):
        raise ValueError("missing real YT packet site list")
    matches=[row for row in sites
             if row.get("name")=="packet send"
             and row.get("feature")=="channel table"
             and row.get("kind")=="hook"]
    if len(matches)!=1:
        raise ValueError("ambiguous original NetSync send site")
    site=matches[0]
    if int(site["offset"],16)!=EXPECTED_SITE or bytes.fromhex(site["original"])!=EXPECTED_BYTES:
        raise ValueError("BBHost hook target differs from exact YT 1.09 site")
    probe=probe_file.read_text(encoding="utf-8")
    head=re.search(r"netsync_prologue_v17\[16\]\s*=\s*\{([^}]+)\}",probe,re.S)
    if not head:
        raise ValueError("BBHost NetSync site prologue missing")
    body=re.sub(r"/\*.*?\*/|//[^\n]*"," ",head.group(1),flags=re.S)
    bytes_in_source=bytes(int(x,16) for x in re.findall(r"0x([0-9A-Fa-f]{2})\b",body))
    if len(bytes_in_source)!=16 or not bytes_in_source.startswith(EXPECTED_BYTES):
        raise ValueError("BBHost plugin prologue not grounded in YT source")
    if ("(UINT64_C(0x017894E0)+UINT64_C(0x400000))" not in probe or
        "#define SHYT_V17_GAME_CHANNELS 68u" not in probe or
        "if (!ctx) return 0;" not in probe):
        raise ValueError("BBHost BN/RVA translation or passive packet ABI changed")
    if "const uint64_t channel=ctx->arg[2]" not in probe or "const uint64_t size=ctx->arg[4]" not in probe:
        raise ValueError("original NetSync channel/size calling convention changed")
    if "return 0; /* NEVER intercept / alter gameplay, only observe */" not in probe:
        raise ValueError("non-intercepting packet observer semantics changed")
    print("SHYT_V17_YT_131_NATIVE_PACKET_SEND_BN_AND_ABI_SOURCE_CONTRACT_PASS")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--yt-source",type=Path,required=True)
    p.add_argument("--probe",type=Path,required=True)
    a=p.parse_args()
    try:
        verify(a.yt_source,a.probe)
    except (ValueError,KeyError,TypeError,OSError,UnicodeError) as e:
        raise SystemExit("SHYT_V17_NETSYNC_SOURCE_CONTRACT_REFUSED: "+type(e).__name__) from None
