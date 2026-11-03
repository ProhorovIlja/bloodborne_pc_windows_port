#!/usr/bin/env python3
"""V202 strict, private-only generated-C guest-runtime dependency audit.

Audit the real pinned broad bbrecomp's recomp.c + recomp_XXXXX.c shards.
All data stays in a PRIVATE directory; only safe aggregate counts on stdout.

This does NOT prove that the game will boot, that all guest ABI has been
removed, or that native Windows graphics/OS services are implemented.
A native-only build MUST refuse generated fallback calls to interpreter
or legacy PS4-shaped runtime, even in cold paths, unless those paths are
actually removed or replaced in the original offline generator. Do not
mistake a synthetic native executable for a standalone retail game.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys

VALID = re.compile(r"recomp(?:_[0-9a-fA-F]{5})?\.c\Z")
CALLBACK = re.compile(r"\brc\s*->\s*(step|call|tail|bail|trace)\s*\(")
ALL_CALLS = ("step","call","tail","bail","trace")
MAX_ONE = 64 * 1024 * 1024
MAX_TOTAL = 4 * 1024 * 1024 * 1024

def executable_tokens(source: str) -> str:
    """Preserve C program text, blank every literal/comment, keep line breaks.

    A bounded linear scanner rather than regexp comment stripping, since
    quoted '/*' and escaped quotes must not become false code or hide calls.
    """
    out = list(source)
    mode = "code"
    i, n = 0, len(source)
    while i < n:
        c = source[i]
        d = source[i+1] if i+1 < n else ""
        if mode == "code":
            if c == "/" and d == "/":
                mode = "line"
                out[i:i+2] = [" "," "]
                i += 2
                continue
            if c == "/" and d == "*":
                mode = "block"
                out[i:i+2] = [" "," "]
                i += 2
                continue
            if c == '"' or c == "'":
                mode = "string" if c=='"' else "char"
                out[i]=" "
                i+=1
                continue
        elif mode == "line":
            if c == "\n":
                mode = "code"
            else:
                out[i] = " "
            i += 1
            continue
        elif mode == "block":
            if c=="*" and d=="/":
                out[i:i+2] = [" "," "]
                mode="code"
                i+=2
                continue
            if c!="\n":
                out[i]=" "
            i+=1
            continue
        else:
            if c=="\\" and d:
                out[i]=" "
                if d!="\n":
                    out[i+1]=" "
                i+=2
                continue
            if c == ('"' if mode=="string" else "'"):
                mode="code"
            if c!="\n":
                out[i]=" "
            i+=1
            continue
        i+=1
    if mode in ("block","string","char"):
        raise ValueError("malformed generated C literal or unterminated comment")
    return "".join(out)

def sources(folder:Path)->list[Path]:
    if not folder.is_dir() or folder.is_symlink():
        raise ValueError("generated-C folder missing or unsafe")
    entries = sorted(folder.glob("recomp*.c"))
    if len(entries)<2 or not (folder/"recomp.c").is_file():
        raise ValueError("no full original bbrecomp C table and shards")
    if any(not VALID.fullmatch(x.name) or x.is_symlink() or
           not x.is_file() or x.stat().st_size>MAX_ONE for x in entries):
        raise ValueError("untrusted generated-C filename or size")
    if sum(x.stat().st_size for x in entries)>MAX_TOTAL:
        raise ValueError("generated-C source set exceeds audit bound")
    return entries

def audit(folder:Path)->dict:
    files=sources(folder)
    totals=dict.fromkeys(ALL_CALLS,0)
    counts_with_fallback=0
    for path in files:
        token=executable_tokens(path.read_text(encoding="utf-8"))
        found=CALLBACK.findall(token)
        if found:counts_with_fallback+=1
        for kind in found:
            totals[kind]+=1
    return {
        "format":"shyt-native-runtime-gate-v202",
        "generated_c_files":len(files),
        "files_with_callbacks":counts_with_fallback,
        "callback_invocations":totals,
        "callback_total":sum(totals.values()),
        "strict_native_runtime_ready":not any(totals.values()),
        "actual_game_boot_proven":False,
        "no_private_source_details_emitted":True
    }

def selftest()->None:
    c=r'''/* rc->call(c, 2, 3); */
char *a="rc->bail(x)";
char q='x';
// rc->tail(z);
void f(void) { rc -> call(c, x, y); rc->step(c);
  rc->trace(x, y, z); rc->bail(c, t); rc->tail(c);
}'''
    found=CALLBACK.findall(executable_tokens(c))
    if found!=["call","step","trace","bail","tail"]:
        raise AssertionError(("unexpected lexical runtime call classification",found))
    c2=r'''/* "q" */ const char*s="escaped \" rc->step(c)";
void f(void) { const char *p="/* rc->call(c) */"; }
'''
    if CALLBACK.findall(executable_tokens(c2)):
        raise AssertionError("false callback in string/comment")
    print("SHYT_NATIVE_V202_C_LEXICAL_CALLBACK_AUDITOR_SELFTEST_PASS")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--generated-dir",type=Path)
    p.add_argument("--strict",action="store_true")
    p.add_argument("--self-test",action="store_true")
    args=p.parse_args()
    try:
        if args.self_test:
            selftest()
        else:
            if args.generated_dir is None:p.error("--generated-dir required")
            result=audit(args.generated_dir)
            print("SHYT_NATIVE_V202_GENERATED_C_RUNTIME_DEPENDENCY_REPORT")
            print(json.dumps(result,sort_keys=True))
            if args.strict and not result["strict_native_runtime_ready"]:
                # No excerpts, filenames, addresses, or game bytes in logs.
                print("SHYT_NATIVE_V202_STRICT_WIN64_NO_GUEST_RUNTIME_REJECTED",
                      file=sys.stderr)
                raise SystemExit(3)
            if args.strict:print("SHYT_NATIVE_V202_STRICT_NO_RUNTIME_PASS")
    except (ValueError,OSError,UnicodeError) as e:
        print("V202 audit error: "+str(e)[:180],file=sys.stderr)
        raise SystemExit(2)
