/* SPDX-License-Identifier: GPL-2.0-or-later
 * Single-controller startup direct-memory bookkeeping. Offsets are not
 * pointers. Native storage/protection is supplied by an explicit backend.
 * No implicit aliasing, fixed mappings, GPU permissions or partial release.
 */
#ifndef SHYT_NATIVE_DIRECT_MEMORY_V411_H
#define SHYT_NATIVE_DIRECT_MEMORY_V411_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>
enum { SHYT_DM_PAGE=16384, SHYT_DM_MAX=256 };
enum ShytDmResult { SHYT_DM_OK, SHYT_DM_INVALID, SHYT_DM_NO_SPACE,
                    SHYT_DM_UNSUPPORTED, SHYT_DM_BACKEND_FAILED };
typedef struct {
    uint64_t offset, length;
    int type;
    void *mapping;
    void *backend_context;
    int (*unmap)(void *,void *,uint64_t);
} ShytDmBlock;
typedef struct {
    uint64_t limit;
    size_t count;
    ShytDmBlock blocks[SHYT_DM_MAX];
} ShytDmPool;
typedef struct {
    void *context;
    /* On success return a live allocation of length bytes, aligned to
     * alignment. On failure return NULL without leaving a mapping. */
    void *(*map)(void *,uint64_t,uint64_t,uint64_t,int,unsigned);
    /* On failure leave the mapping intact; no callbacks may reenter. */
    int (*unmap)(void *,void *,uint64_t);
} ShytDmBackend;
static inline int shyt_dm_init(ShytDmPool *p,uint64_t limit) {
    if(!p || p->limit || p->count || !limit || limit>INT64_MAX ||
       limit%SHYT_DM_PAGE)return 0;
    p->limit=limit;
    return 1;
}
static inline int shyt_dm_align(uint64_t a,uint64_t align,uint64_t *out) {
    const uint64_t r=a%align;
    const uint64_t add=r?align-r:0;
    if(a>UINT64_MAX-add)return 0;
    *out=a+add;
    return 1;
}
static inline enum ShytDmResult shyt_dm_allocate(ShytDmPool *p,int64_t lo,
    int64_t hi,uint64_t length,uint64_t align,int type,uint64_t *out) {
    if(!p || !p->limit || !out || lo<0 || hi<0 || !length ||
       length%SHYT_DM_PAGE || align%SHYT_DM_PAGE || type<0 || type>10)
        return SHYT_DM_INVALID;
    if(!align)align=SHYT_DM_PAGE;
    const uint64_t end=(uint64_t)hi<p->limit?(uint64_t)hi:p->limit;
    uint64_t start=(uint64_t)lo;
    if(p->count>=SHYT_DM_MAX)return SHYT_DM_NO_SPACE;
    for(size_t i=0;i<=p->count;++i) {
        const uint64_t stop=i==p->count || p->blocks[i].offset>end ?
                            end:p->blocks[i].offset;
        uint64_t at;
        if(!shyt_dm_align(start,align,&at) || at>end)break;
        if(at<=stop && length<=stop-at) {
            memmove(&p->blocks[i+1],&p->blocks[i],
                    (p->count-i)*sizeof(p->blocks[0]));
            p->blocks[i]=(ShytDmBlock){at,length,type,NULL,NULL,NULL};
            ++p->count;
            *out=at;
            return SHYT_DM_OK;
        }
        if(i==p->count || stop==end)break;
        const uint64_t next=p->blocks[i].offset+p->blocks[i].length;
        if(next>start)start=next;
    }
    return SHYT_DM_NO_SPACE;
}
static inline size_t shyt_dm_find(const ShytDmPool *p,uint64_t off,uint64_t len) {
    for(size_t i=0;i<p->count;++i)
        if(p->blocks[i].offset==off && p->blocks[i].length==len)return i;
    return p->count;
}
static inline enum ShytDmResult shyt_dm_map(ShytDmPool *p,const ShytDmBackend *b,
    uint64_t off,uint64_t len,uint64_t align,unsigned protection,
    unsigned flags,void **out) {
    if(!p || !p->limit || !b || !b->map || !b->unmap || !out ||
       !len || len%SHYT_DM_PAGE || off%SHYT_DM_PAGE || align%SHYT_DM_PAGE)
        return SHYT_DM_INVALID;
    if(flags || protection!=3)return SHYT_DM_UNSUPPORTED;
    if(!align)align=SHYT_DM_PAGE;
    const size_t i=shyt_dm_find(p,off,len);
    if(i==p->count || p->blocks[i].mapping)return SHYT_DM_UNSUPPORTED;
    void *ptr=b->map(b->context,off,len,align,p->blocks[i].type,protection);
    if(!ptr)return SHYT_DM_BACKEND_FAILED;
    p->blocks[i].mapping=ptr;
    p->blocks[i].backend_context=b->context;
    p->blocks[i].unmap=b->unmap;
    *out=ptr;
    return SHYT_DM_OK;
}
static inline enum ShytDmResult shyt_dm_release(ShytDmPool *p,
    uint64_t off,uint64_t len) {
    if(!p || !p->limit || off%SHYT_DM_PAGE || len%SHYT_DM_PAGE)
        return SHYT_DM_INVALID;
    if(!len)return SHYT_DM_OK;
    const size_t i=shyt_dm_find(p,off,len);
    if(i==p->count)return SHYT_DM_UNSUPPORTED;
    void *ptr=p->blocks[i].mapping;
    if(ptr && !p->blocks[i].unmap(p->blocks[i].backend_context,ptr,len))
        return SHYT_DM_BACKEND_FAILED;
    --p->count;
    memmove(&p->blocks[i],&p->blocks[i+1],
            (p->count-i)*sizeof(p->blocks[0]));
    p->blocks[p->count]=(ShytDmBlock){0};
    return SHYT_DM_OK;
}
#endif
