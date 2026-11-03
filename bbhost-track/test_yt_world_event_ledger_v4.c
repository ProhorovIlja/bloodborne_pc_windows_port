/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "yt_world_event_ledger_v4.h"
#include <assert.h>
#include <stdio.h>

int main(void) {
    ShytWorldLedgerV4 ledger={0};
    ShytWorldDeltaV4 item={0};
    assert(!shyt_world_ledger_pop_v4(&ledger,&item));
    assert(shyt_world_ledger_push_v4(&ledger,900001u,1));
    assert(shyt_world_ledger_push_v4(&ledger,900001u,0));
    assert(shyt_world_ledger_pop_v4(&ledger,&item));
    assert(item.sequence==1u && item.flag_id==900001u && item.value==1);
    assert(shyt_world_ledger_pop_v4(&ledger,&item));
    assert(item.sequence==2u && item.flag_id==900001u && item.value==0);
    assert(!shyt_world_ledger_pop_v4(&ledger,&item));
    for(unsigned i=0;i<SHYT_WORLD_EVENT_CAP_V4;++i)
        assert(shyt_world_ledger_push_v4(&ledger,70000u+i,i%2u));
    assert(ledger.count==SHYT_WORLD_EVENT_CAP_V4);
    assert(!shyt_world_ledger_push_v4(&ledger,99u,1));
    assert(ledger.invalid_incremental && ledger.count==0u);
    assert(!shyt_world_ledger_pop_v4(&ledger,&item));
    assert(!shyt_world_ledger_push_v4(&ledger,99u,0));
    shyt_world_ledger_reset_v4(&ledger);
    assert(!ledger.invalid_incremental && ledger.count==0u);
    assert(shyt_world_ledger_push_v4(&ledger,1u,1));
    assert(!shyt_world_ledger_push_v4(&ledger,1u,2));
    assert(ledger.invalid_incremental && ledger.count==0u);
    shyt_world_ledger_reset_v4(&ledger);
    ledger.next_sequence=UINT64_MAX;
    assert(!shyt_world_ledger_push_v4(&ledger,900u,1));
    assert(ledger.invalid_incremental);
    shyt_world_ledger_reset_v4(&ledger);
    for(unsigned i=0;i<SHYT_WORLD_EVENT_CAP_V4+20u;++i) {
        if(ledger.count==SHYT_WORLD_EVENT_CAP_V4)
            assert(shyt_world_ledger_pop_v4(&ledger,&item));
        assert(shyt_world_ledger_push_v4(&ledger,100u+i,1));
    }
    assert(ledger.count==SHYT_WORLD_EVENT_CAP_V4);
    while(shyt_world_ledger_pop_v4(&ledger,&item)) {
        assert(item.sequence>0);
    }
    assert(!ledger.invalid_incremental);
    puts("SHYT_BBHOST_V4_WORLD_FLAG_LEDGER_OVERFLOW_INVALIDATES_NOT_REPLICATES_PASS");
}
