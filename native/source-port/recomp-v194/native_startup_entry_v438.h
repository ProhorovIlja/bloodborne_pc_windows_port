/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef SHYT_STARTUP_ENTRY_V438_H
#define SHYT_STARTUP_ENTRY_V438_H
#include "native_startup_rcapi_v436.h"

enum {
    SHYT_V438_BAD_ENTRY_STACK=43801,
    SHYT_V438_BAD_OUTER_RETURN=43802,
    SHYT_V439_POSTCONDITION=43901
};

/* Call an exact prebound constructor entry. This is for translated bodies
 * that consume one synthetic guest return word with normal RET semantics.
 * The host supplies a dedicated return sentinel and stable sorted registry.
 * Recovery stops the replay; it does not roll back memory or imports. */
int shyt_startup_entry_v438(ShytStartupDispatchV435 *state,uint32_t ordinal,
    const RcFunction *registry,size_t count,uint64_t entry,uint64_t sentinel,int *reason);
typedef int (*ShytCtorPostV439)(BbCpu *,uint32_t,uint64_t,void *);
/* Trusted read-only postcondition, checked while the VM is still pinned. */
int shyt_startup_entry_checked_v439(ShytStartupDispatchV435 *state,uint32_t ordinal,
    uint64_t entry,uint64_t sentinel,ShytCtorPostV439 post,void *context,int *reason);
#endif
