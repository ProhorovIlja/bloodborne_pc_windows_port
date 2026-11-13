/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef _WIN32
#define _POSIX_C_SOURCE 200809L
#endif
#include "native_startup_mutex_v413.h"
#include <stdio.h>
#include <stdlib.h>
#define CHECK(x) do { if(!(x)){fprintf(stderr,"V413_MUTEX_FAIL_LINE %d\n",__LINE__);abort();} }while(0)
typedef struct { ShytStartupMutexV413 *mutex; int acquired; } Job;
#ifdef _WIN32
static DWORD WINAPI other(LPVOID arg)
#else
static void *other(void *arg)
#endif
{
    Job *j=arg;
    j->acquired=shyt_startup_mutex_try_v413(j->mutex);
    if(j->acquired)CHECK(shyt_startup_mutex_unlock_v413(j->mutex));
#ifdef _WIN32
    return 0;
#else
    return NULL;
#endif
}
static int other_acquired(ShytStartupMutexV413 *m) {
    Job j={m,0};
#ifdef _WIN32
    HANDLE h=CreateThread(NULL,0,other,&j,0,NULL);
    CHECK(h && WaitForSingleObject(h,INFINITE)==WAIT_OBJECT_0 && CloseHandle(h));
#else
    pthread_t t;
    CHECK(!pthread_create(&t,NULL,other,&j) && !pthread_join(t,NULL));
#endif
    return j.acquired;
}
int main(void) {
    ShytStartupMutexV413 m={0};
    CHECK(!shyt_startup_mutex_lock_v413(&m));
    CHECK(!shyt_startup_mutex_init_v413(&m,9));
    CHECK(shyt_startup_mutex_init_v413(&m,2));
    CHECK(!shyt_startup_mutex_init_v413(&m,2));
    CHECK(shyt_startup_mutex_lock_v413(&m));
    CHECK(shyt_startup_mutex_try_v413(&m));
    CHECK(!other_acquired(&m));
    CHECK(shyt_startup_mutex_unlock_v413(&m));
    CHECK(!other_acquired(&m));
    CHECK(shyt_startup_mutex_unlock_v413(&m));
    CHECK(other_acquired(&m));
    CHECK(shyt_startup_mutex_destroy_v413(&m));
    CHECK(!shyt_startup_mutex_destroy_v413(&m));
    CHECK(shyt_startup_mutex_init_v413(&m,2) && shyt_startup_mutex_destroy_v413(&m));
    puts("NATIVE_V413_STARTUP_RECURSIVE_MUTEX_PASS");
    return 0;
}
