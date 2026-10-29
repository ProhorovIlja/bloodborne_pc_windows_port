// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V87: FULL SHA256 identity derived from game's own server-accepted link ID.
// NOT a trusted peer roster, TLS credential or world authorization by itself.
// Server-issued SHG2 + mTLS still must independently authorize the pair.
// No secrets logged; source-only, developer-gated runtime check.
#include "sh_native_grant_inbox_v84.hpp"
#include <array>
#include <cstdint>
#include <string_view>
#ifdef _WIN32
#include <bcrypt.h>
#else
#include <openssl/evp.h>
#endif

namespace SeamlessHunt::Hybrid {
class NativeGameSelfIdentityV87 final {
public:
    static bool Digest(std::string_view confirmed_online_id,
                       std::array<std::uint8_t,32>& out) noexcept {
        out.fill(0);
        if(confirmed_online_id.empty() || confirmed_online_id.size()>64 ||
           confirmed_online_id.find('\0')!=std::string_view::npos ||
           confirmed_online_id.find('\r')!=std::string_view::npos ||
           confirmed_online_id.find('\n')!=std::string_view::npos)
            return false;
        static constexpr char domain[]="YT-P2P-V84-ID:";
#ifdef _WIN32
        BCRYPT_ALG_HANDLE alg=nullptr;
        BCRYPT_HASH_HANDLE state=nullptr;
        bool ok=BCRYPT_SUCCESS(BCryptOpenAlgorithmProvider(
            &alg,BCRYPT_SHA256_ALGORITHM,nullptr,0));
        if(ok)ok=BCRYPT_SUCCESS(BCryptCreateHash(alg,&state,nullptr,0,
                                                nullptr,0,0));
        if(ok)ok=BCRYPT_SUCCESS(BCryptHashData(
            state,reinterpret_cast<PUCHAR>(const_cast<char*>(domain)),
            static_cast<ULONG>(sizeof(domain)-1),0));
        if(ok)ok=BCRYPT_SUCCESS(BCryptHashData(
            state,reinterpret_cast<PUCHAR>(const_cast<char*>(confirmed_online_id.data())),
            static_cast<ULONG>(confirmed_online_id.size()),0));
        if(ok)ok=BCRYPT_SUCCESS(BCryptFinishHash(
            state,out.data(),static_cast<ULONG>(out.size()),0));
        if(state)(void)BCryptDestroyHash(state);
        if(alg)(void)BCryptCloseAlgorithmProvider(alg,0);
#else
        EVP_MD_CTX* ctx=EVP_MD_CTX_new();
        if(!ctx)return false;
        bool ok=EVP_DigestInit_ex(ctx,EVP_sha256(),nullptr)==1;
        if(ok)ok=EVP_DigestUpdate(ctx,domain,sizeof(domain)-1)==1;
        if(ok)ok=EVP_DigestUpdate(ctx,confirmed_online_id.data(),
                                  confirmed_online_id.size())==1;
        unsigned int n=0;
        if(ok)ok=EVP_DigestFinal_ex(ctx,out.data(),&n)==1 && n==out.size();
        EVP_MD_CTX_free(ctx);
#endif
        if(!ok)out.fill(0);
        return ok;
    }
    static bool MatchesAcceptedLink(std::string_view online_id,
                                    bool server_welcomed,
                                    bool server_endpoint_configured,
                                    const NativeOfferIdentityV84& expected) noexcept {
        if(!server_welcomed || !server_endpoint_configured ||
           !expected.locally_opted_in || !expected.session_epoch ||
           !expected.world_revision ||
           !SecureOfferV84Detail::Nonzero(expected.peer_account))
            return false;
        std::array<std::uint8_t,32> self{};
        const bool ok=Digest(online_id,self);
        const bool matches=ok && SecureOfferV84Detail::EqualDigest(
            self,expected.self_account) &&
            !SecureOfferV84Detail::EqualDigest(self,expected.peer_account);
        CryptoDetail::Erase(self);
        return matches;
    }
};
} // namespace SeamlessHunt::Hybrid
