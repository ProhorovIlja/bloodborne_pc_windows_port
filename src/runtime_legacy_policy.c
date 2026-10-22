/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "runtime_legacy_policy.h"
#include <string.h>
int legacy_net_opted_in(const char *env, int party_enabled) {
    return !party_enabled && env && !strcmp(env, "1");
}
int legacy_net_online_symbol(const char *symbol) {
    static const char *prefixes[] = {"sceNet", "sceNp", "sceHttp", "sceSsl"};
    static const char *excluded[] = {
        "sceNpTrophy", "sceNpCommerce", "sceNpProfileDialog",
        "sceNpScore", "sceNpSns", "sceNpParty"
    };
    if (!symbol) return 0;
    for (unsigned i=0; i<sizeof(excluded)/sizeof(excluded[0]); ++i)
        if (!strncmp(symbol,excluded[i],strlen(excluded[i]))) return 0;
    for (unsigned i=0; i<sizeof(prefixes)/sizeof(prefixes[0]); ++i)
        if (!strncmp(symbol,prefixes[i],strlen(prefixes[i]))) return 1;
    return 0;
}
