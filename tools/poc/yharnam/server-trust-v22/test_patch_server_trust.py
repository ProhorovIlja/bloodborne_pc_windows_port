import unittest
from patch_server_trust import boards,world,world_h
B='''#include <algorithm>
        std::uint32_t damage = 0;
                    damage += hit.damage();
'''
W='''#include "bloodborne_world.h"
    case bbcoop::Envelope::kVitals: {
        if (const bbcoop::Vitals& vitals = envelope.vitals();
            vitals.map() != 0 && (vitals.vital() == 1 || vitals.vital() == 2) &&
            vitals.has_at()) { // up or down where it stands
    const QByteArray party = QByteArray::fromStdString(hello.party()).trimmed();
    if (hello.protocol() != CoopProtocol) {
    if (hello.protocol() != CoopProtocol || hello.member().empty()) {
'''
H='''        bool enemy_owner = false;'''
class TestServerTrust(unittest.TestCase):
    def test_server_ingress_before_unsafe_store(self):
        x=world(W);self.assertIn('SafeVitalValues(values)',x)
        self.assertLess(x.index('if (!valid)'),x.index('if (const bbcoop::Vitals& vitals'))
        self.assertIn('ShouldAudit(now_ms',x)
        self.assertIn('SafeReviveHits(',x)
        self.assertIn('SafeWireText(hello.party(), 512)',x)
        self.assertIn('SafeWireText(hello.member(), 96)',x)
        self.assertIn('SafeWireText(hello.name(), 192)',x)
    def test_damage_cannot_overflow(self):
        x=boards(B);self.assertIn('AddReviveDamage(damage, hit.damage())',x)
        self.assertNotIn('damage += hit.damage()',x)
    def test_no_per_packet_global_state(self):
        x=world_h(H);self.assertIn('rejected_vitals = 0',x)
        self.assertIn('last_invalid_vitals_log_ms',x)
    def test_source_drift_fails_closed(self):
        with self.assertRaisesRegex(ValueError,'vitals ingress'):
            world(W.replace('case bbcoop::Envelope::kVitals:', 'case bbcoop::Envelope::kVitalsV2:'))
        with self.assertRaisesRegex(ValueError,'saturating revive'):
            boards(B.replace('damage += hit.damage()', 'damage -= hit.damage()'))
    def test_double_apply_fails(self):
        with self.assertRaisesRegex(ValueError,'already applied'):
            world(world(W))
        with self.assertRaisesRegex(ValueError,'already applied'):
            boards(boards(B))
if __name__=='__main__':unittest.main()
