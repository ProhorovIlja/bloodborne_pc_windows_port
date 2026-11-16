/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Owner-local comparison of the generated dispatchers, not a game runner. */
#include <inttypes.h>
#include <stdio.h>
#include <string.h>
#define BB_ENABLE_V488 1
#include "dispatch_v493.c"
#include "dispatch_v487.c"

#define COUNT(a) (sizeof(a)/sizeof((a)[0]))

static uint64_t draw(uint64_t *seed) {
    *seed=*seed*UINT64_C(6364136223846793005)+1;
    return *seed;
}

static void hash_word(uint64_t *hash,uint64_t x) {
    for(unsigned i=0;i<8;++i){
        *hash^=(unsigned char)(x>>(8*i));
        *hash*=UINT64_C(1099511628211);
    }
}

struct stats {
    uint64_t calls,hash;
};

static int compare(uint64_t id,uint64_t disp,unsigned tag,struct stats *st) {
    const uint64_t base=UINT64_C(0x100000000);
    uint64_t seed=id^UINT64_C(0xbb495);
    for(unsigned i=0;i<16;++i) {
        unsigned char a[32],b[32];
        for(size_t j=0;j<COUNT(a);++j) a[j]=(unsigned char)(draw(&seed)>>56);
        memcpy(b,a,sizeof a);
        const struct bb_region_v478 ra={base,sizeof a,a},rb={base,sizeof b,b};
        const struct bb_write_region_v492 wa={base,sizeof a,a},wb={base,sizeof b,b};
        struct bb_input_v487 in;
        in.rax=draw(&seed);
        in.rcx=draw(&seed);
        in.rdx=draw(&seed);
        in.rsi=draw(&seed);
        in.rdi=(i<12?base+i:base+sizeof a)-disp;
        in.flags=draw(&seed);
        struct bb_result_v484 x={1,2,3},y=x;
        const int read=(i&3)!=1,write=(i&3)!=2;
        const enum bb_status_v492 s=bb_dispatch_v492(id,&in,read?&ra:NULL,write?&wa:NULL,&x);
        const enum bb_status_v492 t=bb_dispatch_v493(id,&in,read?&rb:NULL,write?&wb:NULL,&y);
        const enum bb_status_v492 expected=tag==4?BB_MISS_V492:
            tag==1&&(!read||i>=12)?BB_READ_DENIED_V492:
            tag==3&&(!write||i>=12)?BB_WRITE_DENIED_V492:BB_OK_V492;
        if(s!=expected||t!=expected||x.rax!=y.rax||x.flags!=y.flags||
           x.flags_valid!=y.flags_valid||memcmp(a,b,sizeof a)) return 0;
        if(t!=BB_OK_V492&&(y.rax!=1||y.flags!=2||y.flags_valid!=3))return 0;
        /* Verify that neither dispatcher modified memory on a miss or a
         * non-store. Reproduce the initial bytes independently of both. */
        if(t!=BB_OK_V492||tag!=3) {
            uint64_t orig=id^UINT64_C(0xbb495);
            for(size_t j=0;j<COUNT(a);++j)
                if(b[j]!=(unsigned char)(draw(&orig)>>56))return 0;
        }
        ++st->calls;
        hash_word(&st->hash,(uint64_t)t);
        hash_word(&st->hash,y.rax);
        hash_word(&st->hash,y.flags&y.flags_valid);
        hash_word(&st->hash,y.flags_valid);
        for(size_t j=0;j<COUNT(b);++j)hash_word(&st->hash,b[j]);
    }
    return 1;
}

int main(void) {
    struct stats st={0,UINT64_C(14695981039346656037)};
    const size_t entries=COUNT(table)+COUNT(memory_routes)+COUNT(alu_rows_v493)+COUNT(stores);
    if(entries!=COUNT(bb_ids_v493)||entries!=COUNT(bb_routes_v493))goto fail;
    /* Walk independently emitted family tables, not the index under test.
     * Resolve memory alias targets using the legacy exact-ID relation. */
    for(size_t j=0;j<COUNT(table);++j)
        if(!compare(table[j].id,0,0,&st))goto fail;
    for(size_t j=0;j<COUNT(memory_routes);++j){
        size_t lo=0,hi=COUNT(load_rows_v493);
        const uint64_t t=memory_routes[j].target;
        while(lo<hi){size_t m=lo+(hi-lo)/2;if(load_rows_v493[m].id<t)lo=m+1;else hi=m;}
        if(lo==COUNT(load_rows_v493)||load_rows_v493[lo].id!=t||
           !compare(memory_routes[j].id,load_rows_v493[lo].disp,1,&st))goto fail;
    }
    for(size_t j=0;j<COUNT(alu_rows_v493);++j)
        if(!compare(alu_rows_v493[j].id,0,2,&st))goto fail;
    for(size_t j=0;j<COUNT(stores);++j)
        if(!compare(stores[j].id,stores[j].disp,3,&st))goto fail;
    uint64_t misses=0;
    for(size_t j=1;j<entries&&misses<256;++j)
        if((uint64_t)bb_ids_v493[j]-bb_ids_v493[j-1]>1) {
            if(!compare((uint64_t)bb_ids_v493[j-1]+1,0,4,&st))goto fail;
            ++misses;
        }
    if(bb_ids_v493[0]>0) {
        if(!compare(0,0,4,&st))goto fail;
        ++misses;
    }
    const uint64_t final_id=bb_ids_v493[entries-1];
    if(final_id<UINT64_MAX) {
        if(!compare(UINT64_MAX,0,4,&st))goto fail;
        ++misses;
    }
    printf("{\"entries\":%zu,\"miss_ids\":%" PRIu64 ",\"calls\":%" PRIu64
           ",\"fingerprint\":\"%016" PRIx64 "\"}\n",entries,misses,st.calls,st.hash);
    return 0;
fail:
    fputs("V495 indexed dispatcher comparison failed\n",stderr);
    return 1;
}
