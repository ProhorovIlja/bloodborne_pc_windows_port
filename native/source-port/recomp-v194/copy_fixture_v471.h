/* SPDX-License-Identifier: GPL-2.0-or-later */
static const unsigned char pool[16]={90};
enum {STATE_SIZE=16};
static const struct row rows[]={
#if defined(V471_BAD_COLLISION)
    {1,1,{{0,0}}}
#elif defined(V471_BAD_SPAN)
    {2,1,{{0,16}}}
#else
    {2,1,{{0,0}}}
#endif
};
