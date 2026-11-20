/* SPDX-License-Identifier: GPL-2.0-or-later */
#include <stddef.h>
#include <stdint.h>

/*
 * Single-threaded startup only. Call only after checking the complete original
 * leaf and the vtable's provenance offline. The caller supplies one writable
 * data span (not a host pointer derived from guest input), the relative object
 * offset, and a validated game-visible vtable address.
 * Return -1 on invalid span, 0 for an already-set guard, 1 for a new write.
 * This helper reproduces memory side effects, not guest flags or registers.
 */
int native_guarded_leaf_v463(unsigned char *data, size_t size, size_t object,
                             uint64_t vtable) {
    if (!data || object > size || size - object < 16 || !vtable) return -1;
    unsigned char *p = data + object;
    if (p[8] != 0) return 0;
    for (unsigned i = 0; i < 8; ++i) p[i] = (unsigned char)(vtable >> (i * 8));
    p[8] = 1;
    for (unsigned i = 9; i < 16; ++i) p[i] = 0;
    return 1;
}

#ifdef NATIVE_GUARDED_LEAF_V463_SELF_TEST
#include <string.h>
int main(void) {
    unsigned char data[18], before[18];
    memset(data, 0xab, sizeof data);
    data[9] = 0; /* Low guard byte only; high guard bytes are nonzero. */
    memcpy(before, data, sizeof data);
    if (native_guarded_leaf_v463(data, sizeof data, SIZE_MAX, 1) != -1 ||
        native_guarded_leaf_v463(data, sizeof data, 3, 1) != -1 ||
        native_guarded_leaf_v463(data, sizeof data, 1, 0) != -1 ||
        native_guarded_leaf_v463(NULL, sizeof data, 1, 1) != -1 ||
        memcmp(data, before, sizeof data)) return 1;
    if (native_guarded_leaf_v463(data, sizeof data, 1, UINT64_C(0x123456789abcdef0)) != 1)
        return 2;
    const unsigned char expected[18] = {
        0xab, 0xf0, 0xde, 0xbc, 0x9a, 0x78, 0x56, 0x34, 0x12,
        1, 0, 0, 0, 0, 0, 0, 0, 0xab
    };
    if (memcmp(data, expected, sizeof data) ||
        native_guarded_leaf_v463(data, sizeof data, 1, 2) != 0 ||
        memcmp(data, expected, sizeof data)) return 3;
    return 0;
}
#endif
