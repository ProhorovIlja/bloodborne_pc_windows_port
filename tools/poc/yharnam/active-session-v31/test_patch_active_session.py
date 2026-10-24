import unittest
from patch_active_session import header,hub_cpp,server_cpp,tests
H='''#include <functional>
    void SetSignIn(SignIn sign_in) {
        this->sign_in = std::move(sign_in);
    }
    bool lost = false; // its sign-in session ended for this silence
    SignIn sign_in;'''
CPP='''    QList<quint64> gone;
    for (const Link& link : std::as_const(members)) {
        const qint64 gap = now_ms - link.last_heard_ms;
        if (gap > gone_ms) {
            gone.append(link.endpoint.Key());
        }
    }
Hub::Result Hub::Tick(qint64 now_ms) {
        TellOthers(link, MemberState::Gone, now_ms - link.last_heard_ms, result);
        result.gone.append(link.endpoint);'''
SERVER='''    m_link.SetSignIn([this](const QByteArray& online_id, const QByteArray& secret) {
        return SignIn(online_id, secret);
    });'''
T='''int Relays() {
      HelloAdmissionLimitsDbCalls() != 0 || Relays() != 0 ||'''
class Tests(unittest.TestCase):
    def test_bounded_status_scans(self):
        s=hub_cpp(CPP)
        self.assertIn('account_checks',s)
        self.assertIn('CheckNow(',s)
        self.assertIn('result.retired_online_ids.append(link.online_id);',s)
        self.assertLess(s.index('Unlink(key);'),s.index('result.retired_online_ids')) if 'Unlink(key);' in s else None
    def test_explicit_staging_opt_in(self):
        self.assertIn('ActiveSession::Enabled()',server_cpp(SERVER))
        self.assertIn('CurrentCredentialStatus(',server_cpp(SERVER))
    def test_header_and_qt_test(self):
        self.assertIn('SetActiveAccountAllowed',header(H))
        self.assertIn('RevokedActiveAccountExitsWorld()',tests(T))
    def test_anchor_drift(self):
        with self.assertRaisesRegex(ValueError,'bounded verification tick'):
            hub_cpp(CPP.replace('std::as_const(members)','std::as_const(sessions)'))
    def test_reapply(self):
        with self.assertRaisesRegex(ValueError,'already applied'):
            hub_cpp(hub_cpp(CPP))
if __name__=='__main__': unittest.main()
