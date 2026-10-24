// SPDX-License-Identifier: GPL-2.0-or-later
#include "sh_friends_permissions.hpp"

using SeamlessHunt::Friends::MayJoinSession;
using SeamlessHunt::Friends::MaySendSessionInvite;

// These predicates are called by the actual V47 patched Qt WebAPI routes.
// Cover all four caller/recipient combinations, with the restrictive default
// for private sessions, rather than testing only that a string patch exists.
static_assert(MayJoinSession(false, false));
static_assert(MayJoinSession(false, true));
static_assert(!MayJoinSession(true, false));
static_assert(MayJoinSession(true, true));

static_assert(MaySendSessionInvite(false, false));
static_assert(MaySendSessionInvite(false, true));
static_assert(!MaySendSessionInvite(true, false));
static_assert(MaySendSessionInvite(true, true));

int main() {
    for (int privacy = 0; privacy != 2; ++privacy) {
        for (int allowed = 0; allowed != 2; ++allowed) {
            const bool expect = !privacy || allowed;
            if (MayJoinSession(privacy != 0, allowed != 0) != expect) return 1;
            if (MaySendSessionInvite(privacy != 0, allowed != 0) != expect) return 2;
        }
    }
    return 0;
}
