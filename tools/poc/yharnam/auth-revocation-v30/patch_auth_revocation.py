#!/usr/bin/env python3
"""V30: revoke cached auth on database password rotation, ban or account deletion."""
from pathlib import Path

DB_H = 'server/src/database.h'
DB_CPP = 'server/src/database.cpp'
LINK_H = 'server/src/link_server.h'
LINK_CPP = 'server/src/link_server.cpp'
POLICY = 'server/src/sh_auth_revocation.hpp'
HERE = Path(__file__).resolve().parent

def one(s,old,new,label):
    n=s.count(old)
    if n!=1: raise ValueError(f'V30 {label}: expected 1 pinned anchor, got {n}')
    return s.replace(old,new,1)

def database_header(s):
    if 'SH-AUTH-REVOCATION-V30' in s: raise ValueError('V30 DB header already patched')
    return one(s, '''    std::optional<UserRecord> CheckUser(const QString& npid, const QString& password,
                                        const QString& token, bool checkToken);''',
     '''    std::optional<UserRecord> CheckUser(const QString& npid, const QString& password,
                                        const QString& token, bool checkToken);
    // SH-AUTH-REVOCATION-V30: cheap read-only lookup on a cached login; never
    // reruns the 100k-round password KDF for a valid unchanged account.
    struct CredentialStatus {
        QByteArray db_hash;
        bool banned = false;
    };
    std::optional<CredentialStatus> CurrentCredentialStatus(const QString& npid);''',
     'credential status API')

def database_cpp(s):
    if 'SH-AUTH-REVOCATION-V30' in s: raise ValueError('V30 DB cpp already patched')
    return one(s, '''std::optional<UserRecord> Database::CheckUser(const QString& npid, const QString& password,''',
    '''// SH-AUTH-REVOCATION-V30: lookup the current salted-hash stamp and ban
// without running the 100k-round password verification on each repeated Hello.
std::optional<Database::CredentialStatus> Database::CurrentCredentialStatus(const QString& npid) {
    QSqlQuery q(m_db);
    q.prepare("SELECT username,hash,banned FROM account WHERE username=? COLLATE NOCASE");
    q.addBindValue(npid);
    if (!Exec(q) || !q.next() || q.value(0).toString() != npid)
        return std::nullopt; // includes a DB read error: fail closed
    CredentialStatus current;
    current.db_hash = q.value(1).toByteArray();
    current.banned = q.value(2).toBool();
    if (current.db_hash.isEmpty()) return std::nullopt;
    return current;
}

std::optional<UserRecord> Database::CheckUser(const QString& npid, const QString& password,''',
    'read-only credential status')

def link_header(s):
    if 'SH-AUTH-REVOCATION-V30' in s: raise ValueError('V30 link header already patched')
    return one(s, '''    QHash<QByteArray, QByteArray> m_signedIn; // player id -> its secret's hash, once signed in''',
      '''    // SH-AUTH-REVOCATION-V30: bound hot cache must also remember the DB
    // credential stamp, never grant access from a client secret hash alone.
    struct VerifiedCredential {
        QByteArray secret_sha256;
        QByteArray db_hash_at_signin;
    };
    QHash<QByteArray, VerifiedCredential> m_signedIn;''',
      'cached credential representation')

def link_cpp(s):
    if 'SH-AUTH-REVOCATION-V30' in s: raise ValueError('V30 auth login already patched')
    s=one(s, '''#include "link_server.h"''',
          '''#include "link_server.h"
#include "sh_auth_revocation.hpp" // SH-AUTH-REVOCATION-V30''',
          'link policy include')
    s=one(s, '''    const auto known = m_signedIn.constFind(online_id);
    if (known != m_signedIn.constEnd())
        return *known == hash;
    const bool make = !m_shared->config || m_shared->config->IsMakingAccountsAtSignIn();''',
      '''    const auto known = m_signedIn.constFind(online_id);
    if (known != m_signedIn.constEnd()) {
        // A cached secret is not authorization: check today's DB account
        // record on EVERY cache hit. A cheap indexed SELECT (no password KDF).
        const auto current = m_db.CurrentCredentialStatus(QString::fromUtf8(online_id));
        if (!current || current->banned) {
            m_signedIn.remove(online_id);
            return false; // deleted, banned, or DB unavailable
        }
        const bool unchanged = current->db_hash == known->db_hash_at_signin;
        if (unchanged)
            return SeamlessHunt::AuthRevocation::CanTrustCache(
                true, false, true, known->secret_sha256 == hash);
        // Password was rotated: evict and check new secret against the DB.
        m_signedIn.remove(online_id);
    }
    const bool make = !m_shared->config || m_shared->config->IsMakingAccountsAtSignIn();''',
      'check live account status before cached login')
    s=one(s, '''    if (!user)
        return false;
    // SH-RPC-BUDGET-V29:''',
      '''    if (!user || user->banned)
        return false; // V30: banned accounts cannot sign in, even without cache
    // SH-RPC-BUDGET-V29:''', 'fresh sign-in ban enforcement')
    s=one(s, '''    m_signedIn.insert(online_id, hash);
    return true;''',
      '''    m_signedIn.insert(online_id, VerifiedCredential{hash, user->hash});
    return true;''', 'store DB stamp with secret')
    return s

def transform(src):
    return {DB_H: database_header(src[DB_H]),
            DB_CPP: database_cpp(src[DB_CPP]),
            LINK_H: link_header(src[LINK_H]),
            LINK_CPP: link_cpp(src[LINK_CPP]),
            POLICY: (HERE/'sh_auth_revocation.hpp').read_text('utf-8')}
