/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef SHYT_NATIVE_CRT_CHECKED_BOOT_V448_H
#define SHYT_NATIVE_CRT_CHECKED_BOOT_V448_H
#include "native_crt_lifecycle_v409.h"
#include "native_startup_retail_plan_v439.h"

typedef struct {
    ShytStartupDispatchV435 *state;
    const ShytCtorRowV427 *rows;
    size_t count;
    /* Caller obtains this separately from the complete audited startup order.
     * Count equality alone does not attest row identity or retail provenance. */
    size_t expected_count;
    uint64_t sentinel;
    ShytCtorPostV439 post;
    void *post_context;
    ShytReplayReportV437 report;
    enum ShytReplayResultV437 result;
} ShytCheckedBootV448;

typedef struct {
    ShytCheckedBootV448 *plan;
    const ShytCrtHooksV409 *host;
    void *context;
} ShytBootBridgeV448;

static inline int shyt_boot_env_v448(void *opaque,int argc,char *const *argv,
    char *const *envp) {
    ShytBootBridgeV448 *b=opaque;
    return b->host->setup_environment(b->context,argc,argv,envp);
}
static inline int shyt_boot_init_v448(void *opaque,ShytCrtV409 *crt) {
    ShytBootBridgeV448 *b=opaque;
    ShytCheckedBootV448 *p=b->plan;
    (void)crt;
    p->result=shyt_startup_retail_plan_v439(p->state,p->rows,1,p->count,
        p->sentinel,p->post,p->post_context,&p->report);
    return p->result==SHYT_REPLAY_COMPLETE && p->report.returned==p->expected_count;
}
static inline int shyt_boot_main_v448(void *opaque,ShytCrtV409 *crt,int argc,
    char *const *argv,void *third) {
    ShytBootBridgeV448 *b=opaque;
    return b->host->main_entry(b->context,crt,argc,argv,third);
}
static inline void shyt_boot_notify_v448(void *opaque,int status) {
    ShytBootBridgeV448 *b=opaque;
    b->host->main_returned(b->context,status);
}

/* Synchronous one-shot lifecycle. The host supplies a real main adapter;
 * the bridge neither loads a console executable nor implements game main.
 * No arbitrary initializer hook may skip the checked native replay. */
static inline int shyt_checked_boot_v448(ShytCrtV409 *crt,ShytCheckedBootV448 *p,
    const ShytCrtHooksV409 *host,void *context,int argc,char *const *argv,
    char *const *envp,int *status) {
    if(!p)return 0;
    p->result=SHYT_REPLAY_REFUSED;
    p->report=(ShytReplayReportV437){0};
    if(!host || !host->setup_environment || !host->main_entry ||
       !host->main_returned || !p->state || p->state->terminal || !p->rows ||
       !p->post || !p->sentinel || !p->count ||
       p->count>SHYT_CTOR_LIMIT_V427 || p->count!=p->expected_count)
        return 0;
    ShytBootBridgeV448 bridge={p,host,context};
    ShytCrtHooksV409 hooks={shyt_boot_env_v448,host->loader_shutdown,
        host->image_shutdown,shyt_boot_init_v448,shyt_boot_main_v448,
        shyt_boot_notify_v448};
    return shyt_crt_run_v409(crt,&hooks,&bridge,argc,argv,envp,status);
}
typedef struct {
    uint64_t entry,argv_address;
    size_t argv_capacity;
    int result,reason;
    int attempted;
} ShytBootMainV450;
typedef struct {
    ShytBootBridgeV448 bridge;
    ShytBootMainV450 *main;
} ShytAotBootV450;
static inline int shyt_aot_boot_env_v450(void *opaque,int argc,char *const *argv,
    char *const *envp) {
    ShytAotBootV450 *a=opaque;
    return shyt_boot_env_v448(&a->bridge,argc,argv,envp);
}
static inline int shyt_aot_boot_init_v450(void *opaque,ShytCrtV409 *crt) {
    ShytAotBootV450 *a=opaque;
    return shyt_boot_init_v448(&a->bridge,crt);
}
static inline void shyt_aot_boot_notify_v450(void *opaque,int status) {
    ShytAotBootV450 *a=opaque;
    shyt_boot_notify_v448(&a->bridge,status);
}
static inline int shyt_aot_boot_main_v450(void *opaque,ShytCrtV409 *crt,int argc,
    char *const *argv,int *status) {
    ShytAotBootV450 *a=opaque;
    ShytBootMainV450 *m=a->main;
    ShytCheckedBootV448 *p=a->bridge.plan;
    int32_t rc;
    (void)crt;
    m->attempted=1;
    m->result=shyt_startup_main_v449(p->state,m->entry,p->sentinel,argc,argv,
        m->argv_address,m->argv_capacity,&rc,&m->reason);
    if(m->result!=SHYT_V393_COMPLETED) {
        p->state->terminal=1;
        return 0;
    }
    *status=rc;
    return 1;
}

/* One synchronous path: ordered constructors, bound AOT main, cleanup.
 * No host main override. A stop and a negative main exit are distinct.
 * Inputs are trusted and immutable during the lifecycle. */
static inline int shyt_aot_boot_v450(ShytCrtV409 *crt,ShytCheckedBootV448 *p,
    ShytBootMainV450 *m,const ShytCrtHooksV409 *host,void *context,int argc,
    char *const *argv,char *const *envp,int *status) {
    if(m) {
        m->attempted=0;
        m->result=SHYT_V393_DENIED;
        m->reason=0;
    }
    if(!p)return 0;
    p->result=SHYT_REPLAY_REFUSED;
    p->report=(ShytReplayReportV437){0};
    if(!m || !host || !host->setup_environment || !host->main_returned ||
       !p->state || p->state->terminal || !p->rows || !p->post || !p->sentinel ||
       !p->count || p->count>SHYT_CTOR_LIMIT_V427 || p->count!=p->expected_count ||
       !m->entry || m->entry==p->sentinel || !m->argv_address ||
       !m->argv_capacity || m->argv_capacity>65536u || argc<0 || argc>64 ||
       !p->state->registry || !p->state->registry_count ||
       p->state->registry_count>SHYT_CTOR_REG_LIMIT_V427 ||
       !shyt_startup_find_v418(p->state->registry,p->state->registry_count,m->entry))
        return 0;
    ShytAotBootV450 a={{p,host,context},m};
    const ShytCrtHooksV409 hooks={shyt_aot_boot_env_v450,host->loader_shutdown,
        host->image_shutdown,shyt_aot_boot_init_v450,NULL,shyt_aot_boot_notify_v450};
    return shyt_crt_run_checked_v450(crt,&hooks,&a,argc,argv,envp,status,shyt_aot_boot_main_v450);
}
#endif
