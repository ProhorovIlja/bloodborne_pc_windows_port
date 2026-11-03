#!/usr/bin/env python3
"""V200 original bbrecomp: direct AOT dispatch for indirect x86 CALL.

The full-game generator previously forces *every* indirect CALL (register,
vtable, pointer slot) through RcApi.call and its PS4-shaped runtime. This
source-locked adaptation emits a private native binary-search of the ORIGINAL
generated RcFunction table, then invokes registered native RcFn directly.
Unknown targets retain original RcApi.call semantics and are fail-closed by
the separate synthetic no-runtime host. Does NOT solve all indirect JMP,
imports, exceptions, or the full game's engine.

This works ONLY in a disposable checkout with the exact pinned original
upstream code. Neither retail game images nor generated private C are used.
"""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import subprocess

UPSTREAM="8f31ec7c41f252730c6325d52647046baef7549f"
PATH="tools/recomp/bbrecomp.c"
BLOB="f5032c9ead4988579e005af8a0a0ce4ba4ab66d8"
MARK="SHYT_NATIVE_V200_INDIRECT_CALL_NATIVE_DISPATCH"
# This expression is a single physical line of source, with literal escaped
# backslash-n inside its C format. Define it below to avoid text ambiguity.
CALL_OLD='emit("{ const uint64_t t = %s; " SPILL " rc->call(c, t, B + 0x%" PRIx64 "ull); " RELOAD " fk = FK_CPU; }\\n", b.s, next);'
CALL_NEW='''/* SHYT_NATIVE_V200_INDIRECT_CALL_NATIVE_DISPATCH: native AOT table first. */
        emit("{ const uint64_t t = %s; " SPILL " " FLAGS_OUT
             " RcFn direct = rc_native_find(t); "
             "if (direct) { c->r[RSP] -= 8; rc_st(c->r[RSP], 8, B + 0x%" PRIx64
             "ull); c->rip = t; direct(c); } "
             "else rc->call(c, t, B + 0x%" PRIx64 "ull); "
             RELOAD " fk = FK_CPU; }\\n", b.s, next, next);'''
HEADER_OLD='emit("#include \\"recomp/rc.h\\"\\n\\nextern const RcApi *rc;\\n");'
HEADER_NEW='''emit("#include \\"recomp/rc.h\\"\\n\\nextern const RcApi *rc;\\n"
                 "extern RcFn rc_native_find(uint64_t target);\\n");'''
TABLE_OLD='emit("};\\n\\n__attribute__((visibility(\\"default\\"))) const RcFunction *bb_recomp_init(const RcApi *api, size_t *count) {\\n");'
TABLE_NEW='''/* V200: sorted original full-game function table, *EXACT* entrypoints only.
     * O(log n) native dispatch; no fallback interpreter for registered AOT
     * functions. Unknown imports remain RcApi.call for explicit attribution. */
    emit("};\\n\\n"
         "__attribute__((visibility(\\"hidden\\"))) RcFn rc_native_find(uint64_t target) {\\n"
         "    if (!rc || target < rc->image_base) return (RcFn)0;\\n"
         "    const uint64_t off = target - rc->image_base;\\n"
         "    size_t lo = 0, hi = sizeof(table) / sizeof(table[0]);\\n"
         "    while (lo < hi) {\\n"
         "        const size_t mid = lo + (hi - lo) / 2;\\n"
         "        if (table[mid].offset < off) lo = mid + 1;\\n"
         "        else hi = mid;\\n"
         "    }\\n"
         "    if (lo == sizeof(table) / sizeof(table[0]) || table[lo].offset != off) return (RcFn)0;\\n"
         "    return table[lo].direct ? *table[lo].direct : (RcFn)0;\\n"
         "}\\n\\n"
         "__attribute__((visibility(\\"default\\"))) const RcFunction *bb_recomp_init(const RcApi *api, size_t *count) {\\n");'''

def blob(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def patch(root:Path)->None:
    root=root.resolve(strict=True)
    head=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],
                                 text=True,stderr=subprocess.DEVNULL).strip()
    if head!=UPSTREAM:raise ValueError("source revision changed")
    raw=subprocess.check_output(["git","-C",str(root),"show","HEAD:"+PATH])
    if blob(raw)!=BLOB:raise ValueError("original whole-gen blob changed")
    file=root/PATH
    if file.is_symlink() or not file.is_file():raise ValueError("unsafe upstream generator path")
    source=file.read_text(encoding="utf-8")
    base=raw.decode("utf-8")
    # The V199 RET fix may already be applied in the temporary upstream
    # worktree, so accept ONLY that exact known predecessor.
    if source!=base:
        if source.count("SHYT_NATIVE_V199_GUEST_RET_FLAGS_FLUSH")!=1:
            raise ValueError("unrecognized previous upstream modification")
        old_ret='emit("{ const uint64_t t = rc_lds(r[RSP], 8); r[RSP] += %" PRIu64 "; " SPILL " c->rip = t; return; }\\n", pop);'
        if base.count(old_ret)!=1:raise ValueError("prior RET site changed")
        fixed='/* SHYT_NATIVE_V199_GUEST_RET_FLAGS_FLUSH: x86 RET does not clear lazy flags. */\n        emit("{ const uint64_t t = rc_lds(r[RSP], 8); r[RSP] += %" PRIu64 "; " SPILL " " FLAGS_OUT " c->rip = t; return; }\\n", pop);'
        if source != base.replace(old_ret,fixed,1):
            raise ValueError("V199 predecessor was modified beyond pinned EFLAGS fix")
    for old in (CALL_OLD,HEADER_OLD,TABLE_OLD):
        if source.count(old)!=1:
            raise ValueError("exact upstream direct-dispatch source anchor changed: "+old[:45])
    if MARK in source:raise ValueError("V200 already applied")
    source=source.replace(CALL_OLD,CALL_NEW,1)
    source=source.replace(HEADER_OLD,HEADER_NEW,1)
    source=source.replace(TABLE_OLD,TABLE_NEW,1)
    if source.count(MARK)!=1 or source.count("rc_native_find")!=3:
        raise ValueError("unexpected native dispatch patch result")
    file.write_text(source,encoding="utf-8")
    subprocess.run(["git","-C",str(root),"diff","--check"],check=True,
                   stdout=subprocess.DEVNULL)
    print("SHYT_NATIVE_V200_PINNED_ORIGINAL_INDIRECT_CALL_AOT_DISPATCH_PASS")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout",type=Path,required=True)
    args=p.parse_args()
    patch(args.upstream_checkout)
