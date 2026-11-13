/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef SHYT_STARTUP_MUTEX_IMPORT_V413_H
#define SHYT_STARTUP_MUTEX_IMPORT_V413_H
#include "native_startup_mutex_v413.h"
#include "native_static_guard_import_v413.h"

/* Restricted lifecycle for a single observed startup object. These
 * guest tokens are opaque and valid only in the bound slot. This is
 * not a general pthread registry or the game-wide synchronization ABI. */
enum ShytStartupMutexOpV413 {
    SHYT_MUTEX_ATTR_INIT, SHYT_MUTEX_ATTR_TYPE, SHYT_MUTEX_INIT, SHYT_MUTEX_ATTR_DESTROY
};
typedef struct {
    uint64_t target,next;
    enum ShytStartupMutexOpV413 op;
} ShytStartupMutexSiteV413;
typedef struct {
    ShytStartupMutexV413 host;
    ShytNativeOsVmV388 *owner;
    uint64_t attr_slot, mutex_slot;
    unsigned type2, live_attr;
} ShytStartupMutexStateV413;

#define SHYT_MUTEX_ATTR_TOKEN_V413 UINT64_C(0x413010001)
#define SHYT_MUTEX_OBJECT_TOKEN_V413 UINT64_C(0x413020001)
#define SHYT_MUTEX_EINVAL_V413 UINT64_C(0x80020016)
#define SHYT_MUTEX_EAGAIN_V413 UINT64_C(0x80020023)
static inline int shyt_mutex_slot_v413(uint64_t slot,uint64_t rsp) {
    return slot && !(slot&7u) && slot<=UINT64_MAX-8u && rsp<=UINT64_MAX-8u &&
           (slot>=rsp+8u || slot+8u<=rsp) &&
           shyt_generated_try_probe_v390(slot,8,SHYT_V386_READ|SHYT_V386_WRITE);
}
static inline int shyt_mutex_call_v413(ShytStartupMutexStateV413 *m,
    const ShytStartupMutexSiteV413 *site,BbCpu *expected_cpu,BbCpu *cpu,
    uint64_t target,uint64_t next) {
    if(!m || !m->owner || !site || !cpu || cpu!=expected_cpu ||
       !target || !next || target==next || target!=site->target || next!=site->next ||
       shyt_generated_owner_v392()!=m->owner ||
       shyt_generated_recovery_depth_v393()!=1u)return 0;

    const uint64_t arg=cpu->r[7], second=cpu->r[6], rsp=cpu->r[4];
    uint64_t status=SHYT_MUTEX_EINVAL_V413, word=0;
    const int attr_valid=m->live_attr &&
        shyt_mutex_slot_v413(m->attr_slot,rsp) &&
        shyt_generated_try_load_v390(m->attr_slot,8,&word) &&
        word==SHYT_MUTEX_ATTR_TOKEN_V413;
    switch(site->op) {
    case SHYT_MUTEX_ATTR_INIT:
        if(!m->live_attr && arg==m->attr_slot && arg!=m->mutex_slot &&
           shyt_mutex_slot_v413(arg,rsp) &&
           shyt_generated_try_store_v390(arg,8,SHYT_MUTEX_ATTR_TOKEN_V413)) {
            m->live_attr=1;
            m->type2=0;
            status=0;
        }
        break;
    case SHYT_MUTEX_ATTR_TYPE:
        if(attr_valid && arg==m->attr_slot && (uint32_t)second==2u) {
            m->type2=1;
            status=0;
        }
        break;
    case SHYT_MUTEX_INIT:
        if(attr_valid && m->type2 && !m->host.live &&
           arg==m->mutex_slot && second==m->attr_slot && !cpu->r[2] &&
           arg!=second && shyt_mutex_slot_v413(arg,rsp)) {
            status=SHYT_MUTEX_EAGAIN_V413;
            if(shyt_startup_mutex_init_v413(&m->host,2u)) {
                if(shyt_generated_try_store_v390(arg,8,SHYT_MUTEX_OBJECT_TOKEN_V413))status=0;
                else if(!shyt_startup_mutex_destroy_v413(&m->host))return 0;
            }
        }
        break;
    case SHYT_MUTEX_ATTR_DESTROY:
        if(attr_valid && arg==m->attr_slot && shyt_generated_try_store_v390(arg,8,0)) {
            m->live_attr=m->type2=0;
            status=0;
        }
        break;
    default:return 0;
    }
    cpu->r[0]=status;
    cpu->rip=next;
    return 1;
}
#endif
