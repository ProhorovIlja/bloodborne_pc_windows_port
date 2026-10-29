import importlib.util
from pathlib import Path
import unittest

path=Path(__file__).with_name("patch_native_game_aead_drop_guard.py")
spec=importlib.util.spec_from_file_location("shyt_shy2_drop_guard",path)
patch=importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)
INBOUND='''#include "sh_native_direct_rx.hpp" // SHYT-V70-NATIVE-RECV-HMAC
void ReceiveMain() {
            if (SeamlessHunt::Hybrid::IsSHP1(datagram)) {
                SeamlessHunt::Hybrid::NativeRxResult verified{};
                // HMAC path
                continue;
            }
            if (!Link::TakesDatagramFrom(LinkServer(), from.sin_addr.s_addr, from.sin_port)) {
                continue;
            }
}'''

class NativeEncryptedDemux(unittest.TestCase):
    def test_shy2_is_consumed_before_hmac_and_shadnet(self):
        result=patch.patch_game(INBOUND)
        self.assertIn(patch.TAG,result)
        idx=result.index("SHYT-SHY2-UNARMED-DROP")
        self.assertLess(idx,result.index("IsSHP1(datagram)"))
        self.assertLess(idx,result.index("Link::TakesDatagramFrom("))
        self.assertEqual(result.count("if (!Link::TakesDatagramFrom("),1)
        self.assertIn("datagram[3] == '2'",result)
        self.assertIn("continue;\n            }\n            if (SeamlessHunt::Hybrid::IsSHP1",result)
    def test_does_not_arm_crypto_or_change_legacy(self):
        result=patch.patch_game(INBOUND)
        self.assertNotIn("direct_ingress.Arm(",result)
        self.assertNotIn("NativeGameAeadOpener",result)
        self.assertIn("// HMAC path",result)
    def test_original_code_or_second_install_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"requires original V70"):
            patch.patch_game("if (SeamlessHunt::Hybrid::IsSHP1(datagram)) {}")
        with self.assertRaisesRegex(ValueError,"already installed"):
            patch.patch_game(patch.patch_game(INBOUND))
    def test_source_drift_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"anchor drift"):
            patch.patch_game(INBOUND.replace("verified{};","verified;"))
        with self.assertRaisesRegex(ValueError,"anchor drift"):
            patch.patch_game(INBOUND+INBOUND)

if __name__=="__main__":
    unittest.main()
