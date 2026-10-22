/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef BB_RUNTIME_LEGACY_POLICY_H
#define BB_RUNTIME_LEGACY_POLICY_H
#ifdef __cplusplus
extern "C" {
#endif
/* Strict opt-in only. Explicitly reject a conflict with visy's separate party stack. */
int legacy_net_opted_in(const char *env, int party_enabled);
/* Never redirect locally-owned trophy, commerce or profile/dialog APIs. */
int legacy_net_online_symbol(const char *symbol);
#ifdef __cplusplus
}
#endif
#endif
