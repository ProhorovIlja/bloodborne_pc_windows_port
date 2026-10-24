/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_RUNTIME_LEGACY_POLICY_H
#define BB_RUNTIME_LEGACY_POLICY_H
#ifdef __cplusplus
extern "C" {
#endif
/* Strict opt-in only. Explicitly reject a conflict with visy's separate party stack. */
int legacy_net_opted_in(const char *env, int party_enabled);
/* Both opt-ins are required for the still-unreleased native BBSC client. */
int legacy_net_bbsc_enabled(const char *env);
/* Only a verified Bloodborne v1.09 guest may attempt developer-only BBSC. */
int legacy_net_supported_game(const char *serial, const char *title, const char *version);
/* Never redirect locally-owned trophy, commerce or profile/dialog APIs. */
int legacy_net_online_symbol(const char *symbol);
/* A previously unknown, syntactically valid PS4 NID can still be resolved by
 * the pinned network DLL. Unknown human-readable names are never forwarded. */
int legacy_net_scoped_nid(const char *scoped);
#ifdef __cplusplus
}
#endif
#endif
