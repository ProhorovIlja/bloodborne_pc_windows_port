/* SPDX-License-Identifier: GPL-2.0-or-later */
enum { STATE_SIZE=48, INITIAL_SIZE=32, PATCH_COUNT=2 };
static const unsigned char initial[INITIAL_SIZE]={[8]=1}, pool[16]={0x42};
static const struct bb_patch_v474 patches[PATCH_COUNT]={
#ifdef V475_BAD_PATCH
    {8,0x1234},
#else
    {24,0x1234},
#endif
    {40,0xabcd}
};
static const struct row plan[]={
    {1,0,1,128,{{0,0,0,16}}},
    {2,1,1,0,{{0,0,0,16}}},
    {3,2,1,123,{{0,0,0,16}}},
    {4,0,1,128,{{0,0,0,16}}}
};
