/* V228 real Windows guest arena ownership + concurrent teardown test.
 * Only invented allocations and values; no original Bloodborne bytes.
 */
#include "native_guest_arena_v228.h"
#include <assert.h>
#include <stdint.h>

typedef struct {
    ShytGuestArenaV228 *arena;
    HANDLE pinned;
    HANDLE release;
    HANDLE destroy_started;
    int destroyed;
} ThreadState;

static DWORD WINAPI hold_pin(LPVOID user) {
    ThreadState *t=(ThreadState*)user;
    assert(shyt_guest_arena_v228_pin(t->arena));
    SetEvent(t->pinned);
    assert(WaitForSingleObject(t->release,5000)==WAIT_OBJECT_0);
    assert(shyt_guest_arena_v228_unpin(t->arena));
    return 0;
}
static DWORD WINAPI release_arena(LPVOID user) {
    ThreadState *t=(ThreadState*)user;
    SetEvent(t->destroy_started);
    t->destroyed=shyt_guest_arena_v228_destroy(t->arena);
    return 0;
}
int main(void) {
    SYSTEM_INFO si;
    GetSystemInfo(&si);
    const size_t page=(size_t)si.dwPageSize;
    assert(page>=4096 && page<=65536);
    ShytGuestArenaV228 arena={0};
    assert(!shyt_guest_arena_v228_create(&arena,page+1));
    assert(shyt_guest_arena_v228_create(&arena,page*3));
    assert(!shyt_guest_arena_v228_create(&arena,page*3));
    const uint64_t base=(uint64_t)(uintptr_t)arena.base;
    assert(base && arena.live && arena.initialized);
    assert(!shyt_guest_arena_v228_permit_pinned(&arena,base+16,8,1));
    assert(shyt_guest_arena_v228_pin(&arena));
    assert(!shyt_guest_arena_v228_pin(&arena));
    assert(shyt_guest_arena_v228_permit_pinned(&arena,base+16,8,1));
    assert(!shyt_guest_arena_v228_permit_pinned(&arena,base+16,8,0));
    assert(!shyt_guest_arena_v228_permit_pinned(&arena,base-8,8,1));
    assert(!shyt_guest_arena_v228_permit_pinned(
        &arena,base+(uint64_t)page*3-4,8,1));
    assert(!shyt_guest_arena_v228_destroy(&arena));
    assert(!shyt_guest_arena_v228_protect(&arena,page,page,PAGE_READONLY));
    assert(shyt_guest_arena_v228_unpin(&arena));
    assert(!shyt_guest_arena_v228_unpin(&arena));
    assert(shyt_guest_arena_v228_protect(&arena,page,page,PAGE_READONLY));
    assert(shyt_guest_arena_v228_pin(&arena));
    assert(shyt_guest_arena_v228_permit_pinned(&arena,base+8,8,1));
    assert(!shyt_guest_arena_v228_permit_pinned(&arena,base+page+8,8,1));
    assert(!shyt_guest_arena_v228_permit_pinned(&arena,base+page-4,8,1));
    assert(shyt_guest_arena_v228_unpin(&arena));
    assert(shyt_guest_arena_v228_protect(&arena,page,page,PAGE_READWRITE));
    ThreadState state={0};
    state.arena=&arena;
    state.pinned=CreateEventW(NULL,TRUE,FALSE,NULL);
    state.release=CreateEventW(NULL,TRUE,FALSE,NULL);
    state.destroy_started=CreateEventW(NULL,TRUE,FALSE,NULL);
    assert(state.pinned && state.release && state.destroy_started);
    HANDLE worker=CreateThread(NULL,0,hold_pin,&state,0,NULL);
    assert(worker);
    assert(WaitForSingleObject(state.pinned,5000)==WAIT_OBJECT_0);
    HANDLE killer=CreateThread(NULL,0,release_arena,&state,0,NULL);
    assert(killer);
    assert(WaitForSingleObject(state.destroy_started,5000)==WAIT_OBJECT_0);
    /* Free cannot complete until the peer releases its reader lock. */
    assert(WaitForSingleObject(killer,120)==WAIT_TIMEOUT);
    assert(arena.live && arena.base==(void*)(uintptr_t)base);
    SetEvent(state.release);
    assert(WaitForSingleObject(worker,5000)==WAIT_OBJECT_0);
    assert(WaitForSingleObject(killer,5000)==WAIT_OBJECT_0);
    assert(state.destroyed);
    assert(!arena.live && !arena.base);
    assert(!shyt_guest_arena_v228_pin(&arena));
    assert(!shyt_guest_arena_v228_permit_pinned(&arena,base+8,8,1));
    assert(!shyt_guest_arena_v228_protect(&arena,0,page,PAGE_READWRITE));
    assert(!shyt_guest_arena_v228_destroy(&arena));
    assert(!shyt_guest_arena_v228_create(&arena,page)); /* one-shot */
    CloseHandle(worker); CloseHandle(killer);
    CloseHandle(state.pinned); CloseHandle(state.release);
    CloseHandle(state.destroy_started);
    return 0;
}
