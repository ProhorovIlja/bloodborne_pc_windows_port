/* SPDX-License-Identifier: GPL-2.0-or-later */
/* Read only normalized metadata from stdin; no ELF or guest code is loaded.
 * Input: ordinal, child ID, parent ID, name length, four ordered key IDs.
 * The borrowed fixture is deliberately not a production startup entry. */
#define main v603_fixture_main
#include "test_registry_startup_v603.c"
#undef main
#include <inttypes.h>
enum { max_rows=30, max_ids=2*max_rows };
typedef struct {
    unsigned ordinal, child, parent, length;
    uint64_t key[4];
    char name[256];
} Row;
typedef struct {
    Fixture f;
    Row row[max_rows];
    BbClass90State597 nodes[max_ids];
    uint16_t wide[256];
    unsigned prepares, warm;
} Replay;

static int prep605(void *v) { ++((Replay *)v)->prepares; return 0; }
static int get605(void *v,unsigned char **out) {
    Replay *r=v; Fixture *t=&r->f;
    return bb_class_base_v602(r->nodes+r->row[t->idx].parent,&t->cache,&t->base_ops,out);
}
static int field605(void *v,uint64_t d,unsigned slot,uint64_t *out) {
    Replay *r=v; Row *row=r->row+r->f.idx;
    if (slot>=6 || d!=(uintptr_t)r->nodes[row->child].descriptor) return 0;
    *out=slot<2?load594((const unsigned char *)(uintptr_t)d+0x40+8*slot):row->key[slot-2];
    return 1;
}
static int insert605(void *v,unsigned char *d) {
    Replay *r=v; Fixture *t=&r->f;
    t->cache=r->nodes[r->row[t->idx].child].allocator;
    struct bb_class_vector_v599 vec[2];
    for (unsigned i=0;i<2;++i) {
        bb_arena_store_v527(t->hdr[i]+32,(uintptr_t)t->owner);
        vec[i]=(struct bb_class_vector_v599){t->hdr[i],(uintptr_t)t->hdr[i],t->live[i]};
    }
    const struct bb_class_ops_v599 op={r,field605,allocate,release};
    return bb_class_register_v599(vec,vec+1,(uintptr_t)d,&op)!=BB_REG_OK;
}

int main(void) {
    Replay *r=calloc(1,sizeof *r); assert(r);
    unsigned char seen[max_ids]={0}, children[max_ids]={0};
    unsigned count=0, identities=0;
    while (count<max_rows) {
        Row *x=r->row+count;
        int n=scanf("%u %u %u %u %" SCNu64 " %" SCNu64 " %" SCNu64 " %" SCNu64,
                    &x->ordinal,&x->child,&x->parent,&x->length,
                    x->key,x->key+1,x->key+2,x->key+3);
        if (n==EOF) break;
        if (n!=8 || !x->ordinal || (count && x->ordinal<=x[-1].ordinal) ||
            x->child>=max_ids || x->parent>=max_ids || x->child==x->parent ||
            children[x->child] || !x->length || x->length>=sizeof x->name) goto malformed;
        children[x->child]=1;
        identities+=!seen[x->child]; seen[x->child]=1;
        identities+=!seen[x->parent]; seen[x->parent]=1;
        memset(x->name,'A',x->length);
        ++count;
    }
    char extra;
    if (!count || scanf(" %c",&extra)!=EOF) goto malformed;
    for (unsigned i=0;i<255;++i) r->wide[i]='A';
    Fixture *t=&r->f;
    t->arena=malloc(0x100000); assert(t->arena);
    assert(!pthread_mutex_init(&t->gate,NULL) && !pthread_mutex_init(&t->heap,NULL));
    t->base_ops=(BbClass90Ops597){r,1,2,0,0,prep605,factory,kind,insert605,NULL,diagnose};
    unsigned order[max_rows];
    for (t->idx=0;t->idx<count;++t->idx) {
        Row *row=r->row+t->idx;
        BbClass90State597 *s=r->nodes+row->child;
        unsigned before=r->prepares;
        int was_warm=s->published!=NULL;
        int parent_warm=r->nodes[row->parent].published!=NULL;
        s->allocator=t->cache;
        BbClass90Ops597 op=t->base_ops;
        op.ascii_name=(uintptr_t)row->name; op.wide_name=(uintptr_t)r->wide;
        int rc=bb_class90_checked_v603(s,&op,get605);
        if (rc) { fprintf(stderr,"constructor %u stopped: %d\n",row->ordinal,rc); goto stopped; }
        assert(parent597(s->descriptor)==r->nodes[row->parent].published);
        assert(r->prepares-before==(unsigned)(!was_warm+!parent_warm));
        if (was_warm) { ++r->warm; printf("already initialized: %u\n",row->ordinal); }
        unsigned i=t->idx;
        while (i && r->row[order[i-1]].length>row->length) { order[i]=order[i-1]; --i; }
        order[i]=t->idx;
    }
    assert(r->prepares==identities && t->factories==1 && t->inits==1 && t->allocations==2);
    assert(load594(t->hdr[0]+16)-load594(t->hdr[0]+8)==count*32u);
    assert(load594(t->hdr[1]+16)-load594(t->hdr[1]+8)==count*64u);
    unsigned key_seen[max_rows][4]={0};
    uint64_t prev=0;
    for (unsigned i=0;i<count;++i) {
        Row *x=r->row+order[i];
        unsigned char *p=t->live[0].data+32*i;
        assert(load594(p)==(uintptr_t)r->nodes[x->child].descriptor);
        assert(load594(p+8)==(uintptr_t)x->name && load594(p+24)==x->length);
    }
    for (unsigned i=0;i<4*count;++i) {
        unsigned char *p=t->live[1].data+16*i;
        uint64_t key=load594(p), owner=load594(p+8);
        assert(key>=prev); prev=key;
        unsigned j=0;
        while (j<count && owner!=(uintptr_t)r->nodes[r->row[j].child].descriptor) ++j;
        assert(j<count);
        unsigned k=0;
        while (k<4 && (key_seen[j][k] || r->row[j].key[k]!=key)) ++k;
        assert(k<4); key_seen[j][k]=1;
    }
    printf("returns=%u identities=%u warm=%u primary=%u secondary=%u\n",
           count,identities,r->warm,count,4*count);
    assert(!pthread_rwlock_destroy(&t->areas));
    assert(!pthread_mutex_destroy(&t->gate) && !pthread_mutex_destroy(&t->heap));
    free(t->arena); free(r); return 0;
stopped:
    free(t->arena); free(r); return 1;
malformed:
    fputs("invalid normalized fixture\n",stderr);
    free(r); return 2;
}
