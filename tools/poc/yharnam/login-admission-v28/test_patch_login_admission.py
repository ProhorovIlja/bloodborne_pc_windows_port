import unittest
from patch_login_admission import patch_link_cpp, patch_link_h, patch_test
CPP = '''    const auto hello = DecodeHello(datagram);
    if (!hello) {
        return;
    }
    QByteArray refusal;'''
HEADER = '#include <map>\n    int pair_lines;'
TEST = '''using namespace ServerLink;\nint Relays() {
      ChangedAccountOnSameEndpoint() != 0 || Relays() != 0 ||'''

class TestV28(unittest.TestCase):
    def test_before_signin(self):
        s=patch_link_cpp(CPP)
        self.assertIn('SH-LOGIN-ADMISSION-V28', s)\n        self.assertIn('new (std::nothrow)',s)\n        self.assertIn('!hello_admission->Allow',s)\n        self.assertIn('if (!hello_admission)',s)
        self.assertLess(s.index('hello_admission->Allow'),s.index('QByteArray refusal;'))
        self.assertIn('from.ipv4',s)
    def test_no_dynamic_per_source_allocation(self):
        s=patch_link_h(HEADER)
        self.assertIn('std::unique_ptr<SeamlessHunt::LoginAdmission::Gate> hello_admission',s)\n        self.assertIn('#include <memory>',s)\n        self.assertIn('#include <new>',s)
        self.assertIn('sh_login_admission.hpp',s)
    def test_real_qt_hub_regression_included(self):
        s=patch_test(TEST)
        self.assertIn('HelloAdmissionLimitsDbCalls()',s)\n        self.assertIn('static_assert(sizeof(Hub) < 16384',s)
        self.assertIn('sign_in_calls == 9',s)
    def test_drift_refused(self):
        with self.assertRaisesRegex(ValueError,'before SignIn'):
            patch_link_cpp(CPP.replace('DecodeHello(datagram)','DecodeHello(bytes)'))
    def test_double_apply_refused(self):
        with self.assertRaisesRegex(ValueError,'already applied'):
            patch_link_cpp(patch_link_cpp(CPP))
if __name__=='__main__': unittest.main()
