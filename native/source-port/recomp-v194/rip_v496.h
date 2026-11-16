/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_RIP_V496_H
#define BB_RIP_V496_H
#include "leaf_v484.h"
enum bb_rip_status_v496 { BB_RIP_MISS_V496, BB_RIP_OK_V496, BB_RIP_DENIED_V496 };
/* slide is the guest data slide, not a host address. RAX is a guest token. */
enum bb_rip_status_v496 bb_rip_v496(uint64_t id,uint64_t slide,uint64_t flags,struct bb_result_v484 *out);
#endif
