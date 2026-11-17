/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <stddef.h>
#include <stdint.h>

/* PS4 libc wide symbols use unsigned 16-bit code units, not host wchar_t.
 * Counts are code units; memory variants do not stop at embedded zeroes. */
static int order630(uint16_t a, uint16_t b) { return (a>b)-(a<b); }
size_t bb_libc_wcslen_v630(const uint16_t *s) {
    size_t i=0;
    while (s[i]) ++i;
    return i;
}
int bb_libc_wcscmp_v630(const uint16_t *a,const uint16_t *b) {
    while (*a && *a==*b) { ++a; ++b; }
    return order630(*a,*b);
}
int bb_libc_wcsncmp_v630(const uint16_t *a,const uint16_t *b,size_t n) {
    for (size_t i=0;i<n;++i)
        if (a[i]!=b[i] || !a[i]) return order630(a[i],b[i]);
    return 0;
}
const uint16_t *bb_libc_wmemchr_v630(const uint16_t *s,uint16_t c,size_t n) {
    for (size_t i=0;i<n;++i) if (s[i]==c) return s+i;
    return NULL;
}
int bb_libc_wmemcmp_v630(const uint16_t *a,const uint16_t *b,size_t n) {
    for (size_t i=0;i<n;++i) if (a[i]!=b[i]) return order630(a[i],b[i]);
    return 0;
}
