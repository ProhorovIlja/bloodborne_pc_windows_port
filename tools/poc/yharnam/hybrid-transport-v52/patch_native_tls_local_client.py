#!/usr/bin/env python3
"""V83: attach native LibreSSL/OpenSSL client as DEV-ONLY callable game method.

An opt-in CMake flag is required; no auto-connect and NO Direct Arm.
The TLS exchange reuses the original game's embedded LibreSSL dependency
through its existing Cpp_Httplib SSL transitive link.
"""
from __future__ import annotations
NETWORK="emulator/src/core/libraries/network/p2p_sockets.cpp"
HEADER="emulator/src/core/libraries/network/sh_native_tls_local_client.hpp"
CMAKE="emulator/CMakeLists.txt"
def one(s,a,b,label):
    n=s.count(a)
    if n!=1:raise ValueError(f"V83 {label}: expected one pinned anchor, got {n}")
    return s.replace(a,b,1)

def patch_game(src):
    if "SHYT-V83-NATIVE-TLS-LOCAL-CLIENT" in src:
        raise ValueError("V83 game already patched")
    src=one(src,
'''#include "core/libraries/network/sh_native_grant_inbox.hpp" // SHYT-V82-NATIVE-GRANT-INBOX
''',
'''#include "core/libraries/network/sh_native_grant_inbox.hpp" // SHYT-V82-NATIVE-GRANT-INBOX
#ifdef SHYT_ENABLE_TEST_LOCAL_MTLS
#include "core/libraries/network/sh_native_tls_local_client.hpp" // SHYT-V83-NATIVE-TLS-LOCAL-CLIENT
#endif
''',"game TLS header only in dev build")
    src=one(src,
'''private:
    P2PTransport() = default;

    static bool TrustedReverseDirectReady(''',
'''#ifdef SHYT_ENABLE_TEST_LOCAL_MTLS
public:
    // Explicit test call from trusted native game code ONLY. Synchronous;
    // caller must invoke from a worker, NEVER original UDP receive thread.
    // No launcher/network option or runtime automatic activation exists.
    bool TryLocalTlsOfferForTest(
        const SeamlessHunt::Hybrid::NativeTlsLocalConfig& cfg,
        const SeamlessHunt::Hybrid::NativeOfferIdentity& expected,
        std::uint64_t serial,
        SeamlessHunt::Hybrid::RefreshNativeOfferIdentity current,
        void* verified_game_state,std::uint64_t now_ms) {
        std::lock_guard lock(native_grant_mutex);
        return SeamlessHunt::Hybrid::NativeTlsLocalOfferClient::Request(
            cfg,native_grant_inbox,expected,serial,current,
            verified_game_state,now_ms);
    }
private:
#endif
private:
    P2PTransport() = default;

    static bool TrustedReverseDirectReady(''',"game transport controlled dev-only method")
    return src

def patch_cmake(src):
    if "SHYT_ENABLE_TEST_LOCAL_MTLS" in src:
        raise ValueError("V83 CMake already patched")
    return one(src,
'''target_link_libraries(shadps4 PRIVATE Freetype::Freetype)
''',
'''target_link_libraries(shadps4 PRIVATE Freetype::Freetype)
# SHYT V83: optional native TLS client test integration, NEVER ON in release.
# Existing Cpp_Httplib transitive dependency already owns bundled
# LibreSSL::SSL+Crypto; do not build or ship a second TLS stack.
option(SHYT_ENABLE_TEST_LOCAL_MTLS "Enable local-only internal native TLS offer developer test" OFF)
if(SHYT_ENABLE_TEST_LOCAL_MTLS)
    target_compile_definitions(shadps4 PRIVATE SHYT_ENABLE_TEST_LOCAL_MTLS)
endif()
''',"native game CMake opt-in OFF by default")
