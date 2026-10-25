// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V91: same native verified V90 OpenSSL TLS 1.3 client, now returns signed
// receipt to the ORIGINAL Qt server ON THAT SAME mTLS socket.
// NO direct game datagrams, routing or production listener enabled.
#include "sh_native_tls_local_client_v90.hpp"

namespace SeamlessHunt::Hybrid {
class NativeTlsLocalOfferClientV91 final {
public:
    static bool Request(const NativeTlsLocalConfig& config,
                        NativeSealedGrantInboxV84& inbox,
                        const NativeOfferIdentityV84& expected,
                        std::uint64_t tls_serial,
                        RefreshNativeOfferIdentityV84 refresh,
                        void* verified_game_state,
                        std::uint64_t now_ms,
                        bool& server_both_ready,
                        std::uint8_t* nonsecret_test_stage=nullptr) {
        server_both_ready=false;
        return NativeTlsLocalOfferClientV90::Request(
            config,inbox,expected,tls_serial,refresh,verified_game_state,
            now_ms,nonsecret_test_stage,true,&server_both_ready);
    }
};
} // namespace SeamlessHunt::Hybrid
