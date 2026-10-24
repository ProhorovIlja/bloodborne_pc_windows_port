#!/usr/bin/env python3
"""V31 opt-in bounded active-account revocation and stale matchmaking cleanup."""
from pathlib import Path

LINK_CPP='server/src/server_link.cpp'
LINK_H='server/src/server_link.h'
SERVER_CPP='server/src/link_server.cpp'
SERVER_H='server/src/link_server.h'
QT_TEST='server/tests/test_server_link.cpp'
POLICY='server/src/sh_active_session.hpp'
HERE=Path(__file__).resolve().parent

def one(s,old,new,label):
    count=s.count(old)
    if count!=1: raise ValueError(f'V31 {label}: expected exactly one pinned anchor, got {count}')
    return s.replace(old,new,1)

def header(s):
    if 'SH-ACTIVE-SESSION-V31' in s: raise ValueError('V31 already applied Hub header')
    s=one(s,'#include <functional>',
          '#include <functional>\n#include "sh_active_session.hpp" // SH-ACTIVE-SESSION-V31',
          'policy include')
    s=one(s,
'''    void SetSignIn(SignIn sign_in) {
        this->sign_in = std::move(sign_in);
    }''',
'''    void SetSignIn(SignIn sign_in) {
        this->sign_in = std::move(sign_in);
    }
    // A separate read-only status callback, not a new authentication path.
    using ActiveAccountAllowed = std::function<bool(const QByteArray&)>;
    void SetActiveAccountAllowed(ActiveAccountAllowed callback) {
        active_account_allowed = std::move(callback);
    }''', 'active account callback')
    s=one(s,'    bool lost = false; // its sign-in session ended for this silence',
'''    bool lost = false; // its sign-in session ended for this silence
        qint64 last_account_check_ms = -1;''','monotonic per-link validation clock')
    return one(s,'    SignIn sign_in;',
'''    SignIn sign_in;
    ActiveAccountAllowed active_account_allowed;''','callback storage')

def hub_cpp(s):
    if 'SH-ACTIVE-SESSION-V31' in s: raise ValueError('V31 already applied Hub cpp')
    s=one(s,'Hub::Result Hub::Tick(qint64 now_ms) {',
'''// SH-ACTIVE-SESSION-V31: bounded index-backed SQLite checks per tick.
Hub::Result Hub::Tick(qint64 now_ms) {''','tick marker')
    s=one(s,
'''    QList<quint64> gone;
    for (const Link& link : std::as_const(members)) {
        const qint64 gap = now_ms - link.last_heard_ms;
        if (gap > gone_ms) {
            gone.append(link.endpoint.Key());
        }
    }''',
'''    QList<quint64> gone;
    unsigned account_checks = 0;
    for (Link& link : members) {
        const qint64 gap = now_ms - link.last_heard_ms;
        if (gap > gone_ms) {
            gone.append(link.endpoint.Key());
        } else if (active_account_allowed &&
                   SeamlessHunt::ActiveSession::CheckNow(
                       link.last_account_check_ms, now_ms, account_checks)) {
            ++account_checks;
            link.last_account_check_ms = now_ms;
            if (!active_account_allowed(link.online_id)) {
                result.log.append(QStringLiteral("server link: active account revoked: %1")
                                      .arg(QString::fromUtf8(link.online_id)));
                gone.append(link.endpoint.Key());
            }
        }
    }''', 'bounded verification tick')
    s=one(s,
'''        TellOthers(link, MemberState::Gone, now_ms - link.last_heard_ms, result);
        result.gone.append(link.endpoint);''',
'''        TellOthers(link, MemberState::Gone, now_ms - link.last_heard_ms, result);
        result.gone.append(link.endpoint);
        // Every true disconnect must retire virtual matchmaking metadata.
        result.retired_online_ids.append(link.online_id);''','normal logout matchmaking')
    return s

def server_header(s):
    if 'SH-ACTIVE-SESSION-V31' in s: raise ValueError('V31 already applied LinkServer header')
    return one(s,
        '    QHash<QByteArray, VerifiedCredential> m_signedIn;',
        '''    QHash<QByteArray, VerifiedCredential> m_signedIn;
    // Active link credential stamps survive eviction from V30's bounded
    // login cache and are removed together with the retired linked account.
    QHash<QByteArray, QByteArray> m_activeDbStamps;''',
        'per-active-link account snapshot')

def server_cpp(s):
    if 'SH-ACTIVE-SESSION-V31' in s: raise ValueError('V31 already applied LinkServer cpp')
    s=one(s,
'''    m_link.SetSignIn([this](const QByteArray& online_id, const QByteArray& secret) {
        return SignIn(online_id, secret);
    });''',
'''    m_link.SetSignIn([this](const QByteArray& online_id, const QByteArray& secret) {
        return SignIn(online_id, secret);
    });
    // SH-ACTIVE-SESSION-V31: only the test server opt-in installs status
    // polling. Hub checks <=8 accounts / 500ms tick, <=1/player/15 seconds.
    if (SeamlessHunt::ActiveSession::Enabled()) {
        m_link.SetActiveAccountAllowed([this](const QByteArray& id) {
            const auto current = m_db.CurrentCredentialStatus(QString::fromUtf8(id));
            if (!current || current->banned) return false;
            const auto linked = m_activeDbStamps.constFind(id);
            // Absence of an active stamp is not proof of a clean session.
            return linked != m_activeDbStamps.constEnd() &&
                   *linked == current->db_hash;
        });
    }''', 'bounded live DB callback')
    s=one(s,
'''    for (const QByteArray& retired : result.retired_online_ids) {
        QWriteLocker lk(&m_shared->matching.udpLock);
        m_shared->matching.udpExt.remove(QString::fromUtf8(retired));
    }''',
'''    for (const QByteArray& retired : result.retired_online_ids) {
        QWriteLocker lk(&m_shared->matching.udpLock);
        m_shared->matching.udpExt.remove(QString::fromUtf8(retired));
        m_activeDbStamps.remove(retired); // drop the retired session fingerprint
    }''',
        'retire active credential on disconnect')
    s=one(s,
'''    for (const auto& linked : result.linked) {''',
'''    for (const auto& linked : result.linked) {
        // OnHello has already authenticated this online_id via V30 SignIn.
        const auto auth = m_signedIn.constFind(linked.online_id);
        if (auth != m_signedIn.constEnd())
            m_activeDbStamps.insert(linked.online_id, auth->db_hash_at_signin);''',
        'pin credential stamp at authenticated link')
    return s

def tests(s):
    if 'SH-ACTIVE-SESSION-V31' in s: raise ValueError('V31 already applied Qt Hub test')
    s=one(s,'int Relays() {',
'''// SH-ACTIVE-SESSION-V31: true account revocation disconnects and retires
// matchmaking entries; silence disconnects also retire them.
int RevokedActiveAccountExitsWorld() {
  Hub hub;
  hub.Receive(Kaniel, HelloFrom("Kaniel"), 0);
  hub.Receive(Ada, HelloFrom("Ada"), 0);
  hub.SetActiveAccountAllowed([](const QByteArray& id) {
    return id != QByteArray("Kaniel");
  });
  const auto revoked = hub.Tick(500);
  CHECK(hub.Members() == 1);
  CHECK(revoked.gone.contains(Kaniel));
  CHECK(revoked.retired_online_ids.contains(QByteArray("Kaniel")));
  CHECK(!revoked.gone.contains(Ada));
  const auto stale = hub.Tick(61000);
  CHECK(stale.gone.contains(Ada));
  CHECK(stale.retired_online_ids.contains(QByteArray("Ada")));
  CHECK(hub.Members() == 0);
  return 0;
}

int Relays() {''','Qt Hub revocation scenario')
    return one(s,
'''      HelloAdmissionLimitsDbCalls() != 0 || Relays() != 0 ||''',
'''      HelloAdmissionLimitsDbCalls() != 0 ||
      RevokedActiveAccountExitsWorld() != 0 || Relays() != 0 ||''',
'execute revocation scenario')

def transform(src):
    return {LINK_H:header(src[LINK_H]),
            LINK_CPP:hub_cpp(src[LINK_CPP]),
            SERVER_CPP:server_cpp(src[SERVER_CPP]),
            SERVER_H:server_header(src[SERVER_H]),
            QT_TEST:tests(src[QT_TEST]),
            POLICY:(HERE/'sh_active_session.hpp').read_text('utf-8')}
