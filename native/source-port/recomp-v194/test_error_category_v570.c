/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "error_category_v570.h"
#include <string.h>
static int known(void *ctx,int32_t code) { return code==*(const int32_t *)ctx; }
int main(void) {
    const struct bb_error_categories_v570 c={1,2,3};
    int32_t key=-1;
    struct bb_error_value_v570 out={5,6};
    if (strcmp(bb_error_name_v570(c,1),"system") ||
        strcmp(bb_error_name_v570(c,2),"generic") ||
        strcmp(bb_error_name_v570(c,3),"iostream") || bb_error_name_v570(c,4)) return 1;
    if (bb_error_default_v570(c,1,0,0,0,&out) || out.word!=5 || out.category!=6) return 2;
    if (!bb_error_default_v570(c,1,-1,known,&key,&out) ||
        out.category!=2 || out.word!=UINT64_C(0xffffffff00000000)) return 3;
    if (!bb_error_default_v570(c,1,0,known,&key,&out) || out.category!=1 || out.word) return 4;
    if (!bb_error_default_v570(c,3,1,0,0,&out) || out.category!=3 ||
        !bb_error_equal_v570(out,(struct bb_error_value_v570){UINT64_C(0x1deadbeef),3}) ||
        bb_error_equal_v570(out,(struct bb_error_value_v570){UINT64_C(0x100000000),2})) return 5;
    return 0;
}
