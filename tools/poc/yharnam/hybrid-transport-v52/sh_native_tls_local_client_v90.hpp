// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V90 actual native OpenSSL/LibreSSL client -> SAME Qt test-only TLS1.3
// server for one half of coordinated full-identity SHG2 pair. Does not enable Direct.
// Requires external trusted native account state; no public remote listener.
#include "sh_native_tls_local_client.hpp" // reuse verified TLS transport
#include "sh_native_grant_inbox_v84.hpp"
#include "sh_pair_ready_v91.hpp" // separate mTLS possession proof

namespace SeamlessHunt::Hybrid {
class NativeTlsLocalOfferClientV90 final {
public:
    // Explicit TEST-only synchronous request. Run outside the native game
    // UDP receive thread, holding the existing transport's grant mutex.
    // The caller MUST obtain expected from an authentic *current game*
    // state and refresh it on each inbox operation. This class cannot
    // authenticate an arbitrary client-supplied account/peer name.
    static bool Request(const NativeTlsLocalConfig& config,
                        NativeSealedGrantInboxV84& inbox,
                        const NativeOfferIdentityV84& expected,
                        std::uint64_t tls_serial,
                        RefreshNativeOfferIdentityV84 refresh,
                        void* trusted_game_state,
                        std::uint64_t now_ms,
                        std::uint8_t* nonsecret_test_stage=nullptr,
                        bool send_ready_proof=false,
                        bool* both_received_ready=nullptr,
                        std::uint64_t v102_pair_id=0) {
        // Test diagnostics report only milestone numbers, NEVER peer IP,
        // TLS keys, certificate contents, access tokens or secret bytes.
        if(nonsecret_test_stage)*nonsecret_test_stage=0;
        if(both_received_ready)*both_received_ready=false;
        // In particular, no remote endpoint can be configured through
        // this incomplete prototype. No 31313/31314/31315 traffic changes.
        inbox.Revoke();
        if(config.server_ca_pem.empty() || config.client_cert_pem.empty() ||
           config.client_key_pem.empty() || !config.localhost_port ||
           !tls_serial || !refresh || !trusted_game_state)return false;
        if(nonsecret_test_stage)*nonsecret_test_stage=1;
        LocalTlsDetail::SocketPlatform net;
        if(!net.ready)return false;
        LocalTlsDetail::SslCtxOwner context;
        context.p=SSL_CTX_new(TLS_client_method());
        if(!context.p)return false;
        if(SSL_CTX_set_min_proto_version(context.p,TLS1_3_VERSION)!=1 ||
           SSL_CTX_set_max_proto_version(context.p,TLS1_3_VERSION)!=1)
            return false;
        SSL_CTX_set_verify(context.p,SSL_VERIFY_PEER,nullptr);
        if(SSL_CTX_load_verify_locations(context.p,
               config.server_ca_pem.c_str(),nullptr)!=1 ||
           SSL_CTX_use_certificate_file(context.p,
               config.client_cert_pem.c_str(),SSL_FILETYPE_PEM)!=1 ||
           SSL_CTX_use_PrivateKey_file(context.p,
               config.client_key_pem.c_str(),SSL_FILETYPE_PEM)!=1 ||
           SSL_CTX_check_private_key(context.p)!=1)
            return false;

        if(nonsecret_test_stage)*nonsecret_test_stage=2;
        LocalTlsDetail::SocketOwner socket;
        socket.fd=LocalTlsDetail::OpenLocal(config.localhost_port);
        if(socket.fd==LocalTlsDetail::Invalid)return false;
        if(nonsecret_test_stage)*nonsecret_test_stage=3;
        LocalTlsDetail::SslOwner tls;
        tls.p=SSL_new(context.p);
        if(!tls.p)return false;
        // X.509 IP SAN verification is essential. Merely trusting
        // the certificate chain is insufficient to authenticate server.
        if(X509_VERIFY_PARAM_set1_ip_asc(SSL_get0_param(tls.p),
                                         "127.0.0.1")!=1)
            return false;
#ifdef _WIN32
        // OpenSSL BIO socket descriptor must fit its int API on this path.
        if(socket.fd>static_cast<LocalTlsDetail::Socket>(INT_MAX))return false;
#endif
        if(SSL_set_fd(tls.p,static_cast<int>(socket.fd))!=1 ||
           SSL_connect(tls.p)!=1 ||
           SSL_version(tls.p)!=TLS1_3_VERSION ||
           SSL_get_verify_result(tls.p)!=X509_V_OK)
            return false;
        if(nonsecret_test_stage)*nonsecret_test_stage=4;
        X509* server_cert=SSL_get_peer_certificate(tls.p);
        if(!server_cert)return false;
        X509_free(server_cert);
        if(!LocalTlsDetail::Send(tls.p,"YT-P2P/V80 BEGIN\n"))return false;
        std::string line;
        constexpr std::string_view prefix="YT-P2P/V80 KEY ";
        if(!LocalTlsDetail::ReadLine(tls.p,line,prefix.size()+65) ||
           line.size()!=prefix.size()+65 ||
           line.compare(0,prefix.size(),prefix)!=0 ||
           line.back()!='\n')return false;

        if(nonsecret_test_stage)*nonsecret_test_stage=5;
        std::array<std::uint8_t,32> secret{};
        for(std::size_t i=0;i<secret.size();++i) {
            const int hi=LocalTlsDetail::Hex(line[prefix.size()+2*i]);
            const int lo=LocalTlsDetail::Hex(line[prefix.size()+2*i+1]);
            if(hi<0 || lo<0) {
                CryptoDetail::Erase(secret);
                return false;
            }
            secret[i]=static_cast<std::uint8_t>((hi<<4)|lo);
        }
        std::fill(line.begin(),line.end(),char(0));
        if(!inbox.BeginTrustedTls(secret,expected,tls_serial,
                                  refresh,trusted_game_state)) {
            CryptoDetail::Erase(secret);return false;
        }
        CryptoDetail::Erase(secret);
        if(nonsecret_test_stage)*nonsecret_test_stage=6;
        // V102 pair binding is a server-issued opaque selector returned
        // through certificate-bound LIST; never an account or endpoint.
        char pair_selector[16]{};
        constexpr char selector_lut[]="0123456789abcdef";
        for(unsigned i=0;i<16;++i)
            pair_selector[15U-i]=selector_lut[(v102_pair_id>>(4U*i))&0x0fU];
        const std::string id_hex=v102_pair_id?
            std::string(pair_selector,sizeof(pair_selector)):std::string{};
        const std::string offer_command=v102_pair_id?
            "YT-P2P/V102 OFFER "+id_hex+"\n":
            "YT-P2P/V90 OFFER\n";
        if(!LocalTlsDetail::Send(tls.p,offer_command)) {
            inbox.Revoke();return false;
        }
        if(nonsecret_test_stage)*nonsecret_test_stage=7;
        if(!LocalTlsDetail::ReadLine(
              tls.p,line,NativeSealedGrantInboxV84::kLineBytes)) {
            inbox.Revoke();
            std::fill(line.begin(),line.end(),char(0));
            return false;
        }
        if(nonsecret_test_stage)*nonsecret_test_stage=8;
        // V90: the TLS handshake/request takes time. A grant is issued
        // by the server AFTER Request() starts; checking its issued_ms
        // against the call-start timestamp would incorrectly reject every
        // genuine offer as "not yet issued". Sample wall clock ONLY after
        // the full sealed TLS record arrives.
        const auto received_ms=static_cast<std::uint64_t>(
            std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::system_clock::now().time_since_epoch()).count());
        if(received_ms<now_ms ||
           !inbox.ReceiveSealedTlsLine(line,received_ms)) {
            inbox.Revoke();
            std::fill(line.begin(),line.end(),char(0));
            return false;
        }
        std::fill(line.begin(),line.end(),char(0));
        if(nonsecret_test_stage)*nonsecret_test_stage=9;
        // Even a cryptographically verified offer NEVER Arm()s UDP sender
        // or receiver. Only future independently proven NAT game-socket
        // pairing is allowed to use this pending candidate.
        if(!inbox.HasCurrentPending(received_ms))return false;
        if(!send_ready_proof)return true; // V90 compatibility unchanged
        // V91: prove receipt of the SAME V90 pair secret inside this very
        // client-cert-pinned TLS1.3 connection, without exposing master.
        const auto* offer=inbox.PendingForNat(received_ms);
        PairReadyProofV91::Tag proof{};
        if(!offer || !PairReadyProofV91::Create(*offer,received_ms,proof)) {
            inbox.Revoke();return false;
        }
        constexpr char lut[]="0123456789abcdef";
        std::string message=v102_pair_id?
            "YT-P2P/V102 READY "+id_hex+" ":
            "YT-P2P/V91 READY ";
        for(const auto byte:proof){
            message.push_back(lut[byte>>4U]);
            message.push_back(lut[byte&0x0FU]);
        }
        CryptoDetail::Erase(proof);
        message.push_back('\n');
        const bool sent=LocalTlsDetail::Send(tls.p,message);
        std::fill(message.begin(),message.end(),char(0));
        if(!sent || !LocalTlsDetail::ReadLine(tls.p,line,40)) {
            inbox.Revoke();return false;
        }
        const bool complete=v102_pair_id?
            line=="YT-P2P/V102 BOTH_READY\n":
            line=="YT-P2P/V91 BOTH_READY\n";
        const bool pending=v102_pair_id?
            line=="YT-P2P/V102 PENDING\n":
            line=="YT-P2P/V91 PENDING\n";
        std::fill(line.begin(),line.end(),char(0));
        if(!complete && !pending) {inbox.Revoke();return false;}
        if(both_received_ready)*both_received_ready=complete;
        // A PENDING recipient has proved key possession but MUST NOT arm
        // game UDP merely because the second recipient later replies.
        return inbox.HasCurrentPending(received_ms);
    }
};
} // namespace SeamlessHunt::Hybrid
