/* SPDX-License-Identifier: GPL-2.0-or-later */
enum { STATE_SIZE=48, INITIAL_SIZE=32, PATCH_COUNT=2 };
static const unsigned char initial[INITIAL_SIZE]={[8]=1};
static const unsigned char pool[24]={[0]=0x42,[16]='A',[18]='B',[20]='C'};
static const struct bb_ro_row_v476 ro_rows[]={{128,0,16},{256,16,2},{512,18,6}};
static const struct bb_ro_string_v477 ro_strings[]={
    {256,1,1},
#ifdef V477_BAD_WIDE
    {512,1,2}
#else
    {512,2,2}
#endif
};
static const struct bb_patch_v474 patches[PATCH_COUNT]={{24,0x1234},{40,0xabcd}};
static const struct row plan[]={
    {1,0,1,128,{{0,0,0,16}}},
    {2,1,1,0,{{0,128,0,16}}},
#ifdef V477_BAD_VECTOR
    {3,2,1,123,{{0,144,0,16}}},
#else
    {3,2,1,123,{{0,128,0,16}}},
#endif
    {4,0,1,128,{{0,0,0,16}}}
};
