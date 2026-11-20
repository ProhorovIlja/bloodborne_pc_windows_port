/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_STARTUP_RWLOCK_HOST_V539_H
#define BB_STARTUP_RWLOCK_HOST_V539_H
#include <stdint.h>
#ifdef _WIN32
#include <windows.h>
#else
#include <pthread.h>
#endif

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
#endif
