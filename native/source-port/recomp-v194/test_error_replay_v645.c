/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "error_vtable_v573.h"
#include <assert.h>
#include <stdio.h>

struct publication { unsigned ordinal, slot, category; };
static const struct publication plan[] = {
#ifdef BB_PRIVATE_REPLAY
#include "private_v645.inc"
#else
    {3, 0, 0}, {4, 1, 2}, {5, 2, 1}, {6, 0, 0}, {8, 1, 2},
#endif
};

/* Independent native identities for the three objects, not their tables. */
static const char *const names[] = {"system", "generic", "iostream"};

static int known(void *ctx, int32_t code) {
    (void)ctx;
    return code == 42;
}

int main(void) {
    _Alignas(8) unsigned char data[48] = {0};
    size_t count[3] = {0}, changes = 0;
    unsigned last = 0, first_gap = 0;
    for (size_t i = 0; i < sizeof plan / sizeof *plan; ++i) {
        const struct publication r = plan[i];
        assert(r.ordinal > last && r.slot < 3 && r.category < 3);
        if (last && r.ordinal != last + 1 && !first_gap) first_gap = last + 1;
        last = r.ordinal;
        const struct bb_publish_row_v573 route = {16u*r.slot, r.category};
        unsigned char *obj = data + route.dst;
        changes += obj[8] == 0;
        assert(bb_publish_sequence_v573(data, sizeof data, &route, 1));
        uintptr_t word;
        memcpy(&word, obj, sizeof word);
        const struct bb_error_slots_v573 *table = bb_error_slots_v573(r.category);
        assert(word == (uintptr_t)table);
        const struct bb_error_slots_v573 *loaded = (const void *)word;
        assert(!strcmp(loaded->name(), names[r.category]));
        assert(!memcmp(obj + 8, "\1\0\0\0\0\0\0\0", 8));
        ++count[r.category];
    }
    assert(changes == 3);
    const struct bb_error_context_v573 ctx = {.cats = {1, 2, 3}, .known = known};
    struct bb_error_value_v570 out;
    assert(bb_error_slots_v573(0)->condition(&ctx, 1, 42, &out) && out.category == 2);
    assert(bb_error_slots_v573(0)->condition(&ctx, 1, 43, &out) && out.category == 1);
    assert(bb_error_slots_v573(2)->condition(&ctx, 3, 42, &out) && out.category == 3);
#ifdef BB_PRIVATE_REPLAY
    assert(plan[0].ordinal == 3 && first_gap == 90);
    assert(count[0] == 4015 && count[1] == 4015 && count[2] == 4015);
#else
    assert(first_gap == 7 && count[0] == 2 && count[1] == 1 && count[2] == 2);
#endif
    printf("category calls=%zu/%zu/%zu publications=%zu first_gap_after_start=%u\n",
           count[0], count[1], count[2], changes, first_gap);
    return 0;
}
