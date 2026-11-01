#!/usr/bin/env python3
"""V203: source-locked original bbrecomp function-fallthrough -> native AOT.

An x86-64 function with no terminal RET/JMP can continue into the next
function. The original normal-mode bbrecomp generator always emits
RcApi.tail(c) for this *generic* exit, even when the immediate successor
has already been compiled into a native RcFunction.

V203 keeps the original in-function and unusual stack (bail) logic,
and dispatches to a registered native function only if the *exact*
new guest RIP is present in the original full RcFunction table. Unknown
addresses keep the explicit RcApi.tail fallback, which V202's strict
native release audit must continue rejecting until genuinely solved.

Only edits a disposable upstream checkout at original pin plus the exact
source-locked V199/V200/V201 modifications. No private game data involved.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import subprocess
import patch_upstream_ret_flags_v199 as v199
import patch_upstream_indirect_call_v200 as v200
import patch_upstream_indirect_jump_v201 as v201

UPSTREAM=v200.UPSTREAM
PATH=v200.PATH
BLOB=v200.BLOB
MARK="SHYT_NATIVE_V203_GENERIC_TAIL_DIRECT_AOT"
OLD='emit("    else rc->tail(c); /* out of the function, the stack as at its entry: a tail call */\\n}\\n");'
NEW='''/* SHYT_NATIVE_V203_GENERIC_TAIL_DIRECT_AOT:
     * Generic normal function fallthrough/tail: exact AOT entry only.
     * Existing rc->tail remains for UNMAPPED control flow and strict
     * no-guest-runtime release mode MUST reject it. */
    emit("    else { RcFn direct = rc_native_find(dn); "
         "if (direct) direct(c); else rc->tail(c); } "
         "/* exact AOT function fallthrough, unknown target still needs runtime */\\n}\\n");'''

def blob(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def reconstruct(base:str)->str:
    substitutions=[
        (v199.OLD,v199.NEW),
        (v200.CALL_OLD,v200.CALL_NEW),
        (v200.HEADER_OLD,v200.HEADER_NEW),
        (v200.TABLE_OLD,v200.TABLE_NEW),
        (v201.ORIGINAL,v201.NATIVE),
    ]
    for old,new in substitutions:
        if base.count(old)!=1:
            raise ValueError("V203 predecessor source anchor changed")
        base=base.replace(old,new,1)
    return base

def patch(root:Path)->None:
    root=root.resolve(strict=True)
    if subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],
                               text=True,stderr=subprocess.DEVNULL).strip()!=UPSTREAM:
        raise ValueError("V203 original generator pin changed")
    raw=subprocess.check_output(["git","-C",str(root),"show","HEAD:"+PATH])
    if blob(raw)!=BLOB:
        raise ValueError("V203 original bbrecomp Git blob changed")
    file=root/PATH
    if file.is_symlink() or not file.is_file():
        raise ValueError("V203 generator source is unsafe")
    expected=reconstruct(raw.decode("utf-8"))
    if file.read_text(encoding="utf-8")!=expected:
        raise ValueError("V203 unknown changes after preceding V201 source patch")
    if expected.count(OLD)!=1 or MARK in expected:
        raise ValueError("V203 original generic tail emission site changed")
    after=expected.replace(OLD,NEW,1)
    if after.count(MARK)!=1:
        raise ValueError("V203 source replacement did not take")
    file.write_text(after,encoding="utf-8")
    subprocess.run(["git","-C",str(root),"diff","--check"],check=True,
                   stdout=subprocess.DEVNULL)
    print("SHYT_NATIVE_V203_PINNED_ORIGINAL_GENERIC_FALLTHROUGH_AOT_PASS")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout",type=Path,required=True)
    patch(p.parse_args().upstream_checkout)
