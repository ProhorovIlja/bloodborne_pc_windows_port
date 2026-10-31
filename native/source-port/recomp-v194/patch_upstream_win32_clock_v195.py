#!/usr/bin/env python3
"""V195: port the exact upstream generated-C RDTSC helper to Win32 QPC.

This patches ONLY the public src/recomp/rc.h of a disposable upstream checkout.
No original Bloodborne code, eboot, imports or game-derived functions.
The upstream full-image generator remains pinned: this is a Windows *source*
compatibility step, not proof the complete generated DLL or game boots.
"""
from pathlib import Path
import argparse
import hashlib
import subprocess

UPSTREAM = "8f31ec7c41f252730c6325d52647046baef7549f"
UPSTREAM_RC_BLOB = "a27b8f5fc872c75bd08f6788d716b6856c9e2309"
TARGET = "src/recomp/rc.h"
MARK = "SHYT_NATIVE_V195_WIN32_MONOTONIC_GUEST_TSC"
OLD = """#else
#include <time.h>
static inline uint64_t rc_tsc(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return ((uint64_t)t.tv_sec * 1000000000u + (uint64_t)t.tv_nsec) * 8 / 5;
}
#endif"""
NEW = """#elif defined(_WIN32)
/* SHYT_NATIVE_V195_WIN32_MONOTONIC_GUEST_TSC: native Win32 API, no
 * emulated timer or PS4 kernel. Generated Windows code calls this directly.
 * QueryPerformanceCounter uses a monotonic clock independent of wall time.
 * Scale with integer quotient/remainder to avoid count * 1.6GHz overflow.
 */
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
static inline uint64_t rc_tsc(void) {
    LARGE_INTEGER count, frequency;
    if (!QueryPerformanceFrequency(&frequency) ||
        !QueryPerformanceCounter(&count) || frequency.QuadPart <= 0 ||
        count.QuadPart < 0) return 0;
    const uint64_t ticks = (uint64_t)count.QuadPart;
    const uint64_t hz = (uint64_t)frequency.QuadPart;
    const uint64_t whole = (ticks / hz) * BBCPU_TSC_HZ;
    const uint64_t remainder = ticks % hz;
    /* Typical Windows QPC frequencies are below this bound. Handle higher
     * frequencies without overflowing the partial-second product. */
    const uint64_t fraction =
        hz <= UINT64_MAX / BBCPU_TSC_HZ
        ? (remainder * BBCPU_TSC_HZ) / hz
        : (uint64_t)((long double)remainder * (long double)BBCPU_TSC_HZ /
                     (long double)hz);
    return whole + fraction;
}
#else
#include <time.h>
static inline uint64_t rc_tsc(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return ((uint64_t)t.tv_sec * 1000000000u + (uint64_t)t.tv_nsec) * 8 / 5;
}
#endif"""

def git_blob(content:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(content)).encode()+b"\0"+content).hexdigest()

def transform(source:str)->str:
    if MARK in source or source.count(OLD)!=1:
        raise ValueError("V195 exact upstream RDTSC platform block drift")
    if source.count("#if defined(__aarch64__)")<1 or source.count("BBCPU_TSC_HZ")<1:
        raise ValueError("V195 expected upstream guest-clock implementation absent")
    changed=source.replace(OLD,NEW,1)
    if changed.count(MARK)!=1 or changed.count("clock_gettime(CLOCK_MONOTONIC")!=1:
        raise ValueError("V195 non-Windows upstream clock regression")
    return changed

def stage(root:Path)->None:
    root=root.resolve(strict=True)
    rev=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],
                                text=True,stderr=subprocess.DEVNULL).strip()
    if rev!=UPSTREAM:raise ValueError("V195 upstream checkout pin drift")
    src=root/TARGET
    if src.is_symlink() or not src.is_file():raise ValueError("V195 upstream rc.h unavailable")
    saved=subprocess.check_output(["git","-C",str(root),"show","HEAD:"+TARGET])
    if git_blob(saved)!=UPSTREAM_RC_BLOB or src.read_bytes()!=saved:
        raise ValueError("V195 original upstream header bytes changed")
    data=transform(saved.decode("utf-8"))
    src.write_text(data,encoding="utf-8")
    subprocess.run(["git","-C",str(root),"diff","--check"],check=True,
                   stdout=subprocess.DEVNULL)
    print("SHYT_NATIVE_V195_UPSTREAM_WIN32_QPC_RDTSC_SOURCE_STAGED")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout",type=Path,required=True)
    a=p.parse_args()
    stage(a.upstream_checkout)
