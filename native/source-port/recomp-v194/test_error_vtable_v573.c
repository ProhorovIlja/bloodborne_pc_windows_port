/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "error_vtable_v573.h"
static int known(void *p,int32_t c) { return p && c==5; }
static const char *lookup(void *p,int32_t c) { return known(p,c) ? "known" : NULL; }
static void release(void *p,void *x) { *(void **)p=x; }
int main(void) {
    unsigned char bytes[48]={0}, zero[48]={0};
    struct bb_publish_row_v573 rows[]={{0,0},{16,1},{32,3}};
    if (bb_publish_sequence_v573(bytes,48,rows,3) || memcmp(bytes,zero,48)) return 1;
    rows[2].category=2;
    if (!bb_publish_sequence_v573(bytes,48,rows,3)) return 2;
    void *seen=NULL;
    struct bb_error_context_v573 c={{1,2,3},lookup,known,NULL,release,&seen};
    for (unsigned i=0;i<3;++i) {
        const struct bb_error_slots_v573 *v;
        memcpy(&v,bytes+16*i,sizeof v);
        if (v!=bb_error_slots_v573(i) || bytes[16*i+8]!=1) return 3;
        uint64_t self=i+1;
        struct bb_message_v571 m={0};
        struct bb_error_value_v570 e={0};
        if (strcmp(v->name(),bb_error_name_v570(c.cats,self)) ||
            !v->message(&c,self,5,&m) || strcmp(m.storage.text,"known") ||
            !v->condition(&c,self,5,&e) || e.category!=(i ? self : 2) ||
            v->equiv_condition(&c,self,5,e)!=1 ||
            v->equiv_code(self,(struct bb_error_value_v570){e.word,self},5)!=1) return 4;
        v->destroy(bytes);
        if (v->deleting(&c,(void *)(uintptr_t)self) || !v->deleting(&c,bytes) || seen!=bytes) return 5;
    }
    return 0;
}
