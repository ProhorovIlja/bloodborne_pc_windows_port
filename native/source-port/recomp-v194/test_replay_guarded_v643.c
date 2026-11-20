/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "guarded_publish_v569.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
struct pub_row { unsigned ordinal, slot, target; };
#include "private_v643.inc"
static const unsigned char identities[TARGETS];

static void replay(unsigned seed) {
    unsigned char data[SLOTS * 16] = {0};
    uint64_t expected[SLOTS] = {0};
    unsigned char marked[SLOTS] = {0};
    unsigned previous = 0;
    if (seed) for (size_t i = 0; i < SLOTS; ++i) {
        if (i % 2 == 0) {
            data[16*i+8] = 0xa5;
            data[16*i+15] = 0x5a;
            marked[i] = 1;
        } else data[16*i+15] = 0x5a;
    }
    for (size_t j = 0; j < sizeof rows/sizeof *rows; ++j) {
        struct pub_row r = rows[j];
        assert(r.ordinal > previous && r.slot < SLOTS && r.target < TARGETS);
        previous = r.ordinal;
        size_t dst = 16*r.slot, guard = dst + 8;
        uint64_t target = (uintptr_t)&identities[r.target];
        if (!marked[r.slot]) expected[r.slot] = target;
        unsigned char before[8];
        memcpy(before, data + guard, 8);
        assert(bb_guarded_publish_v569(data, sizeof data, dst, guard, target));
        uint64_t got;
        memcpy(&got, data + dst, 8);
        assert(got == expected[r.slot]);
        if (marked[r.slot]) assert(!memcmp(before, data + guard, 8));
        else {
            assert(!memcmp(data + guard, "\1\0\0\0\0\0\0\0", 8));
            marked[r.slot] = 1;
        }
    }
}

int main(void) {
    replay(0);
    replay(1);
    printf("rows=%zu slots=%d targets=%d passes=2\n", sizeof rows/sizeof *rows, SLOTS, TARGETS);
    return 0;
}
