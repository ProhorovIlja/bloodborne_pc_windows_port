/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <stddef.h>
#include <stdint.h>
#include <string.h>

struct startup_copy_v470 { size_t source, destination; };
/* Immutable pool, writable state, and ymm0 output must be disjoint host spans.
 * Offsets are pool/state-relative; original RIP addresses are never used here.
 * Only the opcode-verified one-, three- or four-pair constructor family is supported.
 * The caller owns all other guest registers, flags and control flow. */
int native_startup_copy_v470(const struct startup_copy_v470 *steps, size_t count,
    const unsigned char *pool, size_t pool_size, unsigned char *state, size_t state_size,
    unsigned char ymm0[32]) {
    if (!steps || !pool || !state || !ymm0 || (count != 1 && count != 3 && count != 4) ||
        pool_size < 16 || state_size < 16) return 0;
    for (size_t i=0; i<count; ++i) {
        if (steps[i].source > pool_size-16 || steps[i].destination > state_size-16 ||
            steps[i].source%16 || steps[i].destination%16) return 0;
    }
    for (size_t i=0; i<count; ++i)
        memcpy(state+steps[i].destination,pool+steps[i].source,16);
    memcpy(ymm0,pool+steps[count-1].source,16);
    memset(ymm0+16,0,16);
    return 1;
}

#ifdef STARTUP_COPY_V470_TEST
int main(void) {
    unsigned char pool[48], state[64], result[32], untouched[64];
    struct startup_copy_v470 steps[3]={{0,0},{16,16},{32,0}};
    for (size_t i=0;i<sizeof pool;++i) pool[i]=(unsigned char)i;
    memset(state,0xa5,sizeof state); memset(result,0x5a,sizeof result);
    memcpy(untouched,state,sizeof state);
    if (native_startup_copy_v470(steps,2,pool,sizeof pool,state,sizeof state,result)) return 1;
    steps[2].destination=SIZE_MAX;
    if (native_startup_copy_v470(steps,3,pool,sizeof pool,state,sizeof state,result) ||
        memcmp(state,untouched,sizeof state)) return 2;
    for (size_t i=0;i<sizeof result;++i) if (result[i]!=0x5a) return 3;
    steps[2].destination=0;
    if (!native_startup_copy_v470(steps,3,pool,sizeof pool,state,sizeof state,result) ||
        memcmp(state,pool+32,16) || memcmp(state+16,pool+16,16) ||
        memcmp(state+32,untouched+32,32) || memcmp(result,pool+32,16)) return 4;
    for (size_t i=16;i<sizeof result;++i) if (result[i]!=0) return 5;
    if (!native_startup_copy_v470(steps,1,pool,16,state,16,result) ||
        memcmp(state,pool,16) || memcmp(result,pool,16)) return 6;
    steps[0].source=1;
    if (native_startup_copy_v470(steps,1,pool,sizeof pool,state,sizeof state,result)) return 7;
    return 0;
}
#endif
