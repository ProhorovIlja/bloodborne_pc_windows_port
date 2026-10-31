#!/usr/bin/env python3
"""V199 pinned full bbrecomp RET flags correctness for native Windows AOT.

Upstream tools/recomp/bbrecomp.c emits lazy x86 flags (fk, fa, fb, fr, fz)
in local C variables. RET spills general registers but does not commit the
pending flags back to BbCpu. If a caller observes x86 FLAGS after return,
the native AOT execution diverges from the original x86 instructions.

This exact-source patch adds FLAGS_OUT at a genuine RET instruction,
after SPILL and before returning, preserving source x86 semantics.
No original game bytes, proprietary code, PS4 runtime or emulator involved.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import subprocess

UPSTREAM="8f31ec7c41f252730c6325d52647046baef7549f"
SOURCE="tools/recomp/bbrecomp.c"
BLOB="f5032c9ead4988579e005af8a0a0ce4ba4ab66d8"
MARK="SHYT_NATIVE_V199_GUEST_RET_FLAGS_FLUSH"
OLD='emit("{ const uint64_t t = rc_lds(r[RSP], 8); r[RSP] += %" PRIu64 "; " SPILL " c->rip = t; return; }\\n", pop);'
NEW='/* '+MARK+': x86 RET does not clear lazy flags. */\n        emit("{ const uint64_t t = rc_lds(r[RSP], 8); r[RSP] += %" PRIu64 "; " SPILL " " FLAGS_OUT " c->rip = t; return; }\\n", pop);'

def gitblob(b:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def apply(root:Path)->None:
    root=root.resolve(strict=True)
    if subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],
                               text=True,stderr=subprocess.DEVNULL).strip()!=UPSTREAM:
        raise ValueError("V199 original bbrecomp commit drift")
    raw=subprocess.check_output(["git","-C",str(root),"show","HEAD:"+SOURCE])
    if gitblob(raw)!=BLOB:raise ValueError("V199 generator source changed")
    path=root/SOURCE
    if not path.is_file() or path.is_symlink():
        raise ValueError("upstream source not regular file")
    # Works on Linux original LF and checked out Windows CRLF transparently.
    source=path.read_text(encoding="utf-8")
    if source!=raw.decode("utf-8"):
        raise ValueError("generator already modified or source pin invalid")
    if source.count(OLD)!=1 or MARK in source:
        raise ValueError("original generated RET flags expression drift")
    modified=source.replace(OLD,NEW,1)
    if modified.count(MARK)!=1 or (
        modified.count(' SPILL " " FLAGS_OUT " c->rip = t; return;')!=1
    ):
        raise ValueError("RET lazy flag flush patch malformed")
    path.write_text(modified,encoding="utf-8")
    subprocess.run(["git","-C",str(root),"diff","--check"],
                   stdout=subprocess.DEVNULL,check=True)
    print("SHYT_NATIVE_V199_SOURCE_LOCKED_RET_FLAGS_FLUSH_PATCH_PASS")

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--upstream-checkout",required=True,type=Path)
    a=parser.parse_args()
    apply(a.upstream_checkout)
