/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_generated_scope_v392.h"
#include <stdlib.h>
int shyt_generated_scope_begin_v392(ShytGeneratedScopeV392 *scope,
                                    ShytNativeOsVmV388 *owner) {
    ShytNativeOsVmV388 *current;
    if(!scope || scope->state || scope->owner || !owner ||
       owner->sealed!=1 || owner->released)return 0;
    current=shyt_generated_owner_v392();
    if(current && current!=owner)return 0; /* never borrow wrong VM */
    if(!current && !shyt_generated_enter_v390(owner))return 0;
    scope->owner=owner;
    scope->state=current?2u:1u;
    return 1;
}
int shyt_generated_scope_end_v392(ShytGeneratedScopeV392 *scope) {
    if(!scope || !scope->owner ||
       (scope->state!=1u && scope->state!=2u) ||
       shyt_generated_owner_v392()!=scope->owner)return 0;
    if(scope->state==1u && !shyt_generated_leave_v390())return 0;
    scope->owner=NULL;
    scope->state=0;
    return 1;
}
int shyt_generated_call_v392(ShytNativeOsVmV388 *owner,
                            ShytGeneratedFnV392 fn,
                            BbCpu *cpu,
                            ShytGeneratedPreflightV392 preflight,
                            void *ctx) {
    ShytGeneratedScopeV392 scope={0};
    int permitted;
    if(!owner || !fn || !cpu ||
       !shyt_generated_scope_begin_v392(&scope,owner))return 0;
    permitted=preflight?preflight(cpu,ctx):1;
    if(permitted)fn(cpu);
    /* Inability to restore TLS lease state is a fatal host invariant.
     * Never silently return a success after leaking a pinned mapping. */
    if(!shyt_generated_scope_end_v392(&scope))abort();
    return permitted?1:0;
}
