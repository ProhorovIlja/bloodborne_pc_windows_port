import unittest
from patch_bearer_auth import patch_auth,patch_db
AUTH='''    q.prepare(QStringLiteral("SELECT user_id, username FROM account WHERE token = ?"));'''
DB='''    qInfo() << "Database migrations complete";'''
class PinnedBearerHardening(unittest.TestCase):
    def test_banned_token_never_authenticates(self):
        s=patch_auth(AUTH)
        self.assertIn("WHERE token = ? AND banned = 0",s)
        self.assertIn("SH-V32-BEARER-BAN",s)
    def test_index_applies_to_existing_databases(self):
        s=patch_db(DB)
        self.assertIn('CREATE INDEX IF NOT EXISTS account_token_lookup ON account(token)',s)
        self.assertIn('if (!Exec(',s)
        self.assertIn('return false;',s)
    def test_drift_rejected(self):
        with self.assertRaisesRegex(ValueError,"token lookup banned status"):
            patch_auth(AUTH.replace("username","npid"))
    def test_double_apply_rejected(self):
        with self.assertRaisesRegex(ValueError,"already patched"):
            patch_auth(patch_auth(AUTH))
    def test_index_drift_rejected(self):
        with self.assertRaisesRegex(ValueError,"token index"):
            patch_db(DB.replace("Database migrations complete","Migrated"))
if __name__=="__main__":unittest.main()
