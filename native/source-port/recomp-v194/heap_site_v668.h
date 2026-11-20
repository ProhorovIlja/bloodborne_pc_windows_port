/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_HEAP_SITE_V668_H
#define BB_HEAP_SITE_V668_H
#include <stddef.h>
#include <stdint.h>

/* Scoped replacement for the source-location stores, not the PS4 TLS ABI.
 * Borrowed source strings must outlive any subsequent read on this thread. */
struct bb_heap_site_record_v668 {
    const char *file;
    uint32_t line;
    uint32_t untouched;
    uintptr_t other;
};
_Static_assert(sizeof(struct bb_heap_site_record_v668)==24 &&
               offsetof(struct bb_heap_site_record_v668,line)==8 &&
               offsetof(struct bb_heap_site_record_v668,other)==16,"64-bit site layout");
extern _Thread_local struct bb_heap_site_record_v668 bb_heap_site_v668;
static inline void bb_heap_site_note_v668(const char *file, uint32_t line) {
    bb_heap_site_v668.file=file;
    bb_heap_site_v668.line=line;
}
#endif
