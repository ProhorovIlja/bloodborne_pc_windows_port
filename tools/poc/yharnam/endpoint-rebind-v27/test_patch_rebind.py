import unittest
from patch_rebind import transform, transform_header, transform_server, transform_test
SOURCE='''#include "server_link.h"
    const bool again = members.contains(from.Key());
    Link& link = members[from.Key()];
'''
HEADER='''        QList<Endpoint> gone; // links forgotten'''
SERVER='''    // Phase 7: a linked game's address for the rooms and signaling is its virtual one, known from
    // its hello.
    for (const auto& linked : result.linked) {'''
QT_TEST='''int Relays() {
  if (Contracts() != 0 || HelloAndBuilds() != 0 || Relays() != 0 ||
'''
class Tests(unittest.TestCase):
    def test_cleanup_before_rebinding(self):
        s=transform(SOURCE)
        self.assertIn('MustRetire(',s)
        self.assertIn('TellOthers(prior, MemberState::Gone, 0, result);',s)
        self.assertIn('Unlink(from.Key());',s)
        self.assertIn('result.gone.append(prior.endpoint)',s)
        self.assertIn('result.retired_online_ids.append(prior.online_id)',s)
        self.assertIn('retired_online_ids',transform_header(HEADER))
        filtered=transform_server(SERVER)
        self.assertIn('matching.udpExt.remove(',filtered)
        self.assertLess(filtered.index('udpExt.remove('),filtered.index('for (const auto& linked'))
        self.assertLess(s.index('Unlink(from.Key());'),s.index('Link& link = members[from.Key()];'))
    def test_source_drift_refusal(self):
        with self.assertRaisesRegex(ValueError,'identity-rebind cleanup'):
            transform(SOURCE.replace('members.contains(from.Key())','members.find(from.Key())'))
    def test_real_qt_hub_regression(self):
        t=transform_test(QT_TEST)
        self.assertIn('ChangedAccountOnSameEndpoint()',t)
        self.assertIn('retired_online_ids',t)
        self.assertIn('VirtualEndpointOf("Kaniel")',t)
        self.assertIn('VirtualEndpointOf("Eileen")',t)
        self.assertIn('routes retired\\n',t)
        with self.assertRaisesRegex(ValueError,'Qt identity-switch test'):
            transform_test(QT_TEST.replace('int Relays() {','int RelaysChanged() {'))
    def test_matchmaking_drift_rejected(self):
        with self.assertRaisesRegex(ValueError,'matchmaking address cleanup'):
            transform_server(SERVER.replace('result.linked','result.linkers'))
    def test_double_apply_refusal(self):
        with self.assertRaisesRegex(ValueError,'already applied'):
            transform(transform(SOURCE))
if __name__=='__main__':unittest.main()
