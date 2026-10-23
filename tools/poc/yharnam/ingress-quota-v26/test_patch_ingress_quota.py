import unittest
from patch_ingress_quota import world,world_h
W='''#include "bloodborne_world.h"
    for (const std::vector<u8>& message : messages) {
        if (const auto envelope = DecodeEnvelope(message)) {
'''
H='''#include "bloodborne_party_boards.h"
        bool enemy_owner = false;
'''
class TestQuota(unittest.TestCase):
    def test_before_protobuf_decode(self):
        s=world(W)
        self.assertLess(s.index('ingress.Accept('),s.index('DecodeEnvelope(message)'))
        self.assertIn('Identity::StrictMode()',s)
        self.assertIn('ShouldAudit(now_ms',s)
    def test_scoped_per_link(self):
        s=world_h(H)
        self.assertIn('Ingress::Budget ingress',s)
        self.assertIn('last_budget_notice_ms = 0',s)
    def test_source_drift_and_idempotency(self):
        with self.assertRaisesRegex(ValueError,'pre-decode budget'):
            world(W.replace('DecodeEnvelope(message)','DecodeEnvelope(payload)'))
        with self.assertRaisesRegex(ValueError,'already applied'):
            world(world(W))
if __name__=='__main__':unittest.main()
