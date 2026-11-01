/* SPDX-License-Identifier: GPL-2.0-or-later
 * V228 pinned guest arena. All unmap/protect operations are serialized
 * against successful pins; callbacks must not longjmp while pinned.
 */
#include "native_guest_arena_v228.h"
#include <stdint.h>
#include <string.h>

/* Win64 compiler TLS: a pin can be released only by the owning thread. */
#if defined(__MINGW32__) || (defined(__GNUC__) && !defined(_MSC_VER))
/* clang --target=...-windows-gnu does not accept __declspec(thread). */
static __thread ShytGuestArenaV228 *g_current_pin;
#else
/* clang-cl/MSVC Windows ABI uses its native TLS storage class. */
static __declspec(thread) ShytGuestArenaV228 *g_current_pin;
#endif

int shyt_guest_arena_v228_create(ShytGuestArenaV228 *a, size_t bytes) {
    if (!a || a->initialized || a->live || a->base || a->size)
        return 0;
    SYSTEM_INFO si;
    GetSystemInfo(&si);
    const size_t page=(size_t)si.dwPageSize;
    if (page < 4096 || !bytes || bytes > 128u * 1024u * 1024u ||
        bytes % page) return 0;
    /* Only a fresh zero-initialized arena may initialize this lock. */
    InitializeSRWLock(&a->lifetime_lock);
    a->initialized=1;
    void *p=VirtualAlloc(NULL,bytes,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    if (!p) return 0;
    const uint64_t begin=(uint64_t)(uintptr_t)p;
    if ((uint64_t)bytes > UINT64_MAX-begin) {
        VirtualFree(p,0,MEM_RELEASE);
        return 0;
    }
    const ShytGuestWindowV227 w={begin,begin+(uint64_t)bytes};
    if (!shyt_guest_memory_v227_init(&a->writable_window,&w,1)) {
        VirtualFree(p,0,MEM_RELEASE);
        return 0;
    }
    a->base=p;
    a->size=bytes;
    a->live=1;
    return 1;
}
int shyt_guest_arena_v228_pin(ShytGuestArenaV228 *a) {
    if (!a || !a->initialized || g_current_pin) return 0;
    AcquireSRWLockShared(&a->lifetime_lock);
    if (!a->live || !a->base) {
        ReleaseSRWLockShared(&a->lifetime_lock);
        return 0;
    }
    g_current_pin=a;
    return 1;
}
int shyt_guest_arena_v228_unpin(ShytGuestArenaV228 *a) {
    if (!a || g_current_pin != a) return 0;
    g_current_pin=NULL;
    ReleaseSRWLockShared(&a->lifetime_lock);
    return 1;
}
int shyt_guest_arena_v228_permit_pinned(
    void *ctx, uint64_t address, size_t bytes, int write) {
    ShytGuestArenaV228 *a=(ShytGuestArenaV228 *)ctx;
    if (!a || g_current_pin!=a || !a->live) return 0;
    return shyt_guest_memory_v227_permit(
        &a->writable_window,address,bytes,write);
}
int shyt_guest_arena_v228_protect(
    ShytGuestArenaV228 *a,size_t offset,size_t bytes,DWORD protect) {
    if (!a || !a->initialized || g_current_pin==a ||
        (protect!=PAGE_READWRITE && protect!=PAGE_READONLY &&
         protect!=PAGE_NOACCESS)) return 0;
    SYSTEM_INFO si;
    GetSystemInfo(&si);
    const size_t page=(size_t)si.dwPageSize;
    if (!page || !bytes || offset%page || bytes%page) return 0;
    AcquireSRWLockExclusive(&a->lifetime_lock);
    int ok=0;
    if (a->live && a->base && offset<=a->size &&
        bytes<=a->size-offset) {
        DWORD previous=0;
        ok=VirtualProtect((unsigned char*)a->base+offset,bytes,
                          protect,&previous)!=0;
    }
    ReleaseSRWLockExclusive(&a->lifetime_lock);
    return ok;
}
int shyt_guest_arena_v228_destroy(ShytGuestArenaV228 *a) {
    if (!a || !a->initialized || g_current_pin==a) return 0;
    AcquireSRWLockExclusive(&a->lifetime_lock);
    int ok=0;
    if (a->live && a->base && VirtualFree(a->base,0,MEM_RELEASE)) {
        a->live=0;
        a->base=NULL;
        a->size=0;
        memset(&a->writable_window,0,sizeof(a->writable_window));
        ok=1;
    }
    ReleaseSRWLockExclusive(&a->lifetime_lock);
    return ok;
}
