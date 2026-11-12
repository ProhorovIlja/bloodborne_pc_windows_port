/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "native_tcb_hash_v401.h"
/* Only two decoded source registers are in the test fixture. The
 * public pinned bbcpu decoder derives reg from ZydisRegisterGetId:
 * RAX index 0, RBX index 3. Does not attempt general x86 decoding. */
static uint64_t mix(uint64_t h,uint8_t byte) {
    return (h ^ (uint64_t)byte) * UINT64_C(0x100000001b3);
}
int shyt_native_hash_tcb_probe_v401(const uint8_t *code,size_t n,
                                     uint64_t *out){
    if(!code || !out || n!=10 || (code[0]!=0x64u && code[0]!=0x65u) ||
       code[1]!=0x48u || code[2]!=0x8bu ||
       (code[3]!=0x04u && code[3]!=0x1cu) ||
       code[4]!=0x25u || code[9]!=0xc3u)return 0;
    uint32_t disp=(uint32_t)code[5]|
         ((uint32_t)code[6]<<8)|((uint32_t)code[7]<<16)|
         ((uint32_t)code[8]<<24);
    uint64_t h=UINT64_C(0xcbf29ce484222325);
    if(code[0]==0x65u || disp==0u) {
        h=mix(h,0xf5u);
        h=mix(h,code[3]==0x04u?0u:3u);
        h=mix(h,0xc3u); /* second decoded instruction RET */
    } else {
        /* FS nonzero displacement is NOT the special TCB load:
         * pinned bbcpu hashes every original instruction byte. */
        for(size_t i=0;i<n;i++)h=mix(h,code[i]);
    }
    *out=h;
    return 1;
}
