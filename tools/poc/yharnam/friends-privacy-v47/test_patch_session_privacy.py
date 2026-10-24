"""Offline regression for private friend-session gates in the pinned Qt WebAPI."""
import importlib.util
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("shyt_friend_private_v47",
                                               HERE / "patch_session_privacy.py")
p = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = p
spec.loader.exec_module(p)

# These are the precise, pinned downstream anchors; the full source is composed
# and compiled separately by the actual native Windows/Ubuntu server workflows.
SOURCE = """#include "webapi_routes_session.h"
bool HasActiveInvitation(const SharedState& shared, const QString& sessionId, int64_t userId) {
    return true;
}
QHttpServerResponse HandleSessionJoin(Database& db, SharedState& shared,
                                      const QString& sessionId, const QHttpServerRequest& req) {
    QWriteLocker lk(&shared.sessionsLock);
    {
        auto& s = sit.value();
        for (auto& m : s.members) {
            if (m.userId == *auth.userId) return QHttpServerResponse{};
        }
        if (s.sessionLockFlag) {
            return JsonError(QHttpServerResponse::StatusCode::Forbidden, SESSION_NOT_PERMITTED,
                             QStringLiteral("The session is locked"));
        }
    }
}
QHttpServerResponse HandleSessionInvite(Database& db, SharedState& shared,
                                        const QString& sessionId, const QHttpServerRequest& req) {
    QWriteLocker lk(&shared.sessionsLock);
    auto sit = shared.sessions.constFind(sessionId);
    if (sit == shared.sessions.constEnd()) return QHttpServerResponse{};
        const QStringList sessionPlatforms = sit->availablePlatforms;
        for (const auto& r : recipients) {
        }
}
"""

class PrivateSessionTests(unittest.TestCase):
    def test_join_requires_recipient_bound_live_invitation(self):
        patched = p.transform(SOURCE)
        join = patched.split("QHttpServerResponse HandleSessionJoin(", 1)[1].split(
            "QHttpServerResponse HandleSessionInvite(", 1)[0]
        self.assertIn("SHYT-V47-FRIENDS-PRIVATE-SESSION", join)
        self.assertIn("HasActiveInvitation(shared, sessionId, *auth.userId)", join)
        self.assertIn("MayJoinSession(", join)
        self.assertLess(join.index("MayJoinSession("), join.index("if (s.sessionLockFlag)"))
        self.assertIn("SESSION_NOT_PERMITTED", join)

    def test_private_invitation_requires_sender_already_in_session(self):
        patched = p.transform(SOURCE)
        invite = patched.split("QHttpServerResponse HandleSessionInvite(", 1)[1]
        self.assertIn("SHYT-V47-FRIENDS-PRIVATE-INVITE", invite)
        self.assertIn("member.userId == *auth.userId", invite)
        self.assertIn("MaySendSessionInvite(", invite)
        self.assertIn("Only session members may invite", invite)

    def test_nonprivate_behavior_and_existing_member_branch_stay_intact(self):
        patched = p.transform(SOURCE)
        self.assertIn("!privateSession || HasActiveInvitation(", patched)
        self.assertIn("if (m.userId == *auth.userId) return", patched)
        self.assertIn("if (s.sessionLockFlag)", patched)
        self.assertIn("const QStringList sessionPlatforms = sit->availablePlatforms;", patched)
        self.assertEqual(patched.count("#include \"sh_friends_permissions.hpp\""), 1)

    def test_source_drift_and_reapplication_fail_closed(self):
        changed = SOURCE.replace(p.JOIN_ANCHOR, "        if (s.closed) {\\n")
        with self.assertRaisesRegex(ValueError, "join"):
            p.transform(changed)
        changed = SOURCE.replace("        for (const auto& r : recipients) {",
                                 "        for (const auto& target : recipients) {")
        with self.assertRaisesRegex(ValueError, "invitation"):
            p.transform(changed)
        with self.assertRaisesRegex(ValueError, "already applied"):
            p.transform(p.transform(SOURCE))

if __name__ == "__main__":
    unittest.main()
