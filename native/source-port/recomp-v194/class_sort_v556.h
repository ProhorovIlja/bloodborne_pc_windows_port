/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_CLASS_SORT_V556_H
#define BB_CLASS_SORT_V556_H
#include "registry_reserve_v541.h"

/* Compare signed 64-bit keys without relying on an out-of-range cast. */
static inline uint64_t bb_class_key_v556(const unsigned char *p,size_t i) {
    return bb_vector_word_v541(p+16*i)^UINT64_C(0x8000000000000000);
}
static inline void bb_class_swap_v556(unsigned char *p,size_t i,size_t j) {
    if (i!=j) {
        unsigned char t[16];
        memcpy(t,p+16*i,16); memcpy(p+16*i,p+16*j,16); memcpy(p+16*j,t,16);
    }
}
static inline void bb_class_med_v556(unsigned char *p,size_t a,size_t b,size_t c) {
    if (bb_class_key_v556(p,b)<bb_class_key_v556(p,a)) bb_class_swap_v556(p,a,b);
    if (bb_class_key_v556(p,c)<bb_class_key_v556(p,b)) {
        bb_class_swap_v556(p,b,c);
        if (bb_class_key_v556(p,b)<bb_class_key_v556(p,a)) bb_class_swap_v556(p,a,b);
    }
}
/* Move the larger child up first (right on equality), then sift the saved
 * record back up. Choosing the left child changes the equal-key order. */
static inline void bb_class_heap_hole_v556(unsigned char *p,size_t n,size_t i,
        const unsigned char item[16]) {
    const size_t top=i;
    while (i<n/2) {
        size_t child=2*i+1;
        if (child+1<n && bb_class_key_v556(p,child)<=bb_class_key_v556(p,child+1)) ++child;
        memcpy(p+16*i,p+16*child,16); i=child;
    }
    while (i>top && bb_class_key_v556(p,(i-1)/2)<bb_class_key_v556(item,0)) {
        const size_t parent=(i-1)/2;
        memcpy(p+16*i,p+16*parent,16); i=parent;
    }
    memcpy(p+16*i,item,16);
}
/* Intro-sort structure compared with Microsoft STL's algorithm header;
 * threshold and equal-key moves verified against the retail sorter. */
static inline void bb_class_sort_rows_v556(unsigned char *p,size_t n,size_t budget) {
    while (n>32 && budget) {
        const size_t mid=n/2, last=n-1;
        if (last>40) {
            const size_t step=n/8;
            bb_class_med_v556(p,0,step,2*step);
            bb_class_med_v556(p,mid-step,mid,mid+step);
            bb_class_med_v556(p,last-2*step,last-step,last);
            bb_class_med_v556(p,step,mid,last-step);
        } else bb_class_med_v556(p,0,mid,last);
        const uint64_t pivot=bb_class_key_v556(p,mid);
        size_t l=mid,r=mid+1;
        while (l && bb_class_key_v556(p,l-1)==pivot) --l;
        while (r<n && bb_class_key_v556(p,r)==pivot) ++r;
        size_t low=l,high=r;
        for (;;) {
            while (high<n && bb_class_key_v556(p,high)>=pivot) {
                if (bb_class_key_v556(p,high)==pivot) bb_class_swap_v556(p,r++,high);
                ++high;
            }
            while (low && bb_class_key_v556(p,low-1)<=pivot) {
                --low;
                if (bb_class_key_v556(p,low)==pivot) bb_class_swap_v556(p,--l,low);
            }
            if (!low && high==n) break;
            if (!low) {
                if (r!=high) bb_class_swap_v556(p,l,r);
                ++r;
                bb_class_swap_v556(p,l++,high++);
            } else if (high==n) {
                bb_class_swap_v556(p,--low,--l);
                bb_class_swap_v556(p,l,--r);
            } else bb_class_swap_v556(p,--low,high++);
        }
        budget=budget/2+budget/4;
        if (l<n-r) {
            bb_class_sort_rows_v556(p,l,budget);
            p+=16*r; n-=r;
        } else {
            bb_class_sort_rows_v556(p+16*r,n-r,budget);
            n=l;
        }
    }
    unsigned char item[16];
    if (n>32) {
        for (size_t i=n/2;i;) {
            --i; memcpy(item,p+16*i,16); bb_class_heap_hole_v556(p,n,i,item);
        }
        while (n>1) {
            --n; memcpy(item,p+16*n,16); memcpy(p+16*n,p,16);
            bb_class_heap_hole_v556(p,n,0,item);
        }
    } else for (size_t i=1;i<n;++i) {
        memcpy(item,p+16*i,16);
        size_t j=i;
        while (j && bb_class_key_v556(item,0)<bb_class_key_v556(p,j-1)) {
            memcpy(p+16*j,p+16*(j-1),16); --j;
        }
        memcpy(p+16*j,item,16);
    }
}
static inline int bb_class_sort_v556(unsigned char *p,size_t bytes,size_t n) {
    if (n>bytes/16 || (!p && n)) return 0;
    if (n>1) bb_class_sort_rows_v556(p,n,n);
    return 1;
}
#endif
