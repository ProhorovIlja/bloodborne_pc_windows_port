/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_DISPATCH_V487_H
#define BB_DISPATCH_V487_H
#include "graph_v485.h"
#include "load_v486.h"
struct bb_input_v487 { uint64_t rax,rcx,rdx,rsi,rdi,flags; };
enum bb_status_v487 { BB_MISS_V487, BB_OK_V487, BB_READ_DENIED_V487 };
enum bb_status_v487 bb_dispatch_v487(uint64_t, const struct bb_input_v487 *,
    const struct bb_region_v478 *, struct bb_result_v484 *);
#endif
