/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef SHYT_STARTUP_RWLOCK_V414_H
#define SHYT_STARTUP_RWLOCK_V414_H
#ifdef _WIN32
#include <windows.h>
#else
#include <pthread.h>
#endif
#include "full_cpu_abi_v194.h"
#include "native_host_recovery_v393.h"

/* Stable object, single startup controller. No timed locks, shared
 * acquisitions, blocking across controllers or PS4 internal layout. */
typedef struct {
#ifdef _WIN32
    SRWLOCK os;
#else
    pthread_rwlock_t os;
#endif
    unsigned live, held;
} ShytStartupRwlockV414;
static inline int shyt_rw_init_v414(ShytStartupRwlockV414 *r) {
    if(!r || r->live)return 0;
#ifdef _WIN32
    InitializeSRWLock(&r->os);
#else
    if(pthread_rwlock_init(&r->os,NULL))return 0;
#endif
    r->live=1;
    return 1;
}
static inline int shyt_rw_destroy_v414(ShytStartupRwlockV414 *r) {
    if(!r || !r->live || r->held)return 0;
#ifndef _WIN32
    if(pthread_rwlock_destroy(&r->os))return 0;
#endif
    r->live=0;
    return 1;
}
static inline int shyt_rw_write_v414(ShytStartupRwlockV414 *r) {
    if(!r || !r->live || r->held)return 0;
#ifdef _WIN32
    AcquireSRWLockExclusive(&r->os);
#else
    if(pthread_rwlock_wrlock(&r->os))return 0;
#endif
    r->held=1;
    return 1;
}
static inline int shyt_rw_unlock_v414(ShytStartupRwlockV414 *r) {
    if(!r || !r->live || !r->held)return 0;
#ifdef _WIN32
    ReleaseSRWLockExclusive(&r->os);
#else
    if(pthread_rwlock_unlock(&r->os))return 0;
#endif
    r->held=0;
    return 1;
}
#define SHYT_RW_TOKEN_V414 UINT64_C(0x414010001)
enum ShytRwOpV414 { SHYT_RW_INIT, SHYT_RW_WRITE, SHYT_RW_UNLOCK };
typedef struct {
    uint64_t target,next,slot;
    enum ShytRwOpV414 op;
} ShytRwSiteV414;
/* Bound owner and immutable caller-selected site. EAX holds low 32-bit
 * Orbis status. A bad route returns 0 without touching guest state. */
static inline int shyt_rw_call_v414(ShytStartupRwlockV414 *r,
    ShytNativeOsVmV388 *owner,const ShytRwSiteV414 *site,
    BbCpu *expected,BbCpu *cpu,uint64_t target,uint64_t next) {
    if(!r || !owner || !site || !cpu || cpu!=expected || !target || !next ||
       target==next || target!=site->target || next!=site->next ||
       (unsigned)site->op>SHYT_RW_UNLOCK || shyt_generated_owner_v392()!=owner ||
       shyt_generated_recovery_depth_v393()!=1u)return 0;
    const uint64_t rsp=cpu->r[4], slot=site->slot;
    uint64_t result=UINT64_C(0x80020016), word=0;
    if(slot && !(slot&7u) && slot<=UINT64_MAX-8u && rsp<=UINT64_MAX-8u &&
       (slot>=rsp+8u || slot+8u<=rsp) && cpu->r[7]==slot &&
       shyt_generated_try_probe_v390(slot,8,SHYT_V386_READ|SHYT_V386_WRITE)) {
        if(site->op==SHYT_RW_INIT && !r->live && !cpu->r[6] && !cpu->r[2]) {
            result=UINT64_C(0x80020023);
            if(shyt_rw_init_v414(r)) {
                if(shyt_generated_try_store_v390(slot,8,SHYT_RW_TOKEN_V414))result=0;
                else if(!shyt_rw_destroy_v414(r))return 0;
            }
        } else if(site->op!=SHYT_RW_INIT &&
                  shyt_generated_try_load_v390(slot,8,&word) && word==SHYT_RW_TOKEN_V414) {
            if(site->op==SHYT_RW_WRITE ? shyt_rw_write_v414(r) : shyt_rw_unlock_v414(r))
                result=0;
        }
    }
    cpu->r[0]=result;
    cpu->rip=next;
    return 1;
}
#endif
