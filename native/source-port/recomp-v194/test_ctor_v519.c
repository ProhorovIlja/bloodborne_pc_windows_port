/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "ctor_v519.h"
#include <string.h>
int main(void) {
    unsigned char rw[24]={0}, expected[24]={1};
    expected[8]=0x35; expected[9]=0x12;
    if (!bb_ctor_v519(rw,24,0,8,0x1234,1) || memcmp(rw,expected,24)) return 1;
    if (!bb_ctor_v519(rw,24,0,8,0,1) || memcmp(rw,expected,24)) return 2;
    if (bb_ctor_v519(rw,24,0,7,0,1) || bb_ctor_v519(rw,24,0,17,0,1) ||
        bb_ctor_v519(rw,24,0,8,UINT64_MAX,1) || memcmp(rw,expected,24)) return 3;
    return 0;
}
