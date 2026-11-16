/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <stddef.h>
#include <stdint.h>
#include <string.h>

#include "ro_v477.h"

/* Caller retains immutable and disjoint buffers, and zeroes the view before
 * binding. Guest addresses are lookup keys, not native pointers. */
int bb_ro_bind_v476(struct bb_ro_v476 *v, const struct bb_ro_row_v476 *rows,
    size_t count, const unsigned char *pool, size_t size) {
    if (!v || v->count || v->rows || v->pool || !rows || !pool || !count || count>65536 ||
        !size || size>4194304) return 0;
    uint64_t prev=0;
    size_t offset=0;
    for (size_t i=0;i<count;++i) {
        const struct bb_ro_row_v476 *r=rows+i;
        if (r->address<prev || !r->length || r->length>UINT64_MAX-r->address ||
            r->offset!=offset || r->length>size-offset) return 0;
        prev=r->address+r->length;
        offset+=r->length;
    }
    if (offset!=size) return 0;
    *v=(struct bb_ro_v476){rows,pool,count};
    return 1;
}

static const struct bb_ro_row_v476 *find(const struct bb_ro_v476 *v, uint64_t address) {
    if (!v || !v->rows || !v->pool || !v->count) return NULL;
    size_t lo=0,hi=v->count;
    while (lo<hi) {
        size_t mid=lo+(hi-lo)/2;
        if (v->rows[mid].address<=address) lo=mid+1; else hi=mid;
    }
    if (!lo || address-v->rows[lo-1].address>=v->rows[lo-1].length) return NULL;
    return v->rows+lo-1;
}

int bb_ro_read_v476(const struct bb_ro_v476 *v, uint64_t address, void *out, size_t n) {
    const struct bb_ro_row_v476 *r=find(v,address);
    if (!r || !out || !n) return 0;
    size_t delta=(size_t)(address-r->address);
    if (n>r->length-delta) return 0;
    memcpy(out,v->pool+r->offset+delta,n);
    return 1;
}

/* For attested immutable strings only; this is not a general guest strlen. */
int bb_ro_strlen_v476(const struct bb_ro_v476 *v, uint64_t address, size_t *length) {
    const struct bb_ro_row_v476 *r=find(v,address);
    if (!r || !length) return 0;
    size_t delta=(size_t)(address-r->address);
    const unsigned char *p=v->pool+r->offset+delta;
    const unsigned char *end=memchr(p,0,r->length-delta);
    if (!end) return 0;
    *length=(size_t)(end-p);
    return 1;
}

int bb_ro_offset_v477(const struct bb_ro_v476 *v, uint64_t address, size_t n, size_t *offset) {
    const struct bb_ro_row_v476 *r=find(v,address);
    if (!r || !offset || !n) return 0;
    size_t delta=(size_t)(address-r->address);
    if (n>r->length-delta) return 0;
    *offset=r->offset+delta;
    return 1;
}

/* Bytewise UTF-16LE terminator scan. Length in code units, not code points. */
int bb_ro_u16len_v477(const struct bb_ro_v476 *v, uint64_t address, size_t *length) {
    const struct bb_ro_row_v476 *r=find(v,address);
    if (!r || !length || address%2) return 0;
    size_t delta=(size_t)(address-r->address);
    const unsigned char *p=v->pool+r->offset+delta;
    for (size_t i=0;i<(r->length-delta)/2;++i)
        if (!p[2*i] && !p[2*i+1]) { *length=i; return 1; }
    return 0;
}
