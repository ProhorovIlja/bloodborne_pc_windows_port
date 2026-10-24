#!/usr/bin/env python3
"""Patch the pinned Yharnam Together Qt WebAPI private-session authorization.

Work on the *existing* friendship/invitation APIs. Never create a parallel
player database, auto-invade, or treat knowing a session ID as join authority.
Refuse to patch an unknown upstream revision or an already-patched source.
"""
from __future__ import annotations
from pathlib import Path
import argparse

PATH = "server/src/webapi_routes_session.cpp"
HEADER = "server/src/sh_friends_permissions.hpp"
MARKER = "SHYT-V47-FRIENDS-PRIVATE-SESSION"

JOIN_ANCHOR = "        if (s.sessionLockFlag) {\n"
INVITE_ANCHOR = (
    "        const QStringList sessionPlatforms = sit->availablePlatforms;\n"
    "        for (const auto& r : recipients) {"
)
JOIN_GUARD = """        // SHYT-V47-FRIENDS-PRIVATE-SESSION: a private session ID is not a
        // join capability. Permit existing members above; new members need
        // a live, unused invitation addressed to the signed-in account.
        const bool privateSession = s.sessionPrivacy == QStringLiteral("private");
        if (!SeamlessHunt::Friends::MayJoinSession(
                privateSession,
                !privateSession || HasActiveInvitation(shared, sessionId, *auth.userId))) {
            return JsonError(QHttpServerResponse::StatusCode::Forbidden,
                             SESSION_NOT_PERMITTED,
                             QStringLiteral("A valid invitation is required for this private session"));
        }
"""
# An unused invite opens a private session exactly once. Without this, a guest
# can leave and join again with the same invitation forever (upstream default
# TTL is 0 = no expiry). Invalidate *all* live invitations for this
# recipient/session on successful admission, while holding sessionsLock.
# Do not mark anything used when admission fails or the session is public.
JOIN_CONSUME = """        // SHYT-V50-PRIVATE-INVITE-ONE-SHOT: an accepted private invitation
        // cannot be replayed after the guest leaves or the host removes them.
        // Keep this under sessionsLock so the initial authorization and
        // consumption cannot race other joins.
        if (s.sessionPrivacy == QStringLiteral("private")) {
            const qint64 usedAt = QDateTime::currentMSecsSinceEpoch();
            for (auto it = shared.invitations.begin(); it != shared.invitations.end(); ++it) {
                auto& invitation = it.value();
                if (invitation.sessionId == sessionId &&
                    invitation.toUserId == *auth.userId &&
                    !invitation.used &&
                    (invitation.validUntil == 0 || usedAt <= invitation.validUntil)) {
                    invitation.used = true;
                    invitation.updatedAt = usedAt;
                }
            }
        }
"""
INVITE_GUARD = """        // SHYT-V47-FRIENDS-PRIVATE-INVITE: an unrelated account must not
        // mint invitations that bypass the private session's access rules.
        // Public sessions keep the original invitation behavior.
        bool senderIsMember = false;
        for (const auto& member : sit->members) {
            if (member.userId == *auth.userId) {
                senderIsMember = true;
                break;
            }
        }
        if (!SeamlessHunt::Friends::MaySendSessionInvite(
                sit->sessionPrivacy == QStringLiteral("private"), senderIsMember)) {
            return JsonError(QHttpServerResponse::StatusCode::Forbidden,
                             SESSION_NOT_PERMITTED,
                             QStringLiteral("Only session members may invite to a private session"));
        }
"""

def once(source: str, original: str, replacement: str, label: str) -> str:
    if source.count(original) != 1:
        raise ValueError(f"V47 pinned source anchor drifted: {label}")
    return source.replace(original, replacement, 1)

def transform(source: str) -> str:
    if MARKER in source:
        raise ValueError("V47 already applied")
    for required in (
        "QHttpServerResponse HandleSessionJoin(",
        "QHttpServerResponse HandleSessionInvite(",
        "bool HasActiveInvitation(const SharedState& shared",
        "QWriteLocker lk(&shared.sessionsLock);",
    ):
        if required not in source:
            raise ValueError("V47 missing server session authorization context: " + required)
    source = once(source, '#include "webapi_routes_session.h"\n',
                  '#include "webapi_routes_session.h"\n#include "sh_friends_permissions.hpp"\n',
                  "include")
    source = once(source, JOIN_ANCHOR, JOIN_GUARD + JOIN_ANCHOR,
                  "private session join")
    source = once(source, INVITE_ANCHOR, INVITE_GUARD + INVITE_ANCHOR,
                  "private session invitation")
    source = once(source, "        s.members.append(m);\n",
                  "        s.members.append(m);\n" + JOIN_CONSUME,
                  "consume private invitations on successful join")
    return source

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("session", type=Path)
    args = parser.parse_args()
    original = args.session.read_text(encoding="utf-8")
    args.session.write_text(transform(original), encoding="utf-8")
    print("SHYT_V47_PRIVATE_FRIEND_SESSION_GATES_PATCHED")
