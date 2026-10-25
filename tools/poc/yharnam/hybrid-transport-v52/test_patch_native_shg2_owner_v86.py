#!/usr/bin/env python3
"""V86 regression: real game owner source transformation fail-closed."""
import importlib.util
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("v86patch",HERE/"patch_native_shg2_owner_v86.py")
patch=importlib.util.module_from_spec(spec)
spec.loader.exec_module(patch)

# Synthetic V82+V83 excerpts mirror the real pinned game insertions, and
# deliberately exclude any game socket send/rx behavior.
FIXTURE='''// SHYT-V82-NATIVE-GRANT-INBOX
// SHYT-V83-NATIVE-TLS-LOCAL-CLIENT
#ifdef SHYT_ENABLE_TEST_LOCAL_MTLS
#include "core/libraries/network/sh_native_tls_local_client.hpp" // SHYT-V83-NATIVE-TLS-LOCAL-CLIENT
#endif
    SeamlessHunt::Hybrid::NativeSealedGrantInbox native_grant_inbox{};
    void Stop() {
        {
            std::lock_guard grant_lock(native_grant_mutex);
            native_grant_inbox.Revoke(); // socket shutdown: erase key & peer
        }
    }
    void Configure() {
        {
            std::lock_guard grant_lock(native_grant_mutex);
            native_grant_inbox.Revoke(); // account/server change: invalidate
        }
    }
#ifdef SHYT_ENABLE_TEST_LOCAL_MTLS
public:
    bool TryLocalTlsOfferForTest() { return false; }
private:
#endif
private:
    P2PTransport() = default;

    static bool TrustedReverseDirectReady(
'''
class V86Tests(unittest.TestCase):
    def test_owner_separate_protocol_inert_dev_only(self):
        result=patch.patch_game(FIXTURE)
        self.assertEqual(result.count(patch.TAG),1)
        self.assertEqual(result.count("native_grant_inbox_v84.Revoke();"),2)
        self.assertIn("NativeSealedGrantInboxV84 native_grant_inbox_v84{};",result)
        self.assertIn("NativeTlsLocalOfferClientV85::Request(",result)
        self.assertIn("TryLocalShg2OfferForTest(",result)
        self.assertIn("SHYT_ENABLE_TEST_LOCAL_MTLS",result)
        self.assertIn("NativeSealedGrantInbox native_grant_inbox{};",result)
        self.assertIn("TryLocalTlsOfferForTest()",result)
        self.assertEqual(result.count("private:\n#endif\nprivate:\n"),1)
        self.assertNotIn("direct_egress.Arm(",result)
        self.assertNotIn("SendFrame(",result)
        with self.assertRaisesRegex(ValueError,"already applied"):
            patch.patch_game(result)

    def test_mandatory_lifecycle_and_owner_fail_closed(self):
        wrong=(
            FIXTURE.replace("SHYT-V82-NATIVE-GRANT-INBOX",""),
            FIXTURE.replace("SHYT-V83-NATIVE-TLS-LOCAL-CLIENT","",2),
            FIXTURE.replace("socket shutdown: erase key & peer","socket stop"),
            FIXTURE.replace("account/server change: invalidate","reconfigure"),
            FIXTURE.replace("NativeSealedGrantInbox native_grant_inbox{};",""),
            FIXTURE.replace("P2PTransport() = default;","P2PTransport() noexcept = default;"),
            FIXTURE.replace("private:\n#endif\nprivate:\n","private:\n#endif\n"),
        )
        for source in wrong:
            with self.subTest(kind=source[-70:]):
                with self.assertRaises(ValueError):
                    patch.patch_game(source)

if __name__=="__main__":
    unittest.main()
