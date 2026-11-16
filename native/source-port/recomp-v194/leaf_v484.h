/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_LEAF_V484_H
#define BB_LEAF_V484_H
#include <stddef.h>
#include <stdint.h>
/* flags_valid describes the arithmetic flags defined by this leaf. The
 * controller owns RET, the guest stack and any other register state. */
struct bb_result_v484 { uint64_t rax,flags,flags_valid; };
int bb_call_v484(uint64_t,uint64_t,uint64_t,uint64_t,struct bb_result_v484 *);
#endif
