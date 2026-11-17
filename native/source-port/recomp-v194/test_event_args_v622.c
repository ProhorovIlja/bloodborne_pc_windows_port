/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "event_args_v622.c"
#include <assert.h>

int main(void) {
    BbEventArgs622 args;
    int record, token;
    for (unsigned n=0;n<=2;++n) {
        memset(&args,0xa5,sizeof args);
        assert(bb_event_args_v622(&args,&record,n,n?&token:NULL)==0);
        assert(args.binding==&record);
        for (unsigned i=0;i<15;++i) assert(args.type[i]==(i<n?&token:NULL));
    }
    BbEventArgs622 old=args;
    assert(bb_event_args_v622(&args,&record,3,&token)==-1);
    assert(bb_event_args_v622(&args,&record,2,NULL)==-1);
    assert(bb_event_args_v622(&args,&record,0,&token)==-1);
    assert(bb_event_args_v622(&args,NULL,0,NULL)==-1);
    assert(bb_event_args_v622(NULL,&record,0,NULL)==-1);
    assert(!memcmp(&args,&old,sizeof args));
    return 0;
}
