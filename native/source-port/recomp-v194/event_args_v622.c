/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <stddef.h>
#include <stdint.h>
#include <string.h>

typedef struct {
    const void *type[15];
    const void *binding;
} BbEventArgs622;
_Static_assert(sizeof(BbEventArgs622)==0x80 && offsetof(BbEventArgs622,binding)==0x78,
               "event argument metadata ABI");

/* Model the verified +0x20/+0x28 virtual entries. Type tokens are supplied
 * by the host; they are not game addresses and are never dereferenced here. */
int bb_event_args_v622(BbEventArgs622 *out,const void *binding,unsigned count,const void *type) {
    if (!out || !binding || count>2 || (!!type != !!count)) return -1;
    BbEventArgs622 value={.binding=binding};
    for (unsigned i=0;i<count;++i) value.type[i]=type;
    *out=value;
    return 0;
}
