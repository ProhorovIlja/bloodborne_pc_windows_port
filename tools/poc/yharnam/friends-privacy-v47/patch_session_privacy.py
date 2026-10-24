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
# Authorize outstanding private invites only while the original inviter
# remains this world's owner. Transfer of host invalidates stale invitations.
INVITE_OWNER_FN = "bool HasActiveInvitation(const SharedState& shared, const QString& sessionId, int64_t userId) {\n"
INVITE_OWNER_START = """    // SHYT-V51-INVITE-CURRENT-HOST: fail closed on owner migration.
    const auto activeSession = shared.sessions.constFind(sessionId);
    if (activeSession == shared.sessions.constEnd())
        return false;
"""
INVITE_OWNER_LOOP = """        if (activeSession->sessionPrivacy == QStringLiteral("private") &&
            inv.fromUserId != activeSession->ownerUserId)
            continue;
"""
INVITE_GUARD = """        // SHYT-V51-HOST-ONLY-PRIVATE-INVITE: the owner controls private
        // guest admission. Other members cannot invite without an explicitly
        // authorized future host setting. Public sessions are unchanged.
        const bool senderIsOwner = sit->ownerUserId == *auth.userId;
        if (!SeamlessHunt::Friends::MaySendSessionInvite(
                sit->sessionPrivacy == QStringLiteral("private"), senderIsOwner)) {
            return JsonError(QHttpServerResponse::StatusCode::Forbidden,
                             SESSION_NOT_PERMITTED,
                             QStringLiteral("Only the session owner may invite to a private session"));
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
    source = once(source, INVITE_OWNER_FN, INVITE_OWNER_FN + INVITE_OWNER_START,
                  "validate current session owner for invitations")
    source = once(source,
                  "        if (inv.validUntil != 0 && nowMs > inv.validUntil)\n",
                  INVITE_OWNER_LOOP + "        if (inv.validUntil != 0 && nowMs > inv.validUntil)\n",
                  "revoke former owner's outstanding private invitations")
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
