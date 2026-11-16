/* SPDX-License-Identifier: GPL-2.0-or-later */
#define _POSIX_C_SOURCE 200809L
#include "mutex_host_v523.h"

struct probe { struct bb_mutex_slot_v523 *slot; int busy, locked; };
static void *attempt(void *arg) {
    struct probe *p=arg;
    const int rc=pthread_mutex_trylock(&p->slot->mutex);
    p->busy=rc==EBUSY;
    p->locked=rc==0 && pthread_mutex_unlock(&p->slot->mutex)==0;
    return NULL;
}
static int probe(struct bb_mutex_slot_v523 *slot, int busy) {
    struct probe p={.slot=slot}; pthread_t t;
    return !pthread_create(&t,NULL,attempt,&p) && !pthread_join(t,NULL) &&
           p.busy==busy && p.locked==!busy;
}
int main(void) {
    for (uint64_t i=1;i<=64;++i) {
        struct bb_mutex_slot_v523 slot={0};
        if (bb_mutex_host_v523(&slot,0).status!=BB_MUTEX_MISS_V522 || slot.key) return 1;
        const struct bb_mutex_result_v522 r=bb_mutex_host_v523(&slot,i);
        if (r.status!=BB_MUTEX_RETURN_V522 || r.value || slot.key!=i ||
            bb_mutex_host_v523(&slot,i+1).status!=BB_MUTEX_MISS_V522 || slot.key!=i) return 2;
        if (pthread_mutex_lock(&slot.mutex) || pthread_mutex_trylock(&slot.mutex) ||
            !probe(&slot,1) || pthread_mutex_unlock(&slot.mutex) || !probe(&slot,1) ||
            pthread_mutex_unlock(&slot.mutex) || !probe(&slot,0) ||
            pthread_mutex_destroy(&slot.mutex)) return 3;
    }
    return 0;
}
