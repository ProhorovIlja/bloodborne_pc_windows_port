/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_verified_import_v395.h"
/* Uses the exact pinned public BbCpu physical ABI mirrored by V194.
 * No need to expose upstream generated rc.h in this module. */
#include "full_cpu_abi_v194.h"
#include <stdlib.h>
#include <string.h>
#define SHYT_V395_RAX 0u
#define SHYT_V395_RDX 2u
#define SHYT_V395_RSI 6u
#define SHYT_V395_RDI 7u
#define SHYT_V395_RSP 4u
static int valid_spec(const ShytNativeImportSpecV395 *s) {
    if(!s || !s->guest_target || !s->expected_next ||
       s->guest_target==s->expected_next)return 0;
    if(s->service==SHYT_V395_RETURN_VALUE)
        return s->recover_code==0;
    if(s->service==SHYT_V395_ADD_GUEST_QWORDS)
        return s->recover_code==0 && s->constant==0;
    if(s->service==SHYT_V395_COOPERATIVE_FAILURE)
        return s->recover_code>SHYT_V395_REC_GUEST_PERMISSIONS &&
               s->recover_code<32768 && s->constant==0;
    return 0;
}
int shyt_native_import_init_v395(ShytNativeImportRouterV395 *router,
                                  ShytNativeOsVmV388 *owner){
    if(!router || router->owner || router->count || router->sealed ||
       !owner || owner->initialized!=1 || owner->sealed!=1 ||
       owner->released)return 0;
    router->owner=owner;
    return 1;
}
int shyt_native_import_add_v395(ShytNativeImportRouterV395 *router,
    const ShytNativeImportSpecV395 *spec) {
    if(!router || !router->owner || router->sealed ||
       router->count>=SHYT_V395_MAX_IMPORTS || !valid_spec(spec))return 0;
    for(size_t i=0;i<router->count;i++)
        if(router->spec[i].guest_target==spec->guest_target)return 0;
    router->spec[router->count++]=*spec;
    return 1;
}
int shyt_native_import_seal_v395(ShytNativeImportRouterV395 *router) {
    if(!router || !router->owner || router->sealed || !router->count)
        return 0;
    /* insertion sort is sufficient for a MAX16 fixed import whitelist. */
    for(size_t i=1;i<router->count;i++) {
        ShytNativeImportSpecV395 item=router->spec[i];
        size_t j=i;
        while(j>0 && router->spec[j-1].guest_target>item.guest_target) {
            router->spec[j]=router->spec[j-1];
            --j;
        }
        router->spec[j]=item;
    }
    for(size_t i=1;i<router->count;i++)
        if(router->spec[i-1].guest_target>=router->spec[i].guest_target)
            return 0;
    router->sealed=1;
    return 1;
}
static const ShytNativeImportSpecV395 *lookup(
    const ShytNativeImportRouterV395 *router,uint64_t target) {
    size_t lo=0,hi=router->count;
    while(lo<hi) {
        size_t m=lo+(hi-lo)/2;
        if(router->spec[m].guest_target<target)lo=m+1;
        else hi=m;
    }
    return lo<router->count &&
           router->spec[lo].guest_target==target?&router->spec[lo]:NULL;
}
int shyt_native_import_spec_valid_v398(const ShytNativeImportSpecV395 *spec) {
    return valid_spec(spec);
}
void shyt_native_import_dispatch_site_v398(ShytNativeOsVmV388 *owner,
    const ShytNativeImportSpecV395 *s,BbCpu *cpu,
    uint64_t target,uint64_t next) {
    uint64_t sum=0,first=0,second=0,value=0;
    if(!owner || !cpu || !s || !valid_spec(s) ||
       owner->initialized!=1 || owner->sealed!=1 || owner->released ||
       shyt_generated_owner_v392()!=owner ||
       !shyt_generated_active_v390() ||
       !shyt_generated_recovery_depth_v393())abort();
    if(s->guest_target!=target)
        shyt_generated_raise_v393(SHYT_V395_REC_UNKNOWN);
    if(s->expected_next!=next)
        shyt_generated_raise_v393(SHYT_V395_REC_CONTINUATION);
    if(s->service==SHYT_V395_COOPERATIVE_FAILURE) {
        shyt_generated_raise_v393((int)s->recover_code);
    }
    if(s->service==SHYT_V395_RETURN_VALUE){
        value=s->constant;
    } else if(s->service==SHYT_V395_ADD_GUEST_QWORDS){
        /* Prescan every logical guest address before mutating a word.
         * Source reads are individually atomic, not a transaction. */
        if(!shyt_generated_try_probe_v390(cpu->r[SHYT_V395_RDI],8,
                                          SHYT_V386_READ) ||
           !shyt_generated_try_probe_v390(cpu->r[SHYT_V395_RSI],8,
                                          SHYT_V386_READ) ||
           !shyt_generated_try_probe_v390(cpu->r[SHYT_V395_RDX],8,
                                          SHYT_V386_WRITE))
            shyt_generated_raise_v393(SHYT_V395_REC_GUEST_PERMISSIONS);
        if(!shyt_generated_try_load_v390(
               cpu->r[SHYT_V395_RDI],8,&first) ||
           !shyt_generated_try_load_v390(
               cpu->r[SHYT_V395_RSI],8,&second))
            shyt_generated_raise_v393(SHYT_V395_REC_GUEST_PERMISSIONS);
        sum=first+second;
        if(!shyt_generated_try_store_v390(
               cpu->r[SHYT_V395_RDX],8,sum))
            shyt_generated_raise_v393(SHYT_V395_REC_GUEST_PERMISSIONS);
        value=sum;
    } else abort();
    /* The original generated CALL RAX/RET owns guest stack changes.
     * No raw host pointer or PS4 guest interpreter is entered. */
    cpu->r[SHYT_V395_RAX]=value;
    cpu->rip=next;
}
void shyt_native_import_dispatch_v395(ShytNativeImportRouterV395 *router,
    BbCpu *cpu,uint64_t target,uint64_t next) {
    const ShytNativeImportSpecV395 *s;
    if(!router || !router->sealed || !router->owner || !cpu ||
       shyt_generated_owner_v392()!=router->owner ||
       !shyt_generated_active_v390() ||
       !shyt_generated_recovery_depth_v393())abort();
    s=lookup(router,target);
    if(!s)shyt_generated_raise_v393(SHYT_V395_REC_UNKNOWN);
    shyt_native_import_dispatch_site_v398(router->owner,s,cpu,target,next);
}
