#!/usr/bin/env python3
"""V86: attach the V85 SHG2 full-identity inbox to original native P2PTransport.

DEV ONLY, behind existing SHYT_ENABLE_TEST_LOCAL_MTLS OFF-by-default.
No gameplay Direct Arm, no automatic TLS connection, no new native socket.
An external trusted game identity resolver is still required by the caller.
Exact V82/V83 source anchors and double-application guard fail closed.
"""
from __future__ import annotations
NETWORK="emulator/src/core/libraries/network/p2p_sockets.cpp"
TAG="SHYT-V86-NATIVE-FULL-ID-TLS"

def one(source, before, after, reason, occurrences=1):
    found=source.count(before)
    if found != occurrences:
        raise ValueError(f"V86 {reason}: pinned game source drift ({found}, expected {occurrences})")
    return source.replace(before,after,occurrences)

def patch_game(source):
    if TAG in source:
        raise ValueError("V86 already applied")
    # Old V82/83 code must be present; source-only may not precede these.
    if ("SHYT-V82-NATIVE-GRANT-INBOX" not in source or
        "SHYT-V83-NATIVE-TLS-LOCAL-CLIENT" not in source):
        raise ValueError("V86 requires verified V82 and V83 native game integration")
    source=one(source,
        '#include "core/libraries/network/sh_native_tls_local_client.hpp" // SHYT-V83-NATIVE-TLS-LOCAL-CLIENT\n',
        '#include "core/libraries/network/sh_native_tls_local_client.hpp" // SHYT-V83-NATIVE-TLS-LOCAL-CLIENT\n'
        '#include "core/libraries/network/sh_native_tls_local_client_v85.hpp" // '+TAG+'\n',
        "dev-only full SHA256 mTLS client include")
    source=one(source,
        '    SeamlessHunt::Hybrid::NativeSealedGrantInbox native_grant_inbox{};\n',
        '    SeamlessHunt::Hybrid::NativeSealedGrantInbox native_grant_inbox{};\n'
        '#ifdef SHYT_ENABLE_TEST_LOCAL_MTLS\n'
        '    SeamlessHunt::Hybrid::NativeSealedGrantInboxV84 native_grant_inbox_v84{};\n'
        '#endif\n',
        "separate game-owned full-width inbox")
    # Both old grant revocation sites are already scoped under the lock.
    source=one(source,
        '            native_grant_inbox.Revoke(); // socket shutdown: erase key & peer\n',
        '            native_grant_inbox.Revoke(); // socket shutdown: erase key & peer\n'
        '#ifdef SHYT_ENABLE_TEST_LOCAL_MTLS\n'
        '            native_grant_inbox_v84.Revoke(); // V86 logout/sockets closed\n'
        '#endif\n',
        "transport shutdown revocation")
    source=one(source,
        '            native_grant_inbox.Revoke(); // account/server change: invalidate\n',
        '            native_grant_inbox.Revoke(); // account/server change: invalidate\n'
        '#ifdef SHYT_ENABLE_TEST_LOCAL_MTLS\n'
        '            native_grant_inbox_v84.Revoke(); // V86 account/server change\n'
        '#endif\n',
        "server/account reconfigure revocation")
    method='''    // V86: controlled same-loopback SHG2 test only. The caller MUST use
    // real trusted current game state and invoke off the game's UDP thread.
    // NEVER auto-connect or change SendFrame / UDP routing here.
    bool TryLocalShg2OfferForTest(
        const SeamlessHunt::Hybrid::NativeTlsLocalConfig& cfg,
        const SeamlessHunt::Hybrid::NativeOfferIdentityV84& expected,
        std::uint64_t serial,
        SeamlessHunt::Hybrid::RefreshNativeOfferIdentityV84 current,
        void* verified_game_state,std::uint64_t now_ms) {
        std::lock_guard lock(native_grant_mutex);
        return SeamlessHunt::Hybrid::NativeTlsLocalOfferClientV85::Request(
            cfg,native_grant_inbox_v84,expected,serial,current,
            verified_game_state,now_ms);
    }
'''
    source=one(source,
        '''private:
#endif
private:
    P2PTransport() = default;

    static bool TrustedReverseDirectReady(''',
        method+'''private:
#endif
private:
    P2PTransport() = default;

    static bool TrustedReverseDirectReady(''',
        "protected V83 public debug method adjacency")
    return source
