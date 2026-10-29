// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// Native (non-Qt) V102 certificate-bound team pair LIST.
// This is an explicitly local-only development control connection.
// A LIST returns opaque pair selectors, NOT game-route authorization.
// No peer IPs, private keys, UDP sockets or gameplay Direct activation.
#include "sh_native_tls_local_client.hpp"
#include <algorithm>
#include <array>
#include <climits>
#include <cstddef>
#include <cstdint>
#include <string>
#include <string_view>

namespace SeamlessHunt::Hybrid {

class NativeTlsPairListV102 final {
public:
    static constexpr std::size_t kMaxPairSelectors = 16;
    using PairSelectors = std::array<std::uint64_t,kMaxPairSelectors>;
    static constexpr std::string_view kPrefix = "YT-P2P/V102 PAIRS";
    static constexpr std::size_t kMaxReplyBytes =
        kPrefix.size() + 17*kMaxPairSelectors + 1;

    // Parse ONLY a complete canonical server response. A duplicate,
    // zero-valued, malformed or oversized selector list is entirely
    // rejected; partial untrusted values never escape to a game caller.
    static bool Parse(std::string_view line,PairSelectors& result,
                      std::size_t& count) noexcept {
        result.fill(0);
        count=0;
        if(line.size()<kPrefix.size()+1 || line.size()>kMaxReplyBytes ||
           line.substr(0,kPrefix.size())!=kPrefix ||
           line.back()!='\n')
            return false;
        PairSelectors parsed{};
        std::size_t parsed_count=0;
        std::size_t offset=kPrefix.size();
        while(offset<line.size()-1) {
            if(line[offset]!=' ' || parsed_count>=kMaxPairSelectors ||
               line.size()-1-offset<17)
                return false;
            ++offset;
            std::uint64_t selector=0;
            for(unsigned digit=0;digit<16;++digit) {
                const int hex=LocalTlsDetail::Hex(line[offset++]);
                if(hex<0)return false;
                selector=(selector<<4)|static_cast<std::uint64_t>(hex);
            }
            if(!selector || std::find(parsed.begin(),
                    parsed.begin()+parsed_count,selector)!=parsed.begin()+parsed_count)
                return false;
            parsed[parsed_count++]=selector;
        }
        if(offset!=line.size()-1)return false;
        result=parsed;
        count=parsed_count;
        return true;
    }

    // Cert-bound, bounded, synchronous LIST using the SAME V83 TLS backend.
    // Only the server chooses the current account's pair selectors. This
    // must run off the game's receive thread, and must NEVER Arm Direct.
    static bool List(const NativeTlsLocalConfig& config,
                     PairSelectors& result,std::size_t& count) {
        result.fill(0);count=0;
        if(config.server_ca_pem.empty() ||
           config.client_cert_pem.empty() ||
           config.client_key_pem.empty() ||
           !config.localhost_port)return false;
        LocalTlsDetail::SocketPlatform net;
        if(!net.ready)return false;
        LocalTlsDetail::SslCtxOwner context;
        context.p=SSL_CTX_new(TLS_client_method());
        if(!context.p ||
           SSL_CTX_set_min_proto_version(context.p,TLS1_3_VERSION)!=1 ||
           SSL_CTX_set_max_proto_version(context.p,TLS1_3_VERSION)!=1)
            return false;
        SSL_CTX_set_verify(context.p,SSL_VERIFY_PEER,nullptr);
        if(SSL_CTX_load_verify_locations(
               context.p,config.server_ca_pem.c_str(),nullptr)!=1 ||
           SSL_CTX_use_certificate_file(
               context.p,config.client_cert_pem.c_str(),SSL_FILETYPE_PEM)!=1 ||
           SSL_CTX_use_PrivateKey_file(
               context.p,config.client_key_pem.c_str(),SSL_FILETYPE_PEM)!=1 ||
           SSL_CTX_check_private_key(context.p)!=1)
            return false;
        LocalTlsDetail::SocketOwner socket;
        socket.fd=LocalTlsDetail::OpenLocal(config.localhost_port);
        if(socket.fd==LocalTlsDetail::Invalid)return false;
        LocalTlsDetail::SslOwner tls;
        tls.p=SSL_new(context.p);
        if(!tls.p ||
           X509_VERIFY_PARAM_set1_ip_asc(
               SSL_get0_param(tls.p),"127.0.0.1")!=1)
            return false;
#ifdef _WIN32
        if(socket.fd>static_cast<LocalTlsDetail::Socket>(INT_MAX))
            return false;
#endif
        if(SSL_set_fd(tls.p,static_cast<int>(socket.fd))!=1 ||
           SSL_connect(tls.p)!=1 ||
           SSL_version(tls.p)!=TLS1_3_VERSION ||
           SSL_get_verify_result(tls.p)!=X509_V_OK)
            return false;
        X509* server_certificate=SSL_get_peer_certificate(tls.p);
        if(!server_certificate)return false;
        X509_free(server_certificate);
        if(!LocalTlsDetail::Send(tls.p,"YT-P2P/V102 LIST\n"))
            return false;
        std::string reply;
        if(!LocalTlsDetail::ReadLine(tls.p,reply,kMaxReplyBytes))
            return false;
        return Parse(reply,result,count);
    }
};
} // namespace SeamlessHunt::Hybrid
