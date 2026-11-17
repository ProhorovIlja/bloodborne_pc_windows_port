/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <stddef.h>
#include <stdint.h>
#include <string.h>

typedef struct BbMemberClass608 BbMemberClass608;
typedef struct {
    void *member;
    const char *name;
    const uint16_t *wide;
    size_t length;
} BbMemberRow608;
struct BbMemberClass608 {
    uintptr_t table;
    const BbMemberClass608 *parent;
    uintptr_t auxiliary[2];
    const BbMemberRow608 *begin,*end;
};
_Static_assert(sizeof(BbMemberRow608)==32 && offsetof(BbMemberClass608,begin)==0x20,
               "64-bit member ABI required");

/* Live, sorted rows; bounded ancestry to reject cycles or excessive depth.
 * A matching null member ends the search, as in the retail dispatcher. */
int bb_member_lookup_v608(const BbMemberClass608 *c,const char *name,
                          size_t depth,void **out) {
    if (!c || !name || !out || !depth) return -1;
    *out=NULL;
    size_t length=strlen(name);
    for (;c;c=c->parent) {
        if (!depth--) return -1;
        if ((!c->begin)!=(!c->end)) return -1;
        for (const BbMemberRow608 *r=c->begin;r!=c->end;++r) {
            if (r->length>length) break;
            if (r->length!=length) continue;
            if (!r->name) return -1;
            if (!strcmp(name,r->name)) {
                *out=r->member;
                return *out!=NULL;
            }
        }
    }
    return 0;
}
