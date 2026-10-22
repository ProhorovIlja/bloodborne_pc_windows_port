/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "runtime_legacy_policy.h"
#include <string.h>
int legacy_net_opted_in(const char *env, int party_enabled) {
    return !party_enabled && env && !strcmp(env, "1");
}
int legacy_net_bbsc_enabled(const char *env) {
    return env && strcmp(env, "1") == 0;
}
int legacy_net_supported_game(const char *serial, const char *title, const char *version) {
    if (!serial || !title || !version) return 0;
    if (strlen(serial) < 9 || strlen(serial) > 15) return 0;
    if (strcmp(serial, "UNKNOWN") == 0) return 0;
    /* Regional game identifiers differ; do not hard-code the US CUSA id.
     * Actual game content and patch-site byte verification remain mandatory.
     */
    if (strncmp(title, "Bloodborne", 10) != 0) return 0;
    return strcmp(version, "1.09") == 0;
}
int legacy_net_online_symbol(const char *symbol) {
    static const char *prefixes[] = {"sceNet", "sceNp", "sceHttp", "sceSsl"};
    static const char *excluded[] = {
        "sceNpTrophy", "sceNpCommerce", "sceNpProfileDialog"
    };
    if (!symbol) return 0;
    for (unsigned i=0; i<sizeof(excluded)/sizeof(excluded[0]); ++i)
        if (!strncmp(symbol,excluded[i],strlen(excluded[i]))) return 0;
    for (unsigned i=0; i<sizeof(prefixes)/sizeof(prefixes[0]); ++i)
        if (!strncmp(symbol,prefixes[i],strlen(prefixes[i]))) return 1;
    return 0;
}

/* PS4 NIDs are 11-character URL/base64-like hashes, optionally followed by
 * #library#index metadata. The native network module has its own complete NID
 * table; this avoids silently dropping new NP exports missing in import_names.inc.
 * The DLL returns zero for any hash outside its own explicitly registered APIs.
 */
int legacy_net_scoped_nid(const char *scoped) {
    if (!scoped) return 0;
    unsigned i;
    for (i=0;i<11;++i) {
        const unsigned char c=(unsigned char)scoped[i];
        if (!c || !((c>='a'&&c<='z')||(c>='A'&&c<='Z')||
                    (c>='0'&&c<='9')||c=='+'||c=='-'||c=='_')) return 0;
    }
    if (!scoped[11]) return 1;
    if (scoped[11]!='#') return 0;
    if (!scoped[12]) return 0;
    for (i=12;i<44;++i) {
        const unsigned char c=(unsigned char)scoped[i];
        if (!c) return 1;
        if (!((c>='a'&&c<='z')||(c>='A'&&c<='Z')||
              (c>='0'&&c<='9')||c=='+'||c=='-'||c=='_'||c=='#')) return 0;
    }
    return 0;
}
