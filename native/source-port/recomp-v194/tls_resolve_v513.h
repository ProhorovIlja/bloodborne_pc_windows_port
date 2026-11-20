/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_TLS_RESOLVE_V513_H
#define BB_TLS_RESOLVE_V513_H
#include <stddef.h>
#include <stdint.h>
#include <string.h>

struct bb_tls_module_v513 {
    size_t below_tp, size, file_size;
    const unsigned char *data;
};

/* Modules are in 1-based ID order. Source templates must not alias area.
 * Caller owns alignment and lifetime; this does not set FS/GS or build a TCB. */
static inline int bb_tls_init_v513(unsigned char *area, size_t size,
        const struct bb_tls_module_v513 *modules, size_t count) {
    if (!area || !size || !modules || !count || count > 256) return 0;
    size_t previous = 0;
    for (size_t i=0; i<count; ++i) {
        const struct bb_tls_module_v513 *m=modules+i;
        if (!m->size || m->below_tp > size || m->size > m->below_tp ||
            m->below_tp-m->size < previous || m->file_size > m->size ||
            (m->file_size && !m->data)) return 0;
        previous=m->below_tp;
    }
    memset(area,0,size);
    for (size_t i=0; i<count; ++i)
        if (modules[i].file_size)
            memcpy(area+size-modules[i].below_tp,modules[i].data,modules[i].file_size);
    return 1;
}

/* Decode an already bounded, little-endian 16-byte guest TLS descriptor.
 * Return a host pointer into this context, never an address from the ELF. */
static inline unsigned char *bb_tls_resolve_v513(unsigned char *area, size_t size,
        const struct bb_tls_module_v513 *modules, size_t count,
        const unsigned char *descriptor, size_t descriptor_size, size_t width) {
    if (!area || !modules || !count || count > 256 || !descriptor || descriptor_size != 16 || !width)
        return NULL;
    uint64_t id=0, offset=0;
    for (unsigned i=0; i<8; ++i) {
        id|=(uint64_t)descriptor[i]<<(8*i);
        offset|=(uint64_t)descriptor[8+i]<<(8*i);
    }
    if (!id || id > count) return NULL;
    const struct bb_tls_module_v513 *m=modules+(size_t)id-1;
    if (m->below_tp > size || m->size > m->below_tp || width > m->size || offset > m->size-width)
        return NULL;
    return area+size-m->below_tp+(size_t)offset;
}
#endif
