/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_DISPATCH_V492_H
#define BB_DISPATCH_V492_H
#include "dispatch_v487.h"
struct bb_write_region_v492 { uint64_t base; size_t size; unsigned char *bytes; };
enum bb_status_v492 { BB_MISS_V492, BB_OK_V492, BB_READ_DENIED_V492, BB_WRITE_DENIED_V492, BB_ADDRESS_DENIED_V497 };
/* The caller owns permissions, lifetime, guest stack and synchronization. */
enum bb_status_v492 bb_dispatch_v492(uint64_t,const struct bb_input_v487 *,
    const struct bb_region_v478 *,const struct bb_write_region_v492 *,struct bb_result_v484 *);
#endif
