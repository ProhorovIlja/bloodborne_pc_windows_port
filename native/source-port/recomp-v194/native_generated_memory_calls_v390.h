/* SPDX-License-Identifier: GPL-2.0-or-later
 * V390: include ONLY AFTER pinned real upstream "recomp/rc.h".
 * The macros replace named memory call sites in genuine generated C
 * WITHOUT editing upstream ABI or accidentally intercepting rc.h itself.
 */
#ifndef SHYT_GENERATED_MEMORY_CALLS_V390_H
#define SHYT_GENERATED_MEMORY_CALLS_V390_H
#ifndef BB_RECOMP_API_VERSION
#error "Include pinned real recomp/rc.h BEFORE V390 memory calls"
#endif
#include "native_generated_memory_v390.h"
#include <stdlib.h>
#include <string.h>

static inline BbVec shyt_generated_vld_v390(uint64_t addr,int bytes){
    BbVec value;
    memset(&value,0,sizeof(value));
    if(bytes<=0 || (size_t)bytes>sizeof(value.b) ||
       (bytes!=1 && bytes!=2 && bytes!=4 && bytes!=8 &&
        bytes!=16 && bytes!=32) ||
       !shyt_generated_try_probe_v390(
           addr,(size_t)bytes,SHYT_V386_READ))abort();
    for(int i=0;i<bytes;i+=8){
        const int chunk=bytes-i>=8?8:bytes-i;
        const uint64_t word=shyt_generated_ld_v390(
            addr+(uint64_t)i,chunk);
        memcpy(value.b+i,&word,(size_t)chunk);
    }
    return value;
}
static inline void shyt_generated_vst_v390(
    uint64_t addr,int bytes,BbVec value) {
    if(bytes<=0 || (size_t)bytes>sizeof(value.b) ||
       (bytes!=1 && bytes!=2 && bytes!=4 && bytes!=8 &&
        bytes!=16 && bytes!=32) ||
       !shyt_generated_try_probe_v390(
           addr,(size_t)bytes,SHYT_V386_WRITE))abort();
    /* Entire region permission and span validation before any writes.
     * Multiple chunks are NOT one atomic x86 SIMD transaction. */
    for(int i=0;i<bytes;i+=8){
        const int chunk=bytes-i>=8?8:bytes-i;
        uint64_t word=0;
        memcpy(&word,value.b+i,(size_t)chunk);
        shyt_generated_st_v390(addr+(uint64_t)i,chunk,word);
    }
}
#define rc_ld(addr,bytes) shyt_generated_ld_v390((addr),(bytes))
#define rc_lds(addr,bytes) shyt_generated_ld_v390((addr),(bytes))
#define rc_st(addr,bytes,value) shyt_generated_st_v390((addr),(bytes),(value))
#define rc_sts(addr,bytes,value) shyt_generated_st_v390((addr),(bytes),(value))
#define rc_cas(addr,bytes,expected,desired,seen) \
  shyt_generated_cas_v390((addr),(bytes),(expected),(desired),(seen))
#define rc_vld(addr,bytes) shyt_generated_vld_v390((addr),(bytes))
#define rc_vst(addr,bytes,value) shyt_generated_vst_v390((addr),(bytes),(value))
#endif
