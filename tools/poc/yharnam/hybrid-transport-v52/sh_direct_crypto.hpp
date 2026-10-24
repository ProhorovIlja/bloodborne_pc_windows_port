// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "sh_direct_datagram.hpp"
#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <span>
#include <vector>
#ifdef _WIN32
#include <windows.h>
#include <bcrypt.h>
#ifdef _MSC_VER
#pragma comment(lib, "bcrypt.lib")
#endif
#else
#include <openssl/crypto.h>
#include <openssl/evp.h>
#include <openssl/hmac.h>
#endif

// V60: real HMAC-SHA256 (16-byte truncated authentication tag), backed by
// Windows CNG BCrypt or Linux OpenSSL. Unlike the V58/V59 unit-test stub,
// these routines are cryptographic. Still source-only: NO authenticated
// shadNet rendezvous, NAT traversal or gameplay socket hookup here.
// The caller must provision UNIQUE, CSPRNG-derived, direction-separated keys
// bound to verified room/peer/session grants and securely distribute them.
// HMAC authenticates traffic; it does NOT encrypt packet contents.
namespace SeamlessHunt::Hybrid {

namespace CryptoDetail {
inline void Erase(std::span<std::uint8_t> bytes) noexcept {
#ifdef _WIN32
    if (!bytes.empty()) SecureZeroMemory(bytes.data(), bytes.size());
#else
    if (!bytes.empty()) OPENSSL_cleanse(bytes.data(), bytes.size());
#endif
}
inline bool Sha256Hmac(std::span<const std::uint8_t> key,
                       std::span<const std::uint8_t> message,
                       std::array<std::uint8_t,32>& digest) noexcept {
    digest.fill(0);
    if (key.size() != 32 || message.size() > DirectReceiver::kMaxDatagramBytes)
        return false;
#ifdef _WIN32
    if (message.size() > std::numeric_limits<ULONG>::max())
        return false;
    BCRYPT_ALG_HANDLE alg = nullptr;
    BCRYPT_HASH_HANDLE hash = nullptr;
    auto result = BCryptOpenAlgorithmProvider(
        &alg, BCRYPT_SHA256_ALGORITHM, nullptr, BCRYPT_ALG_HANDLE_HMAC_FLAG);
    if (!BCRYPT_SUCCESS(result)) return false;
    result = BCryptCreateHash(alg, &hash, nullptr, 0,
        const_cast<PUCHAR>(key.data()), static_cast<ULONG>(key.size()), 0);
    bool ok = BCRYPT_SUCCESS(result);
    if (ok) {
        result = BCryptHashData(hash,
            const_cast<PUCHAR>(message.data()),
            static_cast<ULONG>(message.size()), 0);
        ok = BCRYPT_SUCCESS(result);
    }
    if (ok) {
        result = BCryptFinishHash(hash, digest.data(),
                                  static_cast<ULONG>(digest.size()), 0);
        ok = BCRYPT_SUCCESS(result);
    }
    if (hash) (void)BCryptDestroyHash(hash);
    (void)BCryptCloseAlgorithmProvider(alg, 0);
#else
    unsigned int n = 0;
    const auto* result = HMAC(EVP_sha256(), key.data(),
        static_cast<int>(key.size()),
        message.data(), message.size(), digest.data(), &n);
    const bool ok = result != nullptr && n == digest.size();
#endif
    if (!ok) digest.fill(0);
    return ok;
}
inline bool EqualTag(std::span<const std::uint8_t> a,
                     std::span<const std::uint8_t> b) noexcept {
    if (a.size() != DirectReceiver::kTagBytes ||
        b.size() != DirectReceiver::kTagBytes) return false;
#ifdef _WIN32
    // Fixed 16-byte compare with no data-dependent early return.
    volatile std::uint32_t different = 0;
    for (std::size_t i=0; i<DirectReceiver::kTagBytes; ++i)
        different = different | std::uint32_t(a[i] ^ b[i]);
    return different == 0;
#else
    return CRYPTO_memcmp(a.data(), b.data(), DirectReceiver::kTagBytes) == 0;
#endif
}
} // namespace CryptoDetail

class DirectionMac final {
public:
    DirectionMac() = default;
    ~DirectionMac() { Clear(); }
    DirectionMac(const DirectionMac&) = delete;
    DirectionMac& operator=(const DirectionMac&) = delete;
    DirectionMac(DirectionMac&&) = delete;
    DirectionMac& operator=(DirectionMac&&) = delete;

    bool InstallKey(std::span<const std::uint8_t> key) noexcept {
        Clear();
        if (key.size() != key_.size() ||
            std::all_of(key.begin(),key.end(),
                        [](std::uint8_t x) { return x==0; }))
            return false;
        std::copy(key.begin(), key.end(), key_.begin());
        ready_ = true;
        return true;
    }
    bool Tag(std::span<const std::uint8_t> authenticated,
             std::span<std::uint8_t> tag_out) const noexcept {
        if (tag_out.size() != DirectReceiver::kTagBytes)
            return false;
        std::fill(tag_out.begin(), tag_out.end(), 0);
        if (!ready_) return false;
        std::array<std::uint8_t,32> digest{};
        const bool ok = CryptoDetail::Sha256Hmac(key_, authenticated, digest);
        if (ok) std::copy_n(digest.begin(),tag_out.size(),tag_out.begin());
        CryptoDetail::Erase(digest);
        return ok;
    }
    bool Verify(std::span<const std::uint8_t> authenticated,
                std::span<const std::uint8_t> tag) const noexcept {
        if (!ready_ || tag.size() != DirectReceiver::kTagBytes) return false;
        std::array<std::uint8_t,16> expected{};
        const bool ok = Tag(authenticated, expected);
        const bool valid = ok && CryptoDetail::EqualTag(expected,tag);
        CryptoDetail::Erase(expected);
        return valid;
    }
    static bool VerifyCallback(std::span<const std::uint8_t> authenticated,
                               std::span<const std::uint8_t> tag,
                               void* context) noexcept {
        return context &&
            static_cast<const DirectionMac*>(context)->Verify(authenticated,tag);
    }
    void Clear() noexcept {
        CryptoDetail::Erase(key_);
        ready_=false;
    }
    bool ready() const noexcept { return ready_; }

private:
    std::array<std::uint8_t,32> key_{};
    bool ready_=false;
};

// Encodes the V58 wire format with a real tag and non-wrapping monotonically
// increasing sequence. Does not create sockets, grant consent or route traffic.
// A new peer/session requires a new authenticated grant and fresh directional
// key; resetting only the sequence under the same key is forbidden.
class DirectEncoder final {
public:
    DirectEncoder()=default;
    bool Arm(const PeerTicket& ticket, DirectionMac& mac,
             std::int64_t now_ms) noexcept {
        Reset();
        if (!mac.ready() || !Validate(ticket,now_ms)) return false;
        ticket_=ticket;mac_=&mac;started_=now_ms;next_=1;
        return true;
    }
    bool Encode(DirectKind kind, std::span<const std::uint8_t> payload,
                std::int64_t now_ms, std::vector<std::uint8_t>& encoded) noexcept {
        encoded.clear();
        if (!mac_ || !mac_->ready() || next_ == 0 ||
            now_ms < started_) return false;
        if (now_ms > ticket_.expires_at_ms) { Reset();return false; }
        if (payload.size() > DirectReceiver::kMaxPayloadBytes ||
            (kind == DirectKind::GameData ? payload.empty() : !payload.empty()))
            return false;
        const auto kind_value=static_cast<std::uint8_t>(kind);
        if (kind_value < 1 || kind_value > 4) return false;
        encoded.reserve(DirectReceiver::kHeaderBytes + payload.size() +
                        DirectReceiver::kTagBytes);
        encoded.insert(encoded.end(),{'S','H','P','1',1,kind_value,0,0});
        Append64(encoded,ticket_.session_epoch);
        Append64(encoded,ticket_.pair_binding);
        Append64(encoded,ticket_.authenticated_sender);
        Append64(encoded,ticket_.local_receiver);
        Append64(encoded,next_);
        const auto size=static_cast<std::uint16_t>(payload.size());
        encoded.push_back(static_cast<std::uint8_t>(size));
        encoded.push_back(static_cast<std::uint8_t>(size >> 8));
        encoded.push_back(0);encoded.push_back(0);
        encoded.insert(encoded.end(),payload.begin(),payload.end());
        const auto tagged=encoded.size();
        encoded.resize(tagged+DirectReceiver::kTagBytes);
        if (!mac_->Tag(std::span<const std::uint8_t>(encoded.data(),tagged),
                       std::span<std::uint8_t>(encoded.data()+tagged,
                                               DirectReceiver::kTagBytes))) {
            encoded.clear();return false;
        }
        ++next_; // UINT64_MAX becomes 0 and fails closed on the next call.
        return true;
    }
    void Reset() noexcept {
        ticket_={};mac_=nullptr;started_=0;next_=0;
    }
private:
    static bool Validate(const PeerTicket& t,std::int64_t now) noexcept {
        return t.server_grant_verified && t.both_consented &&
            t.version_compatible && t.session_epoch && t.pair_binding &&
            t.authenticated_sender && t.local_receiver &&
            t.authenticated_sender != t.local_receiver &&
            t.expires_at_ms > now;
    }
    static void Append64(std::vector<std::uint8_t>& b,std::uint64_t v) {
        for (unsigned i=0;i<64;i+=8)
            b.push_back(static_cast<std::uint8_t>(v >> i));
    }
    PeerTicket ticket_{};
    DirectionMac* mac_=nullptr; // owner must outlive the encoder
    std::int64_t started_=0;
    std::uint64_t next_=0;
};
} // namespace SeamlessHunt::Hybrid
