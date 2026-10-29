import importlib.util
from pathlib import Path
import unittest

path=Path(__file__).with_name("patch_native_game_aead_drop_guard.py")
spec=importlib.util.spec_from_file_location("shyt_shy2_ingress_patch",path)
patch=importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)

ORIGINAL='''#include "core/libraries/network/sh_native_direct_rx.hpp" // SHYT-V70-NATIVE-RECV-HMAC
// SHYT-V87-TRUSTED-SERVER-LINK
    SeamlessHunt::Hybrid::NativeDirectReceiver direct_ingress{};
    void Stop() {
        {
            std::lock_guard direct_lock(direct_egress_mutex);
            direct_egress.RevokeAll();
        }
    }
    void SetServer() {
        {
            std::lock_guard direct_lock(direct_egress_mutex);
            direct_egress.RevokeAll();
        }
    }
    void ReceiveMain() {
            if (SeamlessHunt::Hybrid::IsSHP1(datagram)) {
                SeamlessHunt::Hybrid::NativeRxResult verified{};
                continue;
            }
            if (!Link::TakesDatagramFrom(LinkServer(), from.sin_addr.s_addr, from.sin_port)) {
                continue;
            }
    }
'''

class NativeEncryptedGameIngress(unittest.TestCase):
    def test_reuses_original_game_recvfrom_and_authoritative_delivery(self):
        out=patch.patch_game(ORIGINAL)
        self.assertEqual(out.count(patch.TAG),1)
        self.assertLess(out.index("IsSHY2(datagram)"),out.index("IsSHP1(datagram)"))
        self.assertLess(out.index("IsSHP1(datagram)"),out.index("Link::TakesDatagramFrom("))
        self.assertIn("native_shy2_ingress.Receive(",out)
        self.assertIn("Deliver(verified.sender.addr_nbo,verified.sender.port_nbo,",out)
        self.assertEqual(out.count("native_shy2_ingress.RevokeAll()"),2)
        self.assertNotIn("native_shy2_ingress.Arm(",out)
        self.assertEqual(out.count("direct_egress.RevokeAll()"),2)
        self.assertEqual(out.count("if (!Link::TakesDatagramFrom("),1)

    def test_original_and_duplicate_install_denied(self):
        with self.assertRaisesRegex(ValueError,"missing original game"):
            patch.patch_game("int main() {}")
        twice=patch.patch_game(ORIGINAL)
        with self.assertRaisesRegex(ValueError,"already installed"):
            patch.patch_game(twice)

    def test_missing_revoke_or_duplicate_demux_denied(self):
        with self.assertRaisesRegex(ValueError,"both original game revoke"):
            patch.patch_game(ORIGINAL.replace("direct_egress.RevokeAll();","",1))
        with self.assertRaisesRegex(ValueError,"pinned anchors"):
            patch.patch_game(ORIGINAL+ORIGINAL)
        with self.assertRaisesRegex(ValueError,"pinned anchors"):
            patch.patch_game(ORIGINAL.replace("verified{};","verified;"))

if __name__=="__main__":
    unittest.main()
