/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_LOAD_ROUTE_V504_H
#define BB_LOAD_ROUTE_V504_H
#include <stddef.h>
#include <stdint.h>
/* Requires the generated memory_routes table, already included by loads.c. */
static inline int bb_load_matches_v504(uint64_t id,uint64_t body) {
    if(id==body)return 1;
    const size_t n=sizeof memory_routes/sizeof *memory_routes;
    size_t lo=0,hi=n;
    while(lo<hi){size_t m=lo+(hi-lo)/2;if(memory_routes[m].id<id)lo=m+1;else hi=m;}
    return lo<n&&memory_routes[lo].id==id&&memory_routes[lo].target==body;
}
#endif
