// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

// Fail-closed authorization primitives for the server-side friend/session UX.
// These are not a friend-list UI, matchmaking transport, or invasion feature.
// A bearer token or an exposed private session ID is NOT an invitation.
namespace SeamlessHunt::Friends {
constexpr bool MayJoinSession(bool private_session, bool has_live_invite) noexcept {
    return !private_session || has_live_invite;
}
constexpr bool MaySendSessionInvite(bool private_session, bool sender_is_member) noexcept {
    return !private_session || sender_is_member;
}
} // namespace SeamlessHunt::Friends
