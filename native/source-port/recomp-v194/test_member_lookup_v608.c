/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "member_lookup_v608.c"
#include <assert.h>

int main(void) {
    int local=1,inherited=2;
    const BbMemberRow608 outer[]={{&inherited,"foo",NULL,3},{&inherited,"bar",NULL,3}};
    const BbMemberRow608 inner[]={{&local,"x",NULL,1},{NULL,"foo",NULL,3},{&local,"long",NULL,4}};
    BbMemberClass608 root={.begin=outer,.end=outer+2};
    BbMemberClass608 child={.parent=&root,.begin=inner,.end=inner+3};
    void *out=NULL;
    assert(bb_member_lookup_v608(&child,"x",2,&out)==1 && out==&local);
    assert(bb_member_lookup_v608(&child,"bar",2,&out)==1 && out==&inherited);
    assert(bb_member_lookup_v608(&child,"foo",2,&out)==0 && !out);
    assert(bb_member_lookup_v608(&child,"absent",2,&out)==0 && !out);
    assert(bb_member_lookup_v608(&child,"bar",1,&out)==-1 && !out);
    root.parent=&child;
    assert(bb_member_lookup_v608(&child,"absent",8,&out)==-1 && !out);
    return 0;
}
