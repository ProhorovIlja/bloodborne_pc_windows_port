/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "registry_rows_v650.h"
#include <assert.h>
#include <stdio.h>

#ifdef BB_PRIVATE_DIFFERENTIAL
extern const struct bb_registry_row_v650 *bb_original_upper(
    const struct bb_registry_row_v650 *, const struct bb_registry_row_v650 *, uint64_t);
#endif

int main(void) {
    static const uint64_t keys[] = {0, 1, 7, INT64_MAX, UINT64_C(1)<<63, UINT64_MAX};
    struct bb_registry_row_v650 a[96], b[96];
    size_t cases = 0;
    /* Rejections must preserve both the caller's count and any existing row. */
    size_t count = 0;
    const struct bb_registry_row_v650 sentinel = {1, 2, 3, 4};
    a[0] = sentinel;
    assert(!bb_registry_insert_v650(NULL, &count, 96, sentinel));
    assert(!bb_registry_insert_v650(a, NULL, 96, sentinel));
    assert(!bb_registry_insert_v650(a, &count, 0, sentinel));
    assert(!bb_registry_insert_v650(a, &count, SIZE_MAX / sizeof *a + 1, sentinel));
    assert(count == 0 && !memcmp(a, &sentinel, sizeof sentinel));
    assert(bb_registry_upper_v650(NULL, 0, UINT64_MAX) == 0);
    uint64_t rng = 650;
    for (size_t round = 0; round < 256; ++round) {
        size_t n = 0;
        for (size_t i = 0; i < 96; ++i) {
            rng = rng * UINT64_C(6364136223846793005) + 1;
            uint64_t k = keys[(rng >> 32) % 6];
            const struct bb_registry_row_v650 x = {i+1, round+1, rng, k};
            size_t pos = 0;
            while (pos < i && b[pos].key <= k) ++pos;
            assert(bb_registry_upper_v650(a, n, k) == pos);
#ifdef BB_PRIVATE_DIFFERENTIAL
            assert(bb_original_upper(a, a+n, k) == a+pos);
#endif
            for (size_t j = i; j > pos; --j) b[j] = b[j-1];
            b[pos] = x;
            assert(bb_registry_insert_v650(a, &n, 96, x) && n == i+1);
            assert(!memcmp(a, b, n*sizeof *a));
            ++cases;
        }
        assert(!bb_registry_insert_v650(a, &n, 96, b[0]) && n == 96);
        assert(!memcmp(a,b,sizeof a));
    }
    printf("%zu registry row cases passed\n", cases);
    return 0;
}
