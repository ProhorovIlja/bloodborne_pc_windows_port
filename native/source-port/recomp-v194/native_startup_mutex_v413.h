/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef SHYT_STARTUP_MUTEX_V413_H
#define SHYT_STARTUP_MUTEX_V413_H
#ifdef _WIN32
#include <windows.h>
#else
#include <pthread.h>
#endif

/* Host-only backend for the type-2 recursive mutex identified in the
 * first retail initializer. Object lives at a stable address. Control
 * thread initializes before publication and destroys after all users join,
 * with no lock held. Only a thread holding the mutex may unlock it.
 * No PS4 handle layout, error translation or guest pointer exposure. */
typedef struct {
#ifdef _WIN32
    CRITICAL_SECTION os;
#else
    pthread_mutex_t os;
#endif
    unsigned live;
} ShytStartupMutexV413;
static inline int shyt_startup_mutex_init_v413(ShytStartupMutexV413 *m,unsigned type) {
    if(!m || m->live || type!=2)return 0;
#ifdef _WIN32
    if(!InitializeCriticalSectionEx(&m->os,0,0))return 0;
#else
    pthread_mutexattr_t attr;
    if(pthread_mutexattr_init(&attr))return 0;
    const int type_error=pthread_mutexattr_settype(&attr,PTHREAD_MUTEX_RECURSIVE);
    const int init_error=type_error?type_error:pthread_mutex_init(&m->os,&attr);
    if(pthread_mutexattr_destroy(&attr)) {
        if(!init_error) (void)pthread_mutex_destroy(&m->os);
        return 0;
    }
    if(init_error)return 0;
#endif
    m->live=1;
    return 1;
}
static inline int shyt_startup_mutex_lock_v413(ShytStartupMutexV413 *m) {
    if(!m || !m->live)return 0;
#ifdef _WIN32
    EnterCriticalSection(&m->os);
    return 1;
#else
    return pthread_mutex_lock(&m->os)==0;
#endif
}
static inline int shyt_startup_mutex_try_v413(ShytStartupMutexV413 *m) {
    if(!m || !m->live)return 0;
#ifdef _WIN32
    return TryEnterCriticalSection(&m->os)!=0;
#else
    return pthread_mutex_trylock(&m->os)==0;
#endif
}
static inline int shyt_startup_mutex_unlock_v413(ShytStartupMutexV413 *m) {
    if(!m || !m->live)return 0;
#ifdef _WIN32
    LeaveCriticalSection(&m->os);
    return 1;
#else
    return pthread_mutex_unlock(&m->os)==0;
#endif
}
static inline int shyt_startup_mutex_destroy_v413(ShytStartupMutexV413 *m) {
    if(!m || !m->live)return 0;
#ifdef _WIN32
    DeleteCriticalSection(&m->os);
#else
    if(pthread_mutex_destroy(&m->os))return 0;
#endif
    m->live=0;
    return 1;
}
#endif
