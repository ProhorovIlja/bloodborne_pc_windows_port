/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef SHYT_STARTUP_CTOR_PLAN_V427_H
#define SHYT_STARTUP_CTOR_PLAN_V427_H
#include "native_startup_call_v418.h"

enum { SHYT_CTOR_LIMIT_V427=65536, SHYT_CTOR_REG_LIMIT_V427=1000000 };
typedef struct { unsigned ordinal; uint64_t id; } ShytCtorRowV427;

/* Preserve retail execution order, including repeated target IDs. The
 * caller retains immutable, disjoint rows/registry/output arrays during
 * startup. Preflight the whole requested range before writing any output.
 * This resolves native pointers; it does not invoke or attest functions. */
static inline int shyt_ctor_prepare_v427(const ShytCtorRowV427 *rows,size_t n,
    unsigned first,const RcFunction *table,size_t count,RcFn *out,size_t capacity) {
    if(!rows || !table || !out || !first || first>SHYT_CTOR_LIMIT_V427 ||
       !n || n>SHYT_CTOR_LIMIT_V427-first+1u || n>capacity ||
       !count || count>SHYT_CTOR_REG_LIMIT_V427)return 0;
    for(size_t i=0;i<count;++i)
        if(!table[i].fn || (i && table[i-1].offset>=table[i].offset))return 0;
    for(size_t i=0;i<n;++i)
        if(rows[i].ordinal!=first+i || !rows[i].id ||
           !shyt_startup_find_v418(table,count,rows[i].id))return 0;
    for(size_t i=0;i<n;++i)out[i]=shyt_startup_find_v418(table,count,rows[i].id);
    return 1;
}
#endif
