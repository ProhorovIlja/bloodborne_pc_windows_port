/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_PENDING_SORT_V653_H
#define BB_PENDING_SORT_V653_H
#include "pending_sort_v652.h"
typedef struct bb_pending_v651 bb_pending_row_v653;
static inline void bb_pending_swap_v653(bb_pending_row_v653 *p,bb_pending_row_v653 *q){bb_pending_row_v653 t=*p;*p=*q;*q=t;}
static inline int bb_pending_lt_v653(bb_pending_row_v653 *p,bb_pending_row_v653 *q){return bb_pending_less_v652(p->target,q->target);}
static inline void bb_pending_median_v653(bb_pending_row_v653 *a,bb_pending_row_v653 *b,bb_pending_row_v653 *c){if(bb_pending_lt_v653(b,a))bb_pending_swap_v653(a,b);if(bb_pending_lt_v653(c,b)){bb_pending_swap_v653(c,b);if(bb_pending_lt_v653(b,a))bb_pending_swap_v653(a,b);}}
/* Move the hole down choosing the right child on ties, then bubble the
 * saved row up. Ordinary swap-down heapsort can reorder equal keys. */
static inline void bb_pending_adjust_v653(bb_pending_row_v653 *p,size_t root,size_t n,bb_pending_row_v653 saved){
 size_t hole=root;
 while(hole<n/2){
  size_t child=2*hole+1;
  if(child+1<n&&!bb_pending_lt_v653(p+child+1,p+child))++child;
  p[hole]=p[child];hole=child;
 }
 while(hole>root){
  size_t parent=(hole-1)/2;
  if(!bb_pending_lt_v653(p+parent,&saved))break;
  p[hole]=p[parent];hole=parent;
 }
 p[hole]=saved;
}
static inline void bb_pending_heap_v653(bb_pending_row_v653 *p,size_t n){
 for(size_t i=n/2;i;){--i;bb_pending_adjust_v653(p,i,n,p[i]);}
 while(n>1){bb_pending_row_v653 saved=p[--n];p[n]=p[0];bb_pending_adjust_v653(p,0,n,saved);}
}
static inline int bb_pending_sort_budget_v653(bb_pending_row_v653 *p,size_t n,size_t budget){
 while(n>32){
  if(!budget){bb_pending_heap_v653(p,n);return 1;}
  size_t m=n/2;
  if(n>=42){size_t s=n/8;bb_pending_median_v653(p,p+s,p+2*s);bb_pending_median_v653(p+m-s,p+m,p+m+s);bb_pending_median_v653(p+n-1-2*s,p+n-1-s,p+n-1);bb_pending_median_v653(p+s,p+m,p+n-1-s);}else bb_pending_median_v653(p,p+m,p+n-1);
  size_t l=m,h=m+1;
  while(l&&p[l-1].target==p[l].target)--l;
  while(h<n&&p[h].target==p[l].target)++h;
  size_t i=h,j=l;
  for(;;){
   while(i<n&&!bb_pending_lt_v653(p+i,p+l)){if(p[i].target==p[l].target){if(h!=i)bb_pending_swap_v653(p+h,p+i);++h;}++i;}
   while(j&&!bb_pending_lt_v653(p+l,p+j-1)){if(p[j-1].target==p[l].target){--l;if(l!=j-1)bb_pending_swap_v653(p+l,p+j-1);}--j;}
   if(!j&&i==n)break;
   if(!j){if(h!=i)bb_pending_swap_v653(p+l,p+h);++h;bb_pending_swap_v653(p+l,p+i);++l;++i;}
   else if(i==n){--j;--l;if(j!=l)bb_pending_swap_v653(p+j,p+l);--h;bb_pending_swap_v653(p+l,p+h);}
   else{--j;bb_pending_swap_v653(p+i,p+j);++i;}
  }
  budget=budget/2+budget/4;
  if(l<n-h){if(!bb_pending_sort_budget_v653(p,l,budget))return 0;p+=h;n-=h;}
  else{if(!bb_pending_sort_budget_v653(p+h,n-h,budget))return 0;n=l;}
 }
 return bb_pending_sort_v652(p,n);
}

/* Exclusive owner. Sort cannot fail after the checked V651 append. */
static inline int bb_registry_register_v653(struct bb_registry_v651 *v,
        const struct bb_registry_allocator_v651 *a, struct bb_registry_row_v650 row,
        const uint64_t targets[static 4]) {
    if (!bb_registry_register_v651(v,a,row,targets)) return 0;
    return bb_pending_sort_budget_v653(v->pending,v->used,v->used);
}
#endif
