/* SPDX-License-Identifier: GPL-2.0-or-later */
static const struct object objects[] = {{32,128,{0}}, {48,136,{0}}};
static const struct step steps[] = {
    {1,0}, {2,0},
#if defined(V469_BAD_INDEX)
    {3,2}
#elif defined(V469_BAD_ORDER)
    {2,1}
#else
    {3,1}
#endif
};
