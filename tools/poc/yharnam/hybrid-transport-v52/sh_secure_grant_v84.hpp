// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V84: new SHG2 sealed format with 256-bit account identities; source-only.
// AES-256-GCM encrypts BOTH peer endpoints and the one-direction UDP MAC key.
// The AEAD transport key MUST be supplied by a future mutually authenticated,
// encrypted TLS control channel (TLS exporter with unique per-session context).
// Never feed plaintext legacy SHLK / HTTP passwords to InstallChannelKey.
// Source-only: no Qt listener or native game Arm() caller is installed here.
#include "sh_direct_crypto.hpp"
#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <limits>
#include <span>
#include <vector>
#ifdef _WIN32
#include <bcrypt.h>
#else
#include <openssl/rand.h>
#endif

namespace SeamlessHunt::Hybrid {
struct SecurePeerOfferV84 {
    std::array<std::uint8_t,32> sender_account{}; // full SHA-256 trusted ID
    std::array<std::uint8_t,32> recipient_account{};
    std::uint64_t session_epoch=0;
    std::uint64_t pair_binding=0;
    std::uint64_t world_revision=0;
    std::uint64_t issued_ms=0;
    std::uint64_t expires_ms=0;
    std::uint32_t peer_ipv4_nbo=0;
    std::uint16_t peer_port_nbo=0;
    std::uint32_t peer_virtual_ipv4_nbo=0;
    std::uint16_t peer_virtual_port_nbo=0;
    std::array<std::uint8_t,32> direction_key{};
};
namespace SecureOfferV84Detail {
constexpr std::size_t kPlaintextBytes=148; // 2x256, 5x64, 2x32, 2x16, 32 key
constexpr std::size_t kNonceBytes=12;
constexpr std::size_t kTagBytes=16;
constexpr std::size_t kHeaderBytes=19; // "SHG2", ver, 12-byte nonce, 2-byte size
constexpr std::size_t kWireBytes=kHeaderBytes+kPlaintextBytes+kTagBytes;
constexpr std::uint64_t kMaxLifetimeMs=30000;
constexpr std::array<std::uint8_t,16> kDomain{
    'Y','T','-','P','2','P','-','G','R','A','N','T','-','V','8','4'};
inline bool Random(std::span<std::uint8_t> b) noexcept {
    if(b.empty() || b.size()>4096)return false;
#ifdef _WIN32
    return BCRYPT_SUCCESS(BCryptGenRandom(nullptr,b.data(),
        static_cast<ULONG>(b.size()),BCRYPT_USE_SYSTEM_PREFERRED_RNG));
#else
    return RAND_bytes(b.data(),static_cast<int>(b.size()))==1;
#endif
}
inline void Append(std::vector<std::uint8_t>& out,std::uint64_t n,
                   unsigned bytes) {
    for(unsigned i=0;i<bytes;++i){out.push_back(static_cast<std::uint8_t>(n));n>>=8;}
}
inline std::uint64_t Read(std::span<const std::uint8_t> s,
                          std::size_t& offset,unsigned bytes) noexcept {
    std::uint64_t v=0;
    for(unsigned i=0;i<bytes;++i)
        v|=std::uint64_t(s[offset++]) << (8U*i);
    return v;
}
inline bool Nonzero(std::span<const std::uint8_t> a) noexcept {
    std::uint8_t seen=0;
    for(auto byte:a)seen|=byte;
    return seen!=0;
}
inline bool EqualDigest(std::span<const std::uint8_t> a,
                        std::span<const std::uint8_t> b) noexcept {
    if(a.size()!=32 || b.size()!=32)return false;
    std::uint8_t diff=0;
    for(std::size_t i=0;i<32;++i)diff|=a[i]^b[i];
    return diff==0;
}
inline bool Valid(const SecurePeerOfferV84& a,std::uint64_t now) noexcept {
    const auto& k=a.direction_key;
    return Nonzero(a.sender_account) && Nonzero(a.recipient_account) &&
        !EqualDigest(a.sender_account,a.recipient_account) && a.session_epoch &&
        a.pair_binding && a.world_revision &&
        a.issued_ms<=now && a.expires_ms>now &&
        a.expires_ms>a.issued_ms &&
        a.expires_ms-a.issued_ms<=kMaxLifetimeMs &&
        a.peer_ipv4_nbo && a.peer_port_nbo &&
        a.peer_virtual_ipv4_nbo && a.peer_virtual_port_nbo &&
        std::any_of(k.begin(),k.end(),[](std::uint8_t x){return x!=0;});
}
inline std::vector<std::uint8_t> Encode(const SecurePeerOfferV84& a) {
    std::vector<std::uint8_t> out;
    out.reserve(kPlaintextBytes);
    out.insert(out.end(),a.sender_account.begin(),a.sender_account.end());
    out.insert(out.end(),a.recipient_account.begin(),a.recipient_account.end());
    Append(out,a.session_epoch,8);Append(out,a.pair_binding,8);
    Append(out,a.world_revision,8);Append(out,a.issued_ms,8);
    Append(out,a.expires_ms,8);Append(out,a.peer_ipv4_nbo,4);
    Append(out,a.peer_port_nbo,2);Append(out,a.peer_virtual_ipv4_nbo,4);
    Append(out,a.peer_virtual_port_nbo,2);
    out.insert(out.end(),a.direction_key.begin(),a.direction_key.end());
    return out;
}
inline bool Decode(std::span<const std::uint8_t> p,SecurePeerOfferV84& a) noexcept {
    a={};
    if(p.size()!=kPlaintextBytes)return false;
    std::size_t at=0;
    std::copy_n(p.begin(),32,a.sender_account.begin());at+=32;
    std::copy_n(p.begin()+32,32,a.recipient_account.begin());at+=32;
    a.session_epoch=Read(p,at,8);a.pair_binding=Read(p,at,8);
    a.world_revision=Read(p,at,8);a.issued_ms=Read(p,at,8);
    a.expires_ms=Read(p,at,8);
    a.peer_ipv4_nbo=static_cast<std::uint32_t>(Read(p,at,4));
    a.peer_port_nbo=static_cast<std::uint16_t>(Read(p,at,2));
    a.peer_virtual_ipv4_nbo=static_cast<std::uint32_t>(Read(p,at,4));
    a.peer_virtual_port_nbo=static_cast<std::uint16_t>(Read(p,at,2));
    if(at+32!=p.size())return false;
    std::copy(p.begin()+static_cast<std::ptrdiff_t>(at),p.end(),
              a.direction_key.begin());
    return true;
}
inline bool AesGcm(bool encrypt,std::span<const std::uint8_t> key,
     std::span<const std::uint8_t> nonce,
     std::span<const std::uint8_t> associated,
     std::span<const std::uint8_t> input,
     std::span<std::uint8_t> output,
     std::span<std::uint8_t> tag) noexcept {
    if(key.size()!=32 || nonce.size()!=kNonceBytes ||
       tag.size()!=kTagBytes || input.size()!=output.size() ||
       associated.size()>1024 || input.size()>1024)
        return false;
#ifdef _WIN32
    BCRYPT_ALG_HANDLE alg=nullptr;
    BCRYPT_KEY_HANDLE aes=nullptr;
    if(!BCRYPT_SUCCESS(BCryptOpenAlgorithmProvider(
        &alg,BCRYPT_AES_ALGORITHM,nullptr,0)))return false;
    bool ok=BCRYPT_SUCCESS(BCryptSetProperty(
        alg,BCRYPT_CHAINING_MODE,
        reinterpret_cast<PUCHAR>(const_cast<wchar_t*>(BCRYPT_CHAIN_MODE_GCM)),
        static_cast<ULONG>(sizeof(BCRYPT_CHAIN_MODE_GCM)),0));
    if(ok)ok=BCRYPT_SUCCESS(BCryptGenerateSymmetricKey(
        alg,&aes,nullptr,0,const_cast<PUCHAR>(key.data()),
        static_cast<ULONG>(key.size()),0));
    if(ok) {
        BCRYPT_AUTHENTICATED_CIPHER_MODE_INFO info;
        BCRYPT_INIT_AUTH_MODE_INFO(info);
        info.pbNonce=const_cast<PUCHAR>(nonce.data());
        info.cbNonce=static_cast<ULONG>(nonce.size());
        info.pbAuthData=const_cast<PUCHAR>(associated.data());
        info.cbAuthData=static_cast<ULONG>(associated.size());
        info.pbTag=tag.data();
        info.cbTag=static_cast<ULONG>(tag.size());
        ULONG written=0;
        const auto status=encrypt ?
            BCryptEncrypt(aes,const_cast<PUCHAR>(input.data()),
                          static_cast<ULONG>(input.size()),&info,
                          nullptr,0,output.data(),
                          static_cast<ULONG>(output.size()),&written,0) :
            BCryptDecrypt(aes,const_cast<PUCHAR>(input.data()),
                          static_cast<ULONG>(input.size()),&info,
                          nullptr,0,output.data(),
                          static_cast<ULONG>(output.size()),&written,0);
        ok=BCRYPT_SUCCESS(status) && written==input.size();
    }
    if(aes)(void)BCryptDestroyKey(aes);
    (void)BCryptCloseAlgorithmProvider(alg,0);
#else
    EVP_CIPHER_CTX* ctx=EVP_CIPHER_CTX_new();
    if(!ctx)return false;
    bool ok=EVP_CipherInit_ex(ctx,EVP_aes_256_gcm(),nullptr,nullptr,nullptr,
                               encrypt?1:0)==1;
    if(ok)ok=EVP_CIPHER_CTX_ctrl(ctx,EVP_CTRL_GCM_SET_IVLEN,
                               static_cast<int>(nonce.size()),nullptr)==1;
    if(ok)ok=EVP_CipherInit_ex(ctx,nullptr,nullptr,key.data(),nonce.data(),
                              encrypt?1:0)==1;
    int n=0,completed=0;
    if(ok)ok=EVP_CipherUpdate(ctx,nullptr,&n,associated.data(),
                             static_cast<int>(associated.size()))==1;
    if(ok)ok=EVP_CipherUpdate(ctx,output.data(),&n,input.data(),
                             static_cast<int>(input.size()))==1 &&
                             static_cast<std::size_t>(n)==input.size();
    if(ok && !encrypt)ok=EVP_CIPHER_CTX_ctrl(
       ctx,EVP_CTRL_GCM_SET_TAG,static_cast<int>(tag.size()),tag.data())==1;
    if(ok)ok=EVP_CipherFinal_ex(ctx,output.data()+n,&completed)==1 &&
              completed==0;
    if(ok && encrypt)ok=EVP_CIPHER_CTX_ctrl(
       ctx,EVP_CTRL_GCM_GET_TAG,static_cast<int>(tag.size()),tag.data())==1;
    EVP_CIPHER_CTX_free(ctx);
#endif
    if(!ok)CryptoDetail::Erase(output);
    return ok;
}
} // namespace SecureOfferV84Detail

// Both the server and a *recipient-authenticated* TLS control channel must
// bind the offer to the intended account/session/world. Never copy verified
// booleans out of an untrusted network datagram into game PeerTicket.
class SealedPeerOffersV84 final {
public:
    SealedPeerOffersV84()=default;
    ~SealedPeerOffersV84(){Clear();}
    SealedPeerOffersV84(const SealedPeerOffersV84&)=delete;
    SealedPeerOffersV84& operator=(const SealedPeerOffersV84&)=delete;

    bool InstallChannelKey(std::span<const std::uint8_t> tls_exporter_key) noexcept {
        Clear();
        if(tls_exporter_key.size()!=key_.size() ||
           !std::any_of(tls_exporter_key.begin(),tls_exporter_key.end(),
                        [](std::uint8_t b){return b!=0;}))return false;
        std::copy(tls_exporter_key.begin(),tls_exporter_key.end(),key_.begin());
        ready_=true;return true;
    }
    bool Seal(const SecurePeerOfferV84& offer,std::uint64_t now,
              std::vector<std::uint8_t>& output) const {
        output.clear();
        if(!ready_ || !SecureOfferV84Detail::Valid(offer,now))return false;
        auto plain=SecureOfferV84Detail::Encode(offer);
        if(plain.size()!=SecureOfferV84Detail::kPlaintextBytes) {
            CryptoDetail::Erase(plain);return false;
        }
        output.insert(output.end(),{'S','H','G','2',2});
        output.resize(SecureOfferV84Detail::kHeaderBytes);
        if(!SecureOfferV84Detail::Random(
               std::span<std::uint8_t>(output.data()+5,
               SecureOfferV84Detail::kNonceBytes))) {
            output.clear();CryptoDetail::Erase(plain);return false;
        }
        output[17]=static_cast<std::uint8_t>(plain.size());
        output[18]=0;
        output.resize(SecureOfferV84Detail::kWireBytes);
        auto aad=SecureOfferV84Detail::kDomain;
        const auto nonce=std::span<const std::uint8_t>(
            output.data()+5,SecureOfferV84Detail::kNonceBytes);
        const bool ok=SecureOfferV84Detail::AesGcm(true,key_,nonce,aad,
           plain,std::span<std::uint8_t>(output.data()+SecureOfferV84Detail::kHeaderBytes,
                                         SecureOfferV84Detail::kPlaintextBytes),
           std::span<std::uint8_t>(output.data()+SecureOfferV84Detail::kHeaderBytes+
                                    SecureOfferV84Detail::kPlaintextBytes,
                                    SecureOfferV84Detail::kTagBytes));
        CryptoDetail::Erase(plain);
        if(!ok)output.clear();
        return ok;
    }
    // TLS client/server and live game authority MUST bind BOTH full SHA256 IDs.
    // Returning verified peer material does NOT directly enable game sockets;
    // admission still needs a fresh server world/consent, NAT verification,
    // and key lifetime tracking by the future trusted runtime installer.
    bool Open(std::span<const std::uint8_t> wire,
              const std::array<std::uint8_t,32>& recipient,
              const std::array<std::uint8_t,32>& sender,
              std::uint64_t expected_session,std::uint64_t expected_world,
              std::uint64_t now,SecurePeerOfferV84& accepted) noexcept {
        accepted={};
        if(!ready_ || !SecureOfferV84Detail::Nonzero(recipient) ||
           !SecureOfferV84Detail::Nonzero(sender) ||
           SecureOfferV84Detail::EqualDigest(recipient,sender) ||
           !expected_session || !expected_world ||
           wire.size()!=SecureOfferV84Detail::kWireBytes ||
           wire[0]!='S'||wire[1]!='H'||wire[2]!='G'||wire[3]!='2' ||
           wire[4]!=2 || wire[17]!=SecureOfferV84Detail::kPlaintextBytes ||
           wire[18]!=0)return false;
        auto nonce=wire.subspan(5,SecureOfferV84Detail::kNonceBytes);
        for(const auto& item:seen_)
            if(item.valid && std::equal(item.nonce.begin(),item.nonce.end(),
                                        nonce.begin()))
                return false;
        std::array<std::uint8_t,SecureOfferV84Detail::kPlaintextBytes> plain{};
        auto tag=std::array<std::uint8_t,SecureOfferV84Detail::kTagBytes>{};
        std::copy(wire.end()-static_cast<std::ptrdiff_t>(tag.size()),
                  wire.end(),tag.begin());
        const bool ok=SecureOfferV84Detail::AesGcm(false,key_,nonce,
            SecureOfferV84Detail::kDomain,
            wire.subspan(SecureOfferV84Detail::kHeaderBytes,
                         SecureOfferV84Detail::kPlaintextBytes),
            plain,tag);
        SecurePeerOfferV84 decoded{};
        if(ok) (void)SecureOfferV84Detail::Decode(plain,decoded);
        CryptoDetail::Erase(plain);
        CryptoDetail::Erase(tag);
        if(!ok || !SecureOfferV84Detail::Valid(decoded,now) ||
           !SecureOfferV84Detail::EqualDigest(decoded.recipient_account,recipient) ||
           !SecureOfferV84Detail::EqualDigest(decoded.sender_account,sender) ||
           decoded.session_epoch!=expected_session ||
           decoded.world_revision!=expected_world) {
            CryptoDetail::Erase(decoded.direction_key);
            return false;
        }
        // Never evict an old nonce while the same TLS-exporter key is in
        // use. Exhaustion forces an authenticated channel rekey and denies
        // further grants; otherwise an older valid offer could be replayed.
        if(next_>=seen_.size()) {
            CryptoDetail::Erase(decoded.direction_key);
            return false;
        }
        accepted=decoded;
        CryptoDetail::Erase(decoded.direction_key);
        auto& cell=seen_[next_++];
        std::copy(nonce.begin(),nonce.end(),cell.nonce.begin());
        cell.valid=true;
        return true;
    }
    void Clear() noexcept {
        CryptoDetail::Erase(key_);ready_=false;
        for(auto& v:seen_){CryptoDetail::Erase(v.nonce);v.valid=false;}
        next_=0;
    }
private:
    struct Seen {std::array<std::uint8_t,SecureOfferV84Detail::kNonceBytes> nonce{};bool valid=false;};
    std::array<std::uint8_t,32> key_{};
    std::array<Seen,64> seen_{};
    std::size_t next_=0;
    bool ready_=false;
};
} // namespace SeamlessHunt::Hybrid
