import unittest
from patch_auth_revocation import database_header,database_cpp,link_header,link_cpp
DBH='''    std::optional<UserRecord> CheckUser(const QString& npid, const QString& password,
                                        const QString& token, bool checkToken);'''
DBC='''std::optional<UserRecord> Database::CheckUser(const QString& npid, const QString& password,'''
LH='''    QHash<QByteArray, QByteArray> m_signedIn; // player id -> its secret's hash, once signed in'''
LC='''#include "link_server.h"
    const auto known = m_signedIn.constFind(online_id);
    if (known != m_signedIn.constEnd())
        return *known == hash;
    const bool make = !m_shared->config || m_shared->config->IsMakingAccountsAtSignIn();
    if (!user)
        return false;
    // SH-RPC-BUDGET-V29:
    m_signedIn.insert(online_id, hash);
    return true;'''
class TestV30(unittest.TestCase):
    def test_cached_password_requires_db(self):
        s=link_cpp(LC)
        self.assertIn('CurrentCredentialStatus(',s)
        self.assertIn('current->banned',s)
        self.assertIn('db_hash_at_signin',s)
        self.assertIn('known->secret_sha256 == hash',s)
        self.assertIn('if (!user || user->banned)',s)
    def test_read_only_indexed_db_query(self):
        self.assertIn('SELECT username,hash,banned',database_cpp(DBC))
        self.assertIn('!Exec(q) || !q.next()',database_cpp(DBC))
        self.assertIn('struct CredentialStatus',database_header(DBH))
        self.assertIn('QHash<QByteArray, VerifiedCredential>',link_header(LH))
    def test_cached_wrong_secret_no_kdf(self):
        s=link_cpp(LC)
        self.assertLess(s.index('if (unchanged)'),s.index('const bool make ='))
    def test_drift_fail_closed(self):
        with self.assertRaisesRegex(ValueError,'cached credential representation'):
            link_header(LH.replace('QHash<QByteArray, QByteArray>','QMap<QByteArray, QByteArray>'))
    def test_second_application_rejected(self):
        with self.assertRaisesRegex(ValueError,'already patched'):
            link_cpp(link_cpp(LC))
if __name__=='__main__': unittest.main()
