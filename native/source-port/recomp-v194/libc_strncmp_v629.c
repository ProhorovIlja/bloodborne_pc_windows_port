/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <stddef.h>
#include <string.h>

/* The pinned PS4 libc returns exactly -1, 0 or 1, unlike the generic
 * strncmp contract. This is a host ABI function; no guest image is needed. */
int bb_libc_strncmp_v629(const char *a,const char *b,size_t n) {
    const int cmp=strncmp(a,b,n);
    return (cmp>0)-(cmp<0);
}
