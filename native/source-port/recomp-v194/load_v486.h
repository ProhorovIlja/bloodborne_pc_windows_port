/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_LOAD_V486_H
#define BB_LOAD_V486_H
#include "startup_memory_v478.h"
/* Read one bounded data span; RAX only, flags unchanged. A miss leaves out intact. */
int bb_load_v486(uint64_t,uint64_t,const struct bb_region_v478 *,uint64_t *);
#endif
