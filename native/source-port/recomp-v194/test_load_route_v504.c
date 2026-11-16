/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "load_route_v504.h"
int main(void) {
    return !bb_load_matches_v504(108,108) ||
           !bb_load_matches_v504(116,108) ||
           !bb_load_matches_v504(124,108) ||
           bb_load_matches_v504(116,132) ||
           bb_load_matches_v504(108,132) ||
           bb_load_matches_v504(140,108) ||
           bb_load_matches_v504(100,108);
}
