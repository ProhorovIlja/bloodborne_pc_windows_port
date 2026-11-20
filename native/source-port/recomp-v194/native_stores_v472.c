/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <stddef.h>
#include <stdint.h>
#include <string.h>

struct store_v472 { size_t dst, src; uint32_t immediate; unsigned width; };
/* Buffers and plan must be disjoint host spans. rax_id is a normalized guest
 * address (zero means unchanged); never a host pointer. Only RAX and YMM0
 * are outputs; FLAGS, other registers and control flow belong to the caller. */
int native_stores_v472(const struct store_v472 *ops, size_t n,
    const unsigned char *pool, size_t pn, unsigned char *data, size_t dn,
    uint64_t rax_id, uint64_t *rax, unsigned char ymm[32]) {
    if (!ops || !pool || !data || !rax || !ymm || (n!=1 && n!=4 && n!=6) || pn<16) return 0;
    size_t last = 0;
    if (ops[0].width!=16) return 0;
    for (size_t i=0;i<n;i++) {
        const struct store_v472 *s=ops+i;
        const unsigned w=s->width;
        if ((w!=16 && w!=2 && w!=4) || w>dn || s->dst>dn-w ||
            (w==16 && (s->src>pn-16 || s->src%16 || s->dst%16)) ||
            (w!=16 && (i+1!=n || (w==2 && s->immediate>UINT16_MAX)))) return 0;
        if (w==16) last=s->src;
    }
    for (size_t i=0;i<n;i++) {
        const struct store_v472 *s=ops+i;
        if (s->width==16) memcpy(data+s->dst,pool+s->src,16);
        else for (unsigned j=0;j<s->width;j++) data[s->dst+j]=(unsigned char)(s->immediate>>(8*j));
    }
    memcpy(ymm,pool+last,16); memset(ymm+16,0,16);
    if (rax_id) *rax=rax_id;
    return 1;
}

#ifdef TEST_V472
int main(void) {
    const unsigned char pool[16]={90};
    unsigned char data[51], ymm[32];
    struct store_v472 ops[]={{0,0,0,16},{16,0,0,16},{32,0,0,16},{49,0,0xaabbccdd,2}};
    uint64_t rax=123;
    memset(data,7,sizeof data); memset(ymm,9,sizeof ymm);
    if (native_stores_v472(ops,4,pool,16,data,51,321,&rax,ymm) || rax!=123 || ymm[0]!=9 || data[0]!=7) return 1;
    ops[3].immediate=0xccdd;
    if (!native_stores_v472(ops,4,pool,16,data,51,321,&rax,ymm) || rax!=321 ||
        data[0]!=90 || data[16]!=90 || data[32]!=90 || data[48]!=7 || data[49]!=0xdd || data[50]!=0xcc || ymm[0]!=90) return 2;
    for (unsigned i=16;i<32;i++) if (ymm[i]) return 3;
    ops[3].dst=50;
    if (native_stores_v472(ops,4,pool,16,data,51,1,&rax,ymm) || rax!=321) return 4;
    return 0;
}
#endif
