/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "startup_transaction_v547.h"
#include <string.h>
int main(void) {
    unsigned char t[80]; memset(t,0xa5,sizeof t);
    if (!bb_tls_mark_v547(t,sizeof t,48,-24,UINT64_C(0x0102030405060708)) ||
        memcmp(t+24,"\x08\x07\x06\x05\x04\x03\x02\x01\xfb\0\0\0",12) ||
        t[23]!=0xa5 || t[36]!=0xa5 || bb_tls_mark_v547(t,sizeof t,48,21,1) ||
        bb_tls_mark_v547(t,sizeof t,48,INT64_MIN,1)) return 1;
    memset(t+40,0,4);
    struct bb_transaction_v547 r=bb_tls_oom_v547(t,sizeof t,0x1000,48,-8,INT64_MIN);
    if (r.kind!=BB_TX_REPORT || r.argument || r.value!=0x109) return 2;
    t[43]=1;
    r=bb_tls_oom_v547(t,sizeof t,0x1000,48,-8,-48);
    if (r.kind!=BB_TX_TRANSFER || r.argument!=0x1000 || r.value!=1) return 3;
    if (bb_tls_oom_v547(t,sizeof t,0x1000,48,-8,32).kind!=BB_TX_INVALID ||
        bb_tls_oom_v547(t,sizeof t,UINT64_MAX,48,-8,-48).kind!=BB_TX_INVALID ||
        bb_tls_oom_v547(t,sizeof t,0x1000,48,29,-48).kind!=BB_TX_INVALID) return 4;
    return 0;
}
