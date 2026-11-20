/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "pending_sort_v653.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>

static void *alloc(void *ctx, size_t bytes, size_t alignment) {
    (void)ctx;
    assert(alignment == 8);
    return malloc(bytes);
}
static void release(void *ctx, void *ptr) { (void)ctx; free(ptr); }

int main(void) {
    /* Fingerprints of the original order on these synthetic rows, offline.
     * Sortedness alone misses changes in the permutation of equal keys. */
    uint64_t order[3] = {UINT64_C(14695981039346656037),
                         UINT64_C(14695981039346656037), UINT64_C(14695981039346656037)};
    for (size_t n = 0; n <= 257; ++n) {
        for (size_t mode = 0; mode < 3; ++mode) {
            struct bb_pending_v651 rows[259];
            unsigned char seen[257] = {0};
            const size_t budget = mode < 2 ? mode : n;
            for (size_t i = 0; i < n; ++i)
                rows[i+1] = (struct bb_pending_v651){(uint64_t)(i*67%11)-5, i};
            rows[0] = rows[n+1] = (struct bb_pending_v651){17, 29};
            assert(bb_pending_sort_budget_v653(rows+1,n,budget));
            for (size_t i = 1; i <= n; ++i) {
                const size_t id = rows[i].object;
                order[mode] = (order[mode] ^ id) * UINT64_C(1099511628211);
                assert(id < n && !seen[id]++ && rows[i].target == (uint64_t)(id*67%11)-5);
                assert(i == 1 || !bb_pending_less_v652(rows[i].target,rows[i-1].target));
            }
            assert(rows[0].target == 17 && rows[0].object == 29 &&
                   rows[n+1].target == 17 && rows[n+1].object == 29);
        }
    }
    assert(order[0] == UINT64_C(0x9deb53ff0e29cbd1));
    assert(order[1] == UINT64_C(0x1bfa5a92e46ed4e7));
    assert(order[2] == UINT64_C(0xc524ab4a50b8148d));
    struct bb_registry_v651 registry = {0};
    const struct bb_registry_allocator_v651 allocator = {NULL,alloc,release};
    const uint64_t targets[] = {3,UINT64_MAX,0,UINT64_C(1)<<63};
    for (size_t i = 0; i < 160; ++i) {
        const struct bb_registry_row_v650 row = {i+1,1,0,i};
        assert(bb_registry_register_v653(&registry,&allocator,row,targets));
        assert(registry.count == i+1 && registry.used == 4*(i+1));
        for (size_t j = 1; j < registry.used; ++j)
            assert(!bb_pending_less_v652(registry.pending[j].target,registry.pending[j-1].target));
    }
    assert(registry.reserved > 512);
    free(registry.rows);
    free(registry.pending);
    puts("V653: 774 sort cases and 160 composed registrations OK");
    return 0;
}
