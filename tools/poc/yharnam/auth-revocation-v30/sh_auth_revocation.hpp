// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// A cached password MUST NOT override revoked credentials or user bans.
// Pure policy, database-backed status is read separately on every cache hit.
namespace SeamlessHunt::AuthRevocation {
constexpr bool CanTrustCache(bool account_exists, bool banned,
                             bool db_password_hash_unchanged,
                             bool presented_secret_matches) noexcept {
    return account_exists && !banned &&
           db_password_hash_unchanged && presented_secret_matches;
}
constexpr bool ShouldReverify(bool account_exists, bool banned,
                              bool db_password_hash_unchanged) noexcept {
    return account_exists && !banned && !db_password_hash_unchanged;
}
} // namespace SeamlessHunt::AuthRevocation
