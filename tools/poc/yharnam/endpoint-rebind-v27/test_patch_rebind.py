import unittest
from patch_rebind import transform
SOURCE='''#include "server_link.h"
    const bool again = members.contains(from.Key());
    Link& link = members[from.Key()];
'''
class Tests(unittest.TestCase):
    def test_cleanup_before_rebinding(self):
        s=transform(SOURCE)
        self.assertIn('MustRetire(',s)
        self.assertIn('TellOthers(prior, MemberState::Gone, 0, result);',s)
        self.assertIn('Unlink(from.Key());',s)
        self.assertIn('result.gone.append(prior.endpoint)',s)
        self.assertLess(s.index('Unlink(from.Key());'),s.index('Link& link = members[from.Key()];'))
    def test_source_drift_refusal(self):
        with self.assertRaisesRegex(ValueError,'identity-rebind cleanup'):
            transform(SOURCE.replace('members.contains(from.Key())','members.find(from.Key())'))
    def test_double_apply_refusal(self):
        with self.assertRaisesRegex(ValueError,'already applied'):
            transform(transform(SOURCE))
if __name__=='__main__':unittest.main()
