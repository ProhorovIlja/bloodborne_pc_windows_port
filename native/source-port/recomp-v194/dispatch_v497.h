/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_DISPATCH_V497_H
#define BB_DISPATCH_V497_H
#include "dispatch_v492.h"
/* Compile dispatch_v493.c with BB_WITH_RIP_V497 and the five-family units.
 * Slide is an unsigned guest address relocation; never a host pointer. */
enum bb_status_v492 bb_dispatch_v497(uint64_t,const struct bb_input_v487 *,
    const struct bb_region_v478 *,const struct bb_write_region_v492 *,uint64_t,
    struct bb_result_v484 *);
#endif
