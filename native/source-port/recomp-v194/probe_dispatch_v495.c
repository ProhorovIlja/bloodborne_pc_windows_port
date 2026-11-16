/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Owner-local comparison of the generated dispatchers, not a game runner. */
#include <inttypes.h>
#include <stdio.h>
#include <string.h>
#define BB_ENABLE_V488 1
#include "dispatch_v493.c"
#define BB_REUSE_MEMORY_ROUTES_V517
#include "dispatch_v487.c"
#undef BB_REUSE_MEMORY_ROUTES_V517

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

static int compare(uint64_t id,uint64_t disp,unsigned tag,unsigned width,
                   const struct store_v491 *store,struct stats *st) {
    if(width!=1&&width!=2&&width!=4&&width!=8) {
        fputs("V495 invalid access width\n",stderr);
        return 0;
    }
    const uint64_t base=UINT64_C(0x100000000);
    uint64_t seed=id^UINT64_C(0xbb495);
    for(unsigned i=0;i<16;++i) {
        unsigned char a[32],b[32],expected_bytes[32];
        for(size_t j=0;j<COUNT(expected_bytes);++j) expected_bytes[j]=(unsigned char)(draw(&seed)>>56);
        memcpy(a,expected_bytes,sizeof a);
        memcpy(b,expected_bytes,sizeof b);
        const struct bb_region_v478 ra={base,sizeof a,a},rb={base,sizeof b,b};
        const struct bb_write_region_v492 wa={base,sizeof a,a},wb={base,sizeof b,b};
        struct bb_input_v487 in;
        in.rax=draw(&seed);
        in.rcx=draw(&seed);
        in.rdx=draw(&seed);
        in.rsi=draw(&seed);
        const size_t offset=i<10?i:i==10?sizeof a-width:
            i==11?sizeof a-width+1:sizeof a;
        in.rdi=(base+offset)-disp;
        in.flags=draw(&seed);
        struct bb_result_v484 x={1,2,3},y=x;
        const int read=(i&3)!=1,write=(i&3)!=2;
        const enum bb_status_v492 s=bb_dispatch_v492(id,&in,read?&ra:NULL,write?&wa:NULL,&x);
#ifdef BB_WITH_RIP_V497
        const enum bb_status_v492 t=bb_dispatch_v497(id,&in,read?&rb:NULL,write?&wb:NULL,base,&y);
#else
        const enum bb_status_v492 t=bb_dispatch_v493(id,&in,read?&rb:NULL,write?&wb:NULL,&y);
#endif
        const enum bb_status_v492 expected=tag==4?BB_MISS_V492:
            tag==1&&(!read||offset>sizeof a-width)?BB_READ_DENIED_V492:
            tag==3&&(!write||offset>sizeof a-width)?BB_WRITE_DENIED_V492:BB_OK_V492;
        if(s!=expected||t!=expected||x.rax!=y.rax||x.flags!=y.flags||
           x.flags_valid!=y.flags_valid||memcmp(a,b,sizeof a)) {
            fprintf(stderr,"V495 mismatch family=%u case=%u legacy=%d indexed=%d expected=%d\n",
                    tag,i,(int)s,(int)t,(int)expected);
            return 0;
        }
        if(t!=BB_OK_V492&&(y.rax!=1||y.flags!=2||y.flags_valid!=3)) {
            fprintf(stderr,"V495 result changed on denial: family=%u case=%u\n",tag,i);
            return 0;
        }
        if(t==BB_OK_V492&&tag==3) {
            uint64_t value;
            switch(store->source) {
            case 0: value=store->value;break;
            case 1: value=in.rcx;break;
            case 2: value=in.rdx;break;
            case 6: value=in.rsi;break;
            case 7: value=in.rdi;break;
            default: fputs("V495 invalid store source\n",stderr);return 0;
            }
            for(unsigned j=0;j<width;++j)expected_bytes[offset+j]=(unsigned char)(value>>(8*j));
        }
        if(memcmp(expected_bytes,b,sizeof b)) {
            fprintf(stderr,"V495 unexpected memory effect: family=%u case=%u\n",tag,i);
            return 0;
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
    size_t entries=COUNT(table)+COUNT(memory_routes)+COUNT(alu_rows_v493)+COUNT(stores);
#ifdef BB_WITH_RIP_V497
    entries+=COUNT(rip_rows_v496);
#endif
    if(entries!=COUNT(bb_ids_v493)||entries!=COUNT(bb_routes_v493)) {
        fputs("V495 family and index counts disagree\n",stderr);
        goto fail;
    }
    /* Walk independently emitted family tables, not the index under test.
     * Resolve memory alias targets using the legacy exact-ID relation. */
    for(size_t j=0;j<COUNT(table);++j)
        if(!compare(table[j].id,0,0,1,NULL,&st))goto fail;
    for(size_t j=0;j<COUNT(memory_routes);++j){
        size_t lo=0,hi=COUNT(load_rows_v493);
        const uint64_t t=memory_routes[j].target;
        while(lo<hi){size_t m=lo+(hi-lo)/2;if(load_rows_v493[m].id<t)lo=m+1;else hi=m;}
        if(lo==COUNT(load_rows_v493)||load_rows_v493[lo].id!=t) {
            fputs("V495 memory route has no terminal row\n",stderr);
            goto fail;
        }
        if(!compare(memory_routes[j].id,load_rows_v493[lo].disp,1,load_rows_v493[lo].width,NULL,&st))goto fail;
    }
    for(size_t j=0;j<COUNT(alu_rows_v493);++j)
        if(!compare(alu_rows_v493[j].id,0,2,1,NULL,&st))goto fail;
    for(size_t j=0;j<COUNT(stores);++j)
        if(!compare(stores[j].id,stores[j].disp,3,stores[j].width,stores+j,&st))goto fail;
#ifdef BB_WITH_RIP_V497
    for(size_t j=0;j<COUNT(rip_rows_v496);++j) {
        const uint64_t target=rip_rows_v496[j].target,id=rip_rows_v496[j].id;
        uint64_t seed=id;
        for(unsigned i=0;i<16;++i) {
            const uint64_t flags=draw(&seed);
            const uint64_t slide=i==0?0:i==1?UINT64_MAX-target:i==2?UINT64_MAX:draw(&seed);
            const int overflow=slide>UINT64_MAX-target;
            const struct bb_input_v487 in={.flags=flags};
            struct bb_result_v484 out={1,2,3};
            const enum bb_status_v492 status=bb_dispatch_v497(id,&in,NULL,NULL,slide,&out);
            if(overflow ? (status!=BB_ADDRESS_DENIED_V497||out.rax!=1||out.flags!=2||out.flags_valid!=3)
                        : (status!=BB_OK_V492||out.rax!=target+slide||out.flags!=flags||out.flags_valid!=0x8d5)) {
                fprintf(stderr,"V497 RIP mismatch case=%u\n",i);
                goto fail;
            }
            ++st.calls;
            hash_word(&st.hash,(uint64_t)status);
            hash_word(&st.hash,out.rax);
            hash_word(&st.hash,out.flags&out.flags_valid);
            hash_word(&st.hash,out.flags_valid);
        }
    }
#endif
    uint64_t misses=0;
    for(size_t j=1;j<entries&&misses<256;++j)
        if((uint64_t)bb_ids_v493[j]-bb_ids_v493[j-1]>1) {
            if(!compare((uint64_t)bb_ids_v493[j-1]+1,0,4,1,NULL,&st))goto fail;
            ++misses;
        }
    if(bb_ids_v493[0]>0) {
        if(!compare(0,0,4,1,NULL,&st))goto fail;
        ++misses;
    }
    const uint64_t final_id=bb_ids_v493[entries-1];
    if(final_id<UINT64_MAX) {
        if(!compare(UINT64_MAX,0,4,1,NULL,&st))goto fail;
        ++misses;
    }
    printf("{\"entries\":%zu,\"miss_ids\":%" PRIu64 ",\"calls\":%" PRIu64
           ",\"fingerprint\":\"%016" PRIx64 "\"}\n",entries,misses,st.calls,st.hash);
    return 0;
fail:
    fputs("V495 indexed dispatcher comparison failed\n",stderr);
    return 1;
}
