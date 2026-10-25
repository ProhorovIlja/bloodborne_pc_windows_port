// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V83: ACTUAL portable OpenSSL/LibreSSL native TLS 1.3 *client* for the
// EXISTING Qt shadNet daemon's V80/V81 encrypted offer protocol.
// Local loopback development-only until PKI/enrollment, full account IDs,
// authenticated remote provisioning, peer NAT and encryption are completed.
// No Qt dependency in native game; never creates/replaces its game UDP socket.
#include "sh_native_grant_inbox.hpp"
#include <array>
#include <cstddef>
#include <cstdint>
#include <climits>
#include <algorithm>
#include <cstring>
#include <span>
#include <string>
#include <string_view>
#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <winsock2.h>
#include <ws2tcpip.h>
#else
#include <arpa/inet.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include <sys/time.h>
#endif
#include <openssl/ssl.h>
#include <openssl/x509_vfy.h>

namespace SeamlessHunt::Hybrid {
struct NativeTlsLocalConfig {
    // Files come only from a trusted operator's TEST installation.
    // Never copy private keys from live server or embed CI private keys.
    std::string server_ca_pem;
    std::string client_cert_pem;
    std::string client_key_pem;
    std::uint16_t localhost_port=0;
};
namespace LocalTlsDetail {
#ifdef _WIN32
using Socket=SOCKET;
constexpr Socket Invalid=INVALID_SOCKET;
inline void Close(Socket s) noexcept {if(s!=Invalid)(void)closesocket(s);}
struct SocketPlatform {
    WSADATA data{};
    bool ready=false;
    SocketPlatform() noexcept {ready=WSAStartup(MAKEWORD(2,2),&data)==0;}
    ~SocketPlatform(){if(ready) WSACleanup();}
};
#else
using Socket=int;
constexpr Socket Invalid=-1;
inline void Close(Socket s) noexcept {if(s!=Invalid)(void)close(s);}
struct SocketPlatform {bool ready=true;};
#endif
inline Socket OpenLocal(std::uint16_t port) noexcept {
    if(!port)return Invalid;
    Socket s=socket(AF_INET,SOCK_STREAM,IPPROTO_TCP);
    if(s==Invalid)return Invalid;
#ifdef _WIN32
    DWORD timeout=3000;
    if(setsockopt(s,SOL_SOCKET,SO_RCVTIMEO,
                  reinterpret_cast<const char*>(&timeout),sizeof(timeout))!=0 ||
       setsockopt(s,SOL_SOCKET,SO_SNDTIMEO,
                  reinterpret_cast<const char*>(&timeout),sizeof(timeout))!=0) {
        Close(s);return Invalid;
    }
#else
    timeval timeout{3,0};
    if(setsockopt(s,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout))!=0 ||
       setsockopt(s,SOL_SOCKET,SO_SNDTIMEO,&timeout,sizeof(timeout))!=0) {
        Close(s);return Invalid;
    }
#endif
    sockaddr_in addr{};
    addr.sin_family=AF_INET;
    addr.sin_port=htons(port);
    // Intentionally NO hostname, public IPv4, resolver, or proxy.
    if(inet_pton(AF_INET,"127.0.0.1",&addr.sin_addr)!=1 ||
       connect(s,reinterpret_cast<const sockaddr*>(&addr),sizeof(addr))!=0) {
        Close(s);return Invalid;
    }
    return s;
}
struct SocketOwner {
    Socket fd=Invalid;
    ~SocketOwner(){Close(fd);}
};
struct SslCtxOwner {
    SSL_CTX* p=nullptr;
    ~SslCtxOwner(){if(p)SSL_CTX_free(p);}
};
struct SslOwner {
    SSL* p=nullptr;
    ~SslOwner(){if(p)SSL_free(p);}
};
inline bool Send(SSL* ssl,std::string_view msg) noexcept {
    while(!msg.empty()) {
        if(msg.size()>4096)return false;
        const int n=SSL_write(ssl,msg.data(),static_cast<int>(msg.size()));
        if(n<=0)return false;
        msg.remove_prefix(static_cast<std::size_t>(n));
    }
    return true;
}
// Strict protocol records. Read one byte at a time so a TLS coalesced
// second record is never mistakenly accepted as part of the first.
inline bool ReadLine(SSL* ssl,std::string& out,std::size_t maximum) {
    out.clear();
    if(!maximum || maximum>512)return false;
    while(out.size()<maximum) {
        char c=0;
        if(SSL_read(ssl,&c,1)!=1)return false;
        if(c=='\0' || c=='\r')return false;
        out.push_back(c);
        if(c=='\n')return true;
    }
    return false;
}
inline int Hex(char c) noexcept {
    if(c>='0'&&c<='9')return c-'0';
    if(c>='a'&&c<='f')return c-'a'+10;
    return -1; // V80 only sends canonical lowercase
}
} // namespace LocalTlsDetail

class NativeTlsLocalOfferClient final {
public:
    // Explicit TEST-only synchronous request. Run outside the native game
    // UDP receive thread, holding the existing transport's grant mutex.
    // The caller MUST obtain expected from an authentic *current game*
    // state and refresh it on each inbox operation. This class cannot
    // authenticate an arbitrary client-supplied account/peer name.
    static bool Request(const NativeTlsLocalConfig& config,
                        NativeSealedGrantInbox& inbox,
                        const NativeOfferIdentity& expected,
                        std::uint64_t tls_serial,
                        RefreshNativeOfferIdentity refresh,
                        void* trusted_game_state,
                        std::uint64_t now_ms) {
        // In particular, no remote endpoint can be configured through
        // this incomplete prototype. No 31313/31314/31315 traffic changes.
        inbox.Revoke();
        if(config.server_ca_pem.empty() || config.client_cert_pem.empty() ||
           config.client_key_pem.empty() || !config.localhost_port ||
           !tls_serial || !refresh || !trusted_game_state)return false;
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

        LocalTlsDetail::SocketOwner socket;
        socket.fd=LocalTlsDetail::OpenLocal(config.localhost_port);
        if(socket.fd==LocalTlsDetail::Invalid)return false;
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
        if(!LocalTlsDetail::Send(tls.p,"YT-P2P/V81 OFFER\n") ||
           !LocalTlsDetail::ReadLine(
              tls.p,line,NativeSealedGrantInbox::kLineBytes) ||
           !inbox.ReceiveSealedTlsLine(line,now_ms)) {
            inbox.Revoke();
            std::fill(line.begin(),line.end(),char(0));
            return false;
        }
        std::fill(line.begin(),line.end(),char(0));
        // Even a cryptographically verified offer NEVER Arm()s UDP sender
        // or receiver. Only future independently proven NAT game-socket
        // pairing is allowed to use this pending candidate.
        return inbox.HasCurrentPending(now_ms);
    }
};
} // namespace SeamlessHunt::Hybrid
