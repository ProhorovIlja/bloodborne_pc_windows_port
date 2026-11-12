/* V403 original-free generated route-guard executable smoke test.
 * This is NOT a Bloodborne runtime dispatcher and does not boot game code.
 */
#include "native_route_guard_v403_generated.h"
#include <stdio.h>

int main(void) {
    unsigned i;
    unsigned import_sites = 0u;
    unsigned count = (unsigned)(sizeof(shyt_v403_routes) /
                                 sizeof(shyt_v403_routes[0]));
    if (count != 11u) return 10;
    if (shyt_v403_is_synthetic_candidate(UINT64_C(0x1140))) return 11;
    if (shyt_v403_is_synthetic_candidate(UINT64_C(0x0))) return 12;
    if (shyt_v403_is_synthetic_candidate(UINT64_C(0x1170))) return 13;
    if (shyt_v403_is_synthetic_candidate(UINT64_C(0xffffffffffffffff))) return 14;
    for (i = 0u; i < count; ++i) {
        if (!shyt_v403_is_synthetic_candidate(shyt_v403_routes[i].offset))
            return 20;
        if (i && shyt_v403_routes[i].offset <= shyt_v403_routes[i - 1u].offset)
            return 21;
        if (shyt_v403_routes[i].host_imports > 1u) return 22;
        import_sites += shyt_v403_routes[i].host_imports;
    }
    if (import_sites != 2u) return 30;
    puts("NATIVE_V403_DEFAULT_DENY_SYNTHETIC_ROUTE_GUARD_PASS");
    return 0;
}
