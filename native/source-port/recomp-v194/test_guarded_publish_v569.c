/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "guarded_publish_v569.h"
#include <string.h>
int main(void) {
    unsigned char data[24]={0},before[24];
    memset(data+8,0xa5,8);
    data[8]=0;
    data[16]=0x7e;
    if (!bb_guarded_publish_v569(data,sizeof data,0,8,UINT64_C(0x8877665544332211)) ||
        memcmp(data,"\x11\x22\x33\x44\x55\x66\x77\x88\x01\0\0\0\0\0\0\0",16) ||
        data[16]!=0x7e) return 1;
    memcpy(before,data,sizeof data);
    if (!bb_guarded_publish_v569(data,sizeof data,0,8,1) ||
        bb_guarded_publish_v569(data,sizeof data,8,8,1) ||
        bb_guarded_publish_v569(data,15,0,8,1) ||
        bb_guarded_publish_v569(data,sizeof data,0,8,0) ||
        memcmp(data,before,sizeof data)) return 2;
    return 0;
}
