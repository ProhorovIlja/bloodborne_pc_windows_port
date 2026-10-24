#ifdef NDEBUG
#undef NDEBUG
#endif
#include "sh_auth_revocation.hpp"
#include <cassert>
#include <iostream>
using namespace SeamlessHunt::AuthRevocation;
int main() {
    static_assert(CanTrustCache(true,false,true,true));
    static_assert(!CanTrustCache(true,false,true,false));
    static_assert(!CanTrustCache(true,false,false,true));
    static_assert(!CanTrustCache(true,true,true,true));
    static_assert(!CanTrustCache(false,false,true,true));
    static_assert(!ShouldReverify(false,false,false));
    static_assert(!ShouldReverify(true,true,false));
    static_assert(!ShouldReverify(true,false,true));
    static_assert(ShouldReverify(true,false,false));
    std::cout << "PASS: stale credentials, ban, deleted account, normal cache and rotation\n";
}
