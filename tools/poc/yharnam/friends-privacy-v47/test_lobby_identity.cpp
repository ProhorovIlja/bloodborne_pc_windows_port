// SPDX-License-Identifier: GPL-2.0-or-later
#include "sh_lobby_identity.hpp"

using SeamlessHunt::Identity::MatchesAuthenticatedMember;
static_assert(MatchesAuthenticatedMember("Kaniel", "4b616e69656c"));
static_assert(MatchesAuthenticatedMember("hunter_01", "68756e7465725f3031"));
static_assert(!MatchesAuthenticatedMember("Kaniel", "4B616E69656C"));
static_assert(!MatchesAuthenticatedMember("Kaniel", "4b616e69656d"));
static_assert(!MatchesAuthenticatedMember("", ""));
static_assert(!MatchesAuthenticatedMember("Kaniel", ""));
static_assert(!MatchesAuthenticatedMember("Kaniel", "host"));
static_assert(!MatchesAuthenticatedMember("A", "41" "00"));
static_assert(!MatchesAuthenticatedMember("AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
                                         "414141414141414141414141414141414141414141414141414141414141414141"));

int main() {
    if (!MatchesAuthenticatedMember(std::string_view("x\0y", 3), "780079")) return 1;
    if (MatchesAuthenticatedMember(std::string_view("x\0y", 3), "780078")) return 2;
    return 0;
}
