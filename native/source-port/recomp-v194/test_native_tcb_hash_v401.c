/* SPDX-License-Identifier: GPL-2.0-or-later
 * Host-only original-free portable decoded FS/GS hash proof.
 * Real upstream bbrecomp generated hash table equality is checked by
 * verify_tcb_hash_v401.py on separate invented ELF64 in Linux CI.
 */
#include "native_tcb_hash_v401.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define CHECK(x) do{if(!(x)){fprintf(stderr,"V401_ASSERT_LINE_%d\n",__LINE__);return 1;}}while(0)
int main(void) {
    static const uint8_t fs_rax_zero[10]=
        {0x64,0x48,0x8b,0x04,0x25,0,0,0,0,0xc3};
    static const uint8_t gs_rax_40[10]=
        {0x65,0x48,0x8b,0x04,0x25,0x40,0,0,0,0xc3};
    static const uint8_t fs_rbx_zero[10]=
        {0x64,0x48,0x8b,0x1c,0x25,0,0,0,0,0xc3};
    static const uint8_t fs_rax_40[10]=
        {0x64,0x48,0x8b,0x04,0x25,0x40,0,0,0,0xc3};
    static const uint8_t gs_rbx_40[10]=
        {0x65,0x48,0x8b,0x1c,0x25,0x40,0,0,0,0xc3};
    static const uint64_t expected[5]={
        UINT64_C(0xa2827e1bb306bdc9),
        UINT64_C(0xa2827e1bb306bdc9),
        UINT64_C(0xa28cae1bb30f63de),
        UINT64_C(0x844cf2c7d6d2b746),
        UINT64_C(0xa28cae1bb30f63de)
    };
    static const uint8_t *const probes[5]={
        fs_rax_zero,gs_rax_40,fs_rbx_zero,fs_rax_40,gs_rbx_40
    };
    for(size_t i=0;i<5;i++){
        uint64_t got=0;
        CHECK(shyt_native_hash_tcb_probe_v401(probes[i],10,&got));
        CHECK(got==expected[i]);
    }
    /* GS with arbitrary absolute disp still normalizes, as the
     * actual bbcpu guest TCB decoder does. */
    uint8_t mutable_rax[10];
    memcpy(mutable_rax,gs_rax_40,sizeof mutable_rax);
    mutable_rax[5]=0xab;mutable_rax[6]=0xcd;
    uint64_t got=0;
    CHECK(shyt_native_hash_tcb_probe_v401(mutable_rax,10,&got));
    CHECK(got==expected[1]);
    memcpy(mutable_rax,fs_rax_40,sizeof mutable_rax);
    mutable_rax[5]=0; /* only FS:[0] is normalized */
    CHECK(shyt_native_hash_tcb_probe_v401(mutable_rax,10,&got));
    CHECK(got==expected[0]);
    mutable_rax[0]=0x66;
    CHECK(!shyt_native_hash_tcb_probe_v401(mutable_rax,10,&got));
    CHECK(!shyt_native_hash_tcb_probe_v401(fs_rax_zero,9,&got));
    CHECK(!shyt_native_hash_tcb_probe_v401(NULL,10,&got));
    CHECK(!shyt_native_hash_tcb_probe_v401(fs_rax_zero,10,NULL));
    memcpy(mutable_rax,gs_rax_40,sizeof mutable_rax);
    mutable_rax[3]=0x3c; /* unsupported destination register */
    CHECK(!shyt_native_hash_tcb_probe_v401(mutable_rax,10,&got));
    memcpy(mutable_rax,gs_rax_40,sizeof mutable_rax);
    mutable_rax[4]=0x24; /* unsupported SIB base or index */
    CHECK(!shyt_native_hash_tcb_probe_v401(mutable_rax,10,&got));
    memcpy(mutable_rax,gs_rax_40,sizeof mutable_rax);
    mutable_rax[9]=0x90; /* not a matched second RET instruction */
    CHECK(!shyt_native_hash_tcb_probe_v401(mutable_rax,10,&got));
    puts("NATIVE_V401_PORTABLE_FS_GS_DECODED_TCB_HASH_PASS");
    puts("Five invented TCB/negative code fixtures; NOT original Bloodborne 1.09.");
    return 0;
}
