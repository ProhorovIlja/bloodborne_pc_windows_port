#!/usr/bin/env python3
"""V201: source-locked original full bbrecomp indirect x86 JMP -> native AOT.

Upstream emits dn=t; goto L_dispatch for all register/slot jumps. For an
external destination that is already fully recompiled, native C can jump
directly into its RcFunction.fn. Preserve original local-label dispatch
for internal targets and retain explicit RcApi.tail/bail for unknown
function bodies / unusual stack layouts. This remains a stepping stone:
no PS4 runtime is permitted in the FINAL game.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import subprocess
import patch_upstream_indirect_call_v200 as v200
import patch_upstream_ret_flags_v199 as v199

UPSTREAM=v200.UPSTREAM
SOURCE=v200.PATH
BLOB=v200.BLOB
MARK="SHYT_NATIVE_V201_INDIRECT_JMP_NATIVE_DISPATCH"
ORIGINAL='emit("{ dn = %s; goto L_dispatch; }\\n", b.s);'
NATIVE='''/* SHYT_NATIVE_V201_INDIRECT_JMP_NATIVE_DISPATCH: local labels first,
         * then direct AOT tail jump only for precisely known entrypoints. */
        emit("{ const uint64_t t = %s; "
             "if (t >= B + 0x%" PRIx64 "ull && t < B + 0x%" PRIx64 "ull) "
             "{ dn = t; goto L_dispatch; } "
             SPILL " " FLAGS_OUT " c->rip = t; "
             "if (r[RSP] == entry_rsp) { RcFn direct = rc_native_find(t); "
             "if (direct) direct(c); else rc->tail(c); } "
             "else rc->bail(c, entry_rsp); return; }\\n",
             b.s, f.start, f.end);'''

def source_blob(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def apply(root:Path)->None:
    root=root.resolve(strict=True)
    head=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],
                                 stderr=subprocess.DEVNULL,text=True).strip()
    if head!=UPSTREAM:raise ValueError("original generator source version changed")
    original=subprocess.check_output(["git","-C",str(root),"show","HEAD:"+SOURCE])
    if source_blob(original)!=BLOB:
        raise ValueError("original upstream bbrecomp blob changed")
    path=root/SOURCE
    if not path.is_file() or path.is_symlink():
        raise ValueError("untrusted temporary generator path")
    expected=original.decode("utf-8")
    for before,after in ((v199.OLD,v199.NEW),
                         (v200.CALL_OLD,v200.CALL_NEW),
                         (v200.HEADER_OLD,v200.HEADER_NEW),
                         (v200.TABLE_OLD,v200.TABLE_NEW)):
        if expected.count(before)!=1:
            raise ValueError("expected exact V199/V200 pinned original source anchor")
        expected=expected.replace(before,after,1)
    if path.read_text(encoding="utf-8")!=expected:
        raise ValueError("unrecognized generator changes beyond verified V199/V200")
    if expected.count(ORIGINAL)!=1 or MARK in expected:
        raise ValueError("upstream indirect jump entry path changed")
    patch=expected.replace(ORIGINAL,NATIVE,1)
    if patch.count(MARK)!=1 or patch.count("rc_native_find(t)")!=2:
        raise ValueError("unexpected native JMP/CALL source substitution")
    path.write_text(patch,encoding="utf-8")
    subprocess.run(["git","-C",str(root),"diff","--check"],check=True,
                   stdout=subprocess.DEVNULL)
    print("SHYT_NATIVE_V201_SOURCE_PINNED_INDIRECT_JMP_AOT_DISPATCH_PASS")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout",type=Path,required=True)
    a=p.parse_args()
    apply(a.upstream_checkout)
