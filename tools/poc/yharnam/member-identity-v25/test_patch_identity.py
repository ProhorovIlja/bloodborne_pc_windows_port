import unittest
from patch_identity import patch_world,patch_link
WORLD='''#include "bloodborne_world.h"
    // The same run saying hello again (a guest whose game took the session host's role: phase 7).
    const bool arrived = member.lobby.empty();
'''
LINK='''#include "server_link.h"
    if (refusal.isEmpty() && sign_in && !sign_in(hello->online_id, hello->secret)) {
'''
class Tests(unittest.TestCase):
    def test_check_claims_before_server_acceptance(self):
        x=patch_world(WORLD)
        self.assertEqual(x.count('Identity::Matches('),2)
        self.assertLess(x.index('Identity::Matches('),x.index('// The same run saying hello again'))
        self.assertIn('lobby identity does not match',x)
    def test_strict_server_requires_real_auth(self):
        x=patch_link(LINK)
        self.assertIn('StrictMode() && !sign_in',x)
        self.assertLess(x.index('StrictMode() && !sign_in'),x.index('sign_in && !sign_in'))
    def test_fail_on_source_drift(self):
        with self.assertRaisesRegex(ValueError,'lobby member claim'):
            patch_world(WORLD.replace('member.lobby.empty()', 'member.lobby.size()==0'))
        with self.assertRaisesRegex(ValueError,'strict auth prerequisite'):
            patch_link(LINK.replace('refusal.isEmpty() && sign_in','sign_in'))
    def test_idempotency_refused(self):
        with self.assertRaisesRegex(ValueError,'already applied'):
            patch_world(patch_world(WORLD))
if __name__=='__main__':unittest.main()
