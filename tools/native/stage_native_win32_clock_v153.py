#!/usr/bin/env python3
"""V153 native Win32 clock for pinned YT1.3 game runtime_time.c.

Replace the original Windows gettimeofday/POSIX-CRT relay with native
GetSystemTimePreciseAsFileTime (Windows 10/11). Preserve the original PS4
x86-64 SysV guest call ABI/layout and leave the POSIX/Linux code unchanged.
No real game files and no modification of the existing production build.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import sys

PIN="0645740a33ae21c56df3b4a0d9777086dbca6053"
PATH=Path("bbport/src/runtime_time.c")
BLOB="31f568e90ffa885e2814a2c6d08851befb681a77"

OLD_INCLUDE="#include <sys/time.h>\n"
NEW_INCLUDE="#ifdef _WIN32\n#include <windows.h>\n#else\n#include <sys/time.h>\n#endif\n"

OLD_FN="""static ABI int guest_gettimeofday(GuestTimeval *value,GuestTimezone *zone) {
    struct timeval t;
#ifdef _WIN32
    if (gettimeofday(&t,NULL)) { perror("STOP: host gettimeofday failed"); exit(21); }
    if (zone) { zone->minuteswest=(int32_t)(-compat_utc_offset((time_t)t.tv_sec)/60); zone->dsttime=0; }
#else
    struct timezone z;
    if (gettimeofday(&t,&z)) {
        /* Guest errno/TLS failure path is not implemented yet. */
        perror("STOP: host gettimeofday failed"); exit(21);
    }
    if (zone) { zone->minuteswest=z.tz_minuteswest; zone->dsttime=z.tz_dsttime; }
#endif
    if (value) { value->seconds=t.tv_sec; value->microseconds=t.tv_usec; }
    return 0;
}
"""

NEW_FN="""static ABI int guest_gettimeofday(GuestTimeval *value,GuestTimezone *zone) {
#ifdef _WIN32
    /* V153: Windows-native wall clock (100-ns intervals since 1601 UTC).
     * Neither POSIX gettimeofday nor a console kernel/clock is involved.
     * Preserve the guest timeval layout: int64_t seconds, int64_t usec. */
    FILETIME ft;
    GetSystemTimePreciseAsFileTime(&ft);
    const uint64_t ticks=((uint64_t)ft.dwHighDateTime<<32)|ft.dwLowDateTime;
    const int64_t unix_100ns=(int64_t)ticks-INT64_C(116444736000000000);
    int64_t seconds=unix_100ns/INT64_C(10000000);
    int64_t micros=(unix_100ns%INT64_C(10000000))/10;
    if (micros<0) { --seconds; micros+=1000000; }
    if (value) { value->seconds=seconds; value->microseconds=micros; }
    if (zone) {
        zone->minuteswest=(int32_t)(-compat_utc_offset((time_t)seconds)/60);
        TIME_ZONE_INFORMATION tz;
        const DWORD status=GetTimeZoneInformation(&tz);
        zone->dsttime=status==TIME_ZONE_ID_DAYLIGHT ? 1 : 0;
    }
#else
    struct timeval t;
    struct timezone z;
    if (gettimeofday(&t,&z)) {
        /* Guest errno/TLS failure path is not implemented yet. */
        perror("STOP: host gettimeofday failed"); exit(21);
    }
    if (zone) { zone->minuteswest=z.tz_minuteswest; zone->dsttime=z.tz_dsttime; }
    if (value) { value->seconds=t.tv_sec; value->microseconds=t.tv_usec; }
#endif
    return 0;
}
"""

def blob_sha(raw:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+bytes([0])+raw).hexdigest()

def normalize(raw:bytes)->bytes:
    # Windows Git checkout CRLF is tolerated only for the EXACT pinned blob.
    return raw.replace(b"\r\n",b"\n")

def rewrite(source:str)->str:
    for label,old,new in (("original include",OLD_INCLUDE,NEW_INCLUDE),
                          ("original Windows guest time ABI",OLD_FN,NEW_FN)):
        if source.count(old)!=1 or new in source:
            raise ValueError("V153 source already staged or original drift: "+label)
        source=source.replace(old,new,1)
    if "runtime_time_resolve(const char *name)" not in source or (
        '"n88vx3C5nW8#I#J"' not in source):
        raise ValueError("V153 original guest-time symbol dispatch drift")
    if source.count("GetSystemTimePreciseAsFileTime(&ft);")!=1:
        raise ValueError("V153 native clock replacement invariant failed")
    return source

def transform(raw:bytes)->bytes:
    original=normalize(raw)
    if blob_sha(original)!=BLOB:
        raise ValueError("V153 expected exact YT1.3 original runtime_time.c Git blob")
    return rewrite(original.decode("utf-8")).encode("utf-8")

def stage(root:Path)->None:
    root=root.resolve()
    target=root/PATH
    if not target.is_file() or target.is_symlink():
        raise ValueError("V153 required original regular runtime_time.c")
    target.write_bytes(transform(target.read_bytes()))

if __name__=="__main__":
    if len(sys.argv)!=2:
        raise SystemExit("usage: stage_native_win32_clock_v153.py PINNED_DISPOSABLE_YT_SOURCE")
    stage(Path(sys.argv[1]))
    print("SHYT_V153_ORIGINAL_YT130_NATIVE_WIN32_WALL_CLOCK_STAGED_NOT_GAMEPLAY")
