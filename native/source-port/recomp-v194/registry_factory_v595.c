/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Cold-path composition only; build instead of the V594 unity unit. */
#include "registry_bind_v594.c"

extern int candidate(unsigned char *,size_t,unsigned char *,size_t,int (*)(void *),int (*)(void *));
extern int bb_registry_cold_v592(unsigned char *,size_t,void *(*)(void *,size_t,size_t),
    void *(*)(void *,size_t),void (*)(void *),void (*)(void *));

/* A single caller owns a preconstructed, fresh manager. Mutex callbacks
 * for bootstrap must complete; area registration uses checked locks.
 * Failure after seed is terminal for this owner, not a retry in place.
 * The diagnostic token is supplied by the native caller, never a guest RVA. */
void *bb_registry_factory_cold_v595(unsigned char *owner,size_t owner_size,
    unsigned char *arena,size_t arena_size,int (*ready)(void *),int (*init)(void *),
    void *(*aligned)(void *,size_t,size_t),void *(*allocate)(void *,size_t),
    void (*take)(void *),void (*drop)(void *),const BbAreaOps593 *area,
    void (*context)(void *,const void *,uint32_t),const void *source,int *status) {
    if (!status) return NULL;
    *status=BB593_INVALID;
    if (sizeof(uintptr_t)!=8 || !owner || owner_size<0x48c || !arena || arena_size!=0x100000 ||
        !ready || !init || !aligned || !allocate || !take || !drop || !area || !area->lock ||
        !area->unlock || !area->overlap || !area->allocate || !area->release || !context || !source ||
        load594(owner+0x468) || load594(owner+0x460)!=(uintptr_t)owner) return NULL;
    if (!candidate(owner,owner_size,arena,arena_size,ready,init)) return NULL;
    if (bb_registry_cold_v592(owner,owner_size,aligned,allocate,take,drop)!=1) {
        *status=BB593_ALLOC;
        return NULL;
    }
    context(area->ctx,source,0xfb);
    *status=bb_registry_bind_v594(owner,owner_size,arena,arena_size,area,
        (uintptr_t)(owner+0x458),(uintptr_t)arena,arena_size);
    /* Retail ignores the registration boolean; native hard failures do not
     * return a usable owner. A committed unlock error must not be retried. */
    return *status>=0?owner:NULL;
}
