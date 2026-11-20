/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "tls_resolve_v513.h"

int main(void) {
    const unsigned char data[]={7,8};
    struct bb_tls_module_v513 modules[]={{16,7,2,data},{32,16,0,NULL}};
    unsigned char a[32],b[32],descriptor[16]={1};
    if (!bb_tls_init_v513(a,32,modules,2) || !bb_tls_init_v513(b,32,modules,2)) return 1;
    if (memcmp(a,b,32) || a[16]!=7 || a[17]!=8 || a[18]!=0 || a[31]!=0) return 2;
    unsigned char *ptr=bb_tls_resolve_v513(a,32,modules,2,descriptor,16,2);
    if (ptr!=a+16) return 3;
    *ptr=99;
    if (b[16]!=7) return 4;
    descriptor[8]=6;
    if (bb_tls_resolve_v513(a,32,modules,2,descriptor,16,1)!=a+22 ||
        bb_tls_resolve_v513(a,32,modules,2,descriptor,16,2) ||
        bb_tls_resolve_v513(a,32,modules,2,descriptor,15,1)) return 5;
    descriptor[0]=2;
    if (bb_tls_resolve_v513(a,32,modules,2,descriptor,16,1)!=a+6) return 6;
    descriptor[0]=0;
    if (bb_tls_resolve_v513(a,32,modules,2,descriptor,16,1)) return 7;
    descriptor[0]=3;
    if (bb_tls_resolve_v513(a,32,modules,2,descriptor,16,1)) return 8;
    descriptor[0]=1; descriptor[15]=0x80;
    if (bb_tls_resolve_v513(a,32,modules,2,descriptor,16,1)) return 9;
    memcpy(b,a,32);
    modules[1].below_tp=31;
    if (bb_tls_init_v513(a,32,modules,2) || memcmp(a,b,32)) return 10;
    return 0;
}
