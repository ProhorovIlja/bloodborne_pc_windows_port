#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""V427 pinned, source-only BBHost/official YT 1.4.0 guest-hook preflight.

Does not open an EBOOT, hook a guest, capture packets or contact a server.
Fail on source drift rather than silently reusing unknown game offsets.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

YT_SITES_BLOB="c181487f1b00fde76d7950d3e314204ae703c44a"
EXPECTED={
    "transport send":(0x00C8F0A0,"55 48 89 E5 41 57"),
    "net sync update":(0x01789B60,"55 48 89 E5 41 57"),
}
EBOOT_SHA="941f887a562aae054fac35af8cc8f27cf075f3d4cc2e029fb5ae2a663aaa5ae7"


def safe_read(path:Path,max_size:int)->bytes:
    if not path.is_file() or path.is_symlink() or path.stat().st_size>max_size:
        raise ValueError("missing/untrusted or oversized source-only input")
    return path.read_bytes()


def verify(yt:Path,header:Path,plugin:Path,bbhost_api:Path)->None:
    raw=safe_read(yt,100000)
    digest=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
    if digest!=YT_SITES_BLOB:
        raise ValueError("released YT game patch site blob drift")
    sites=json.loads(raw).get("sites")
    if not isinstance(sites,list):
        raise ValueError("original YT co-op site list missing")
    h=safe_read(header,10000).decode("utf-8")
    p=safe_read(plugin,90000).decode("utf-8")
    api=safe_read(bbhost_api,70000).decode("utf-8")
    for index,(name,(rva,expected)) in enumerate(EXPECTED.items()):
        found=[v for v in sites if v.get("name")==name and
               v.get("feature")=="game packet link" and v.get("kind")=="hook"]
        if len(found)!=1 or int(found[0]["offset"],16)!=rva or (
            bytes.fromhex(found[0]["original"])!=bytes.fromhex(expected)):
            raise ValueError("original YT v1.4.0 guest send/update signature changed")
        macro=("SHYT_V427_TRANSPORT_SEND_RVA" if index==0 else
               "SHYT_V427_NETSYNC_UPDATE_RVA")
        if f"#define {macro} UINT64_C(0x{rva:08X})" not in h:
            raise ValueError("BBHost guest BN/RVA site drift")
    if (f'#define SHYT_V427_EXPECTED_EBOOT_SHA256 "{EBOOT_SHA}"' not in h or
        "SHYT_V427_PREFERRED_IMAGE_BASE UINT64_C(0x400000)" not in h or
        "SHYT_V427_PREFIX_LENGTH=6" not in h or
        "SHYT_V427_HOOK_INSTALL_ALLOWED=0" not in h or
        "return result->sites_matching==SHYT_V427_SITE_COUNT;" not in h):
        raise ValueError("V427 digest, prefix or no-hook policy changed")
    if ("#include \"shyt_yt_guest_hook_preflight_v427.h\"" not in p or
        'api->config("shyt_bbhost_probe.inspect_yt_game_sites")' not in p or
        'shyt_yt_guest_hook_preflight_v427(' not in p or
        '"false", 0, 0, 0}' not in p):
        raise ValueError("V427 plugin opt-in integration missing")
    if ("int (*read)(uint64_t bn_addr, void* out, size_t n);" not in api or
        "int (*eboot_is_109)(void);" not in api or
        "const char* (*eboot_sha256)(void);" not in api or
        "int (*hook2)(" not in api):
        raise ValueError("pinned BBHost API compatibility changed")
    if "api->hook2(" in h or "api->patch(" in h or "api->write(" in h:
        raise ValueError("hook/write is forbidden in V427 preflight")
    print("SHYT_V427_EXACT_YT_140_GAME_NETSYNC_SITES_AND_BBHOST_API_SOURCE_PASS")


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--yt-source",type=Path,required=True)
    ap.add_argument("--header",type=Path,required=True)
    ap.add_argument("--plugin",type=Path,required=True)
    ap.add_argument("--bbhost-api",type=Path,required=True)
    a=ap.parse_args()
    try:
        verify(a.yt_source,a.header,a.plugin,a.bbhost_api)
    except (ValueError,TypeError,KeyError,OSError,UnicodeError,AttributeError) as err:
        raise SystemExit(
            "SHYT_V427_GUEST_HOOK_CONTRACT_REFUSED: "+type(err).__name__) from None
