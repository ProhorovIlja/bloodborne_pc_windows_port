/* V227: synthetic actual Windows VM protection behavior, no game data. */
#include "native_guest_memory_v227.h"
#include <assert.h>
#include <stdint.h>
#if defined(_WIN64)
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#endif

int main(void) {
    ShytGuestMemoryV227 memory = {0};
    ShytGuestWindowV227 invalid[2] = {{0x1000,0x3000},{0x2000,0x4000}};
    assert(!shyt_guest_memory_v227_init(&memory,invalid,2));
    assert(memory.count==0);
    invalid[1].begin=0x3000;
    assert(shyt_guest_memory_v227_init(&memory,invalid,2));
    assert(memory.count==2);
    assert(shyt_guest_memory_v227_contains(&memory,0x1000,8));
    assert(shyt_guest_memory_v227_contains(&memory,0x2ffc,4));
    assert(!shyt_guest_memory_v227_contains(&memory,0x2ffc,8));
    assert(!shyt_guest_memory_v227_contains(&memory,0x0fff,8));
    assert(!shyt_guest_memory_v227_contains(&memory,0x2000,0));
    assert(!shyt_guest_memory_v227_contains(&memory,UINT64_MAX-1,16));
    assert(!shyt_guest_memory_v227_contains(&memory,0x1000,4097));
    assert(!shyt_guest_memory_v227_permit(&memory,0x1000,8,0));
#if defined(_WIN64)
    SYSTEM_INFO sys;
    GetSystemInfo(&sys);
    const SIZE_T page=(SIZE_T)sys.dwPageSize;
    assert(page>=4096 && page<65536);
    unsigned char *region = (unsigned char *)VirtualAlloc(
        NULL,page*3,MEM_RESERVE|MEM_COMMIT,PAGE_READWRITE);
    assert(region);
    const uint64_t base=(uint64_t)(uintptr_t)region;
    ShytGuestWindowV227 window={base,base+(uint64_t)(page*3)};
    assert(shyt_guest_memory_v227_init(&memory,&window,1));
    assert(shyt_guest_memory_v227_permit(&memory,base+8,8,1));
    assert(shyt_guest_memory_v227_permit(&memory,base+page-4,8,1));
    assert(!shyt_guest_memory_v227_permit(&memory,base+page*3-4,8,1));
    assert(!shyt_guest_memory_v227_permit(&memory,base+8,8,2));
    DWORD old;
    assert(VirtualProtect(region+page,page,PAGE_READONLY,&old));
    assert(!shyt_guest_memory_v227_permit(&memory,base+page+8,8,1));
    assert(!shyt_guest_memory_v227_permit(&memory,base+page-4,8,1));
    assert(shyt_guest_memory_v227_permit(&memory,base+8,8,1));
    assert(VirtualProtect(region+page,page,PAGE_READWRITE,&old));
    assert(shyt_guest_memory_v227_permit(&memory,base+page-4,8,1));
    assert(VirtualProtect(region+page,page,PAGE_READWRITE|PAGE_GUARD,&old));
    assert(!shyt_guest_memory_v227_permit(&memory,base+page+8,8,1));
    assert(VirtualProtect(region+page,page,PAGE_READWRITE,&old));
    assert(shyt_guest_memory_v227_permit(&memory,base+page+8,8,1));
    assert(VirtualFree(region,0,MEM_RELEASE));
    assert(!shyt_guest_memory_v227_permit(&memory,base+8,8,1));
#else
    /* There is no Linux host page validator in this Windows-only component. */
    assert(!shyt_guest_memory_v227_permit(&memory,0x1000,8,1));
#endif
    return 0;
}
