/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_STARTUP_TRANSACTION_V547_H
#define BB_STARTUP_TRANSACTION_V547_H
#include <stddef.h>
#include <stdint.h>

enum bb_transaction_kind_v547 { BB_TX_INVALID, BB_TX_REPORT, BB_TX_TRANSFER };
struct bb_transaction_v547 { enum bb_transaction_kind_v547 kind; uint64_t argument; unsigned value; };
/* Signed TLS displacement, including INT64_MIN. Bounds are guest offsets;
 * never read the host thread pointer or pass guest storage to host longjmp. */
static inline int bb_tls_slot_v547(size_t n,size_t tp,int64_t delta,size_t bytes,size_t *out) {
    const uint64_t mag=delta<0?UINT64_C(0)-(uint64_t)delta:(uint64_t)delta;
    if (tp>n || mag>(delta<0?tp:n-tp)) return 0;
    const size_t at=delta<0?tp-(size_t)mag:tp+(size_t)mag;
    if (bytes>n-at) return 0;
    *out=at;
    return 1;
}
static inline int bb_tls_mark_v547(unsigned char *data,size_t n,size_t tp,
        int64_t delta,uint64_t file) {
    size_t at;
    if (!data || !file || !bb_tls_slot_v547(n,tp,delta,12,&at)) return 0;
    for (unsigned i=0;i<8;++i) data[at+i]=(unsigned char)(file>>(8*i));
    data[at+8]=0xfb; data[at+9]=0; data[at+10]=0; data[at+11]=0;
    return 1;
}
static inline struct bb_transaction_v547 bb_tls_oom_v547(const unsigned char *data,
        size_t n,uint64_t base,size_t tp,int64_t active,int64_t jump) {
    size_t at;
    const struct bb_transaction_v547 bad={BB_TX_INVALID,0,0};
    if (!data || n>UINT64_MAX-base || !bb_tls_slot_v547(n,tp,active,4,&at)) return bad;
    if (!(data[at]|data[at+1]|data[at+2]|data[at+3]))
        return (struct bb_transaction_v547){BB_TX_REPORT,0,0x109};
    if (!bb_tls_slot_v547(n,tp,jump,1,&at) || !(base+at)) return bad;
    /* This only describes the target. A startup driver must stop unless a
     * separately validated nonlocal-transfer mechanism owns the buffer. */
    return (struct bb_transaction_v547){BB_TX_TRANSFER,base+at,1};
}
#endif
