/* SPDX-License-Identifier: GPL-2.0-or-later
 * V227: only vetted guest allocations and actually writable Win64 pages.
 * Caller keeps allocations pinned, and no thread may VirtualFree/
 * VirtualProtect/unmap the ranges while V226 is executing an import.
 */
#include "native_guest_memory_v227.h"
#include <string.h>
#if defined(_WIN64)
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#endif

int shyt_guest_memory_v227_init(ShytGuestMemoryV227 *map,
    const ShytGuestWindowV227 *windows, size_t count) {
    if (!map || !windows || count == 0 ||
        count > SHYT_GUEST_MAX_WINDOWS_V227) return 0;
    ShytGuestMemoryV227 candidate = {0};
    uint64_t previous_end = 0;
    for (size_t i = 0; i < count; ++i) {
        if (!windows[i].begin || windows[i].end <= windows[i].begin ||
            (i > 0 && windows[i].begin < previous_end))
            return 0;
        candidate.windows[i] = windows[i];
        previous_end = windows[i].end;
    }
    candidate.count = count;
    *map = candidate;
    return 1;
}
int shyt_guest_memory_v227_contains(const ShytGuestMemoryV227 *map,
    uint64_t address, size_t bytes) {
    if (!map || !address || !bytes || bytes > 4096 ||
        (uint64_t)bytes > UINT64_MAX - address ||
        map->count == 0 || map->count > SHYT_GUEST_MAX_WINDOWS_V227)
        return 0;
    const uint64_t end = address + (uint64_t)bytes;
    for (size_t i = 0; i < map->count; ++i) {
        if (address >= map->windows[i].begin &&
            end <= map->windows[i].end) return 1;
    }
    return 0;
}
int shyt_guest_memory_v227_permit(void *context, uint64_t address,
    size_t bytes, int write) {
    const ShytGuestMemoryV227 *map = (const ShytGuestMemoryV227 *)context;
    if (write != 1 || !shyt_guest_memory_v227_contains(map, address, bytes))
        return 0;
#if defined(_WIN64)
    uint64_t cursor = address;
    const uint64_t end = address + (uint64_t)bytes;
    while (cursor < end) {
        MEMORY_BASIC_INFORMATION mbi;
        if (!VirtualQuery((LPCVOID)(uintptr_t)cursor, &mbi, sizeof(mbi)))
            return 0;
        if (mbi.State != MEM_COMMIT ||
            (mbi.Protect & (PAGE_GUARD | PAGE_NOACCESS)))
            return 0;
        const DWORD base = mbi.Protect & 0xffu;
        if (base != PAGE_READWRITE && base != PAGE_WRITECOPY &&
            base != PAGE_EXECUTE_READWRITE &&
            base != PAGE_EXECUTE_WRITECOPY) return 0;
        const uint64_t start = (uint64_t)(uintptr_t)mbi.BaseAddress;
        if (start > cursor ||
            (uint64_t)mbi.RegionSize > UINT64_MAX - start) return 0;
        const uint64_t region_end = start + (uint64_t)mbi.RegionSize;
        if (region_end <= cursor) return 0;
        cursor = region_end < end ? region_end : end;
    }
    return 1;
#else
    /* No pretend Linux/other OS implementation. */
    return 0;
#endif
}
