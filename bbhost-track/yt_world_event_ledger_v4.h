/* SPDX-License-Identifier: GPL-3.0-or-later
 * SHYT V4: the actual BBHost game engine's event-flag callback can deliver
 * world progression deltas (boss kills, doors, NPC state) on main thread.
 *
 * This bounded ledger is ONLY a local observation seam for porting YT.
 * It has no peer identity, room epoch, signed lease, or transport, so no
 * code may forward or apply its contents to another game instance.
 * Overflows invalidate the entire incremental stream; a future verified
 * full snapshot/epoch reset is required before any replication.
 */
#ifndef SHYT_BBHOST_YT_WORLD_LEDGER_V4_H
#define SHYT_BBHOST_YT_WORLD_LEDGER_V4_H
#include <stdint.h>
#include <limits.h>
#define SHYT_WORLD_EVENT_CAP_V4 128u

typedef struct ShytWorldDeltaV4 {
    uint64_t sequence;
    uint32_t flag_id;
    int value;
} ShytWorldDeltaV4;

typedef struct ShytWorldLedgerV4 {
    ShytWorldDeltaV4 entries[SHYT_WORLD_EVENT_CAP_V4];
    uint64_t next_sequence;
    unsigned head, count;
    int invalid_incremental;
} ShytWorldLedgerV4;

static inline void shyt_world_ledger_reset_v4(ShytWorldLedgerV4 *ledger) {
    if (!ledger) return;
    ledger->next_sequence=0;
    ledger->head=ledger->count=0;
    ledger->invalid_incremental=0;
}

static inline void shyt_world_ledger_invalidate_v4(ShytWorldLedgerV4 *ledger) {
    if (!ledger) return;
    ledger->head=ledger->count=0;
    ledger->invalid_incremental=1;
}

static inline int shyt_world_ledger_push_v4(ShytWorldLedgerV4 *ledger,
                                            uint32_t flag,int value) {
    if (!ledger || ledger->invalid_incremental) return 0;
    if ((value!=0 && value!=1) ||
        ledger->count==SHYT_WORLD_EVENT_CAP_V4 ||
        ledger->next_sequence==UINT64_MAX) {
        shyt_world_ledger_invalidate_v4(ledger);
        return 0;
    }
    const unsigned slot=(ledger->head+ledger->count)%SHYT_WORLD_EVENT_CAP_V4;
    ledger->entries[slot].sequence=++ledger->next_sequence;
    ledger->entries[slot].flag_id=flag;
    ledger->entries[slot].value=value;
    ++ledger->count;
    return 1;
}

static inline int shyt_world_ledger_pop_v4(ShytWorldLedgerV4 *ledger,
                                           ShytWorldDeltaV4 *out) {
    if (!ledger || !out || ledger->invalid_incremental || !ledger->count)
        return 0;
    *out=ledger->entries[ledger->head];
    ledger->head=(ledger->head+1)%SHYT_WORLD_EVENT_CAP_V4;
    --ledger->count;
    return 1;
}
#endif
