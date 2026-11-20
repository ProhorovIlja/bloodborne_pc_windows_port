/* SPDX-License-Identifier: GPL-2.0-or-later */
static const unsigned char initial[16]={0}, pool[16]={0x42};
static const struct row plan[]={
    {1,0,1,128,{{0,0,0,16}}},
    {2,1,1,0,{{0,0,0,16}}},
#ifdef V473_BAD
    {3,2,1,123,{{16,0,0,16}}},
#else
    {3,2,1,123,{{0,0,0,16}}},
#endif
    {4,0,1,128,{{0,0,0,16}}}
};
