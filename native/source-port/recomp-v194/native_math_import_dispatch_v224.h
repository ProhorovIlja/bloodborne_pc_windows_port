/* SPDX-License-Identifier: GPL-2.0-or-later
 * V224 build-time original-import offset mapping, no runtime EBOOT reader.
 */
#ifndef SHYT_NATIVE_MATH_IMPORT_DISPATCH_V224_H
#define SHYT_NATIVE_MATH_IMPORT_DISPATCH_V224_H
#include "native_math_guest_bridge_v223.h"
#include <stddef.h>
#include <stdint.h>
typedef struct { uint64_t offset; const char *name; } ShytMathImportDesc;
typedef struct { uint64_t offset; ShytGuestMathFn fn; } ShytMathImportEntry;
typedef struct { uint64_t image_base; ShytMathImportEntry entries[23]; } ShytMathImportTable;
/* Bind all 23 distinct names and imported slots, never accept duplicates. */
int shyt_math_import_table_v224_init(ShytMathImportTable *table, uint64_t base,
                                     const ShytMathImportDesc *descs, size_t count);
/* target is RcApi.call's absolute guest address. False = unmodified BbCpu. */
int shyt_math_import_v224_try_call(const ShytMathImportTable *table,
                                  BbCpu *cpu, uint64_t target, uint64_t next);
#endif
