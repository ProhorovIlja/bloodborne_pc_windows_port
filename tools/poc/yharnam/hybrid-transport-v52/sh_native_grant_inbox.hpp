// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V82: REAL native-game compatible recipient for encrypted SHG1 P2P offers.
// Pure C++20, Windows CNG / Linux OpenSSL, no Qt/game socket dependency.
// This class is an UNARMED admission/inbox only; it may ONLY be fed the
// response of a *separately verified* authenticated TLS 1.3 connection.
// It does not perform TLS, authenticate a server, establish NAT reachability,
// validate P2P probes or set the game native sender/receiver to Direct.
// Never feed it a plaintext SHLK frame, a UDP packet or untrusted JSON.
#include "sh_secure_grant.hpp"
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include <string_view>

namespace SeamlessHunt::Hybrid {
struct NativeOfferIdentity {
    std::uint64_t self_account=0;     // TLS-verified client account token
    std::uint64_t peer_account=0;     // trusted server-authorized target
    std::uint64_t session_epoch=0;    // live V77 recipient generation
    std::uint64_t world_revision=0;   // live authoritative world fingerprint
    bool locally_opted_in=false;      // actual native game preference
};
using RefreshNativeOfferIdentity=bool (*)(
    NativeOfferIdentity& result,void* trusted_game_state) noexcept;

class NativeSealedGrantInbox final {
public:
    static constexpr std::string_view kPrefix="YT-P2P/V81 OFFER ";
    static constexpr std::size_t kCipherBytes=SecureOfferDetail::kWireBytes;
    static constexpr std::size_t kLineBytes=kPrefix.size()+2*kCipherBytes+1;
    NativeSealedGrantInbox()=default;
    ~NativeSealedGrantInbox(){Reset();}
    NativeSealedGrantInbox(const NativeSealedGrantInbox&)=delete;
    NativeSealedGrantInbox& operator=(const NativeSealedGrantInbox&)=delete;
    NativeSealedGrantInbox(NativeSealedGrantInbox&&)=delete;
    NativeSealedGrantInbox& operator=(NativeSealedGrantInbox&&)=delete;

    // Called from trusted TLS 1.3 client code AFTER validating server CA,
    // server hostname/pin, client identity and the matching current game
    // account. The wrapping key is V80's freshly delivered, session-local
    // 32-byte key (never a password or TLS certificate fingerprint).
    // Monotonic connection serial prevents accidental reusing a previous
    // TLS session while the native game is still running.
    bool BeginTrustedTls(std::span<const std::uint8_t> ephemeral_key,
                         const NativeOfferIdentity& initial,
                         std::uint64_t tls_connection_serial,
                         RefreshNativeOfferIdentity refresh,
                         void* trusted_game_state) noexcept {
        ResetCurrent();
        if(!tls_connection_serial || tls_connection_serial<=last_tls_serial_ ||
           !refresh || !trusted_game_state || !ValidIdentity(initial) ||
           !sealer_.InstallChannelKey(ephemeral_key))
            return false;
        // Refresh on establishment, not just when the offer arrives.
        NativeOfferIdentity actual{};
        if(!refresh(actual,trusted_game_state) ||
           !EqualIdentity(initial,actual)){
            sealer_.Clear();
            return false;
        }
        last_tls_serial_=tls_connection_serial;
        bound_=initial;
        refresh_=refresh;
        game_state_=trusted_game_state;
        active_=true;
        return true;
    }

    // One complete line from the verified TLS stream, not arbitrary packet
    // fragments; the TLS adapter must frame it precisely and cap its bytes.
    // Invalid input burns this TLS session; no stale grants survive.
    bool ReceiveSealedTlsLine(std::string_view line,
                              std::uint64_t now_ms) noexcept {
        if(!active_ || accepted_ || line.size()!=kLineBytes ||
           line.substr(0,kPrefix.size())!=kPrefix ||
           line.back()!='\n') {
            ResetCurrent();
            return false;
        }
        NativeOfferIdentity actual{};
        if(!refresh_ || !refresh_(actual,game_state_) ||
           !EqualIdentity(bound_,actual)) {
            ResetCurrent();return false;
        }
        std::array<std::uint8_t,kCipherBytes> ciphertext{};
        for(std::size_t i=0;i<kCipherBytes;++i){
            const int high=Hex(line[kPrefix.size()+i*2]);
            const int low=Hex(line[kPrefix.size()+i*2+1]);
            if(high<0 || low<0) {
                ResetCurrent();return false;
            }
            ciphertext[i]=static_cast<std::uint8_t>((high<<4)|low);
        }
        SecurePeerOffer verified{};
        const bool opened=sealer_.Open(ciphertext,bound_.self_account,
            bound_.session_epoch,bound_.world_revision,now_ms,verified);
        CryptoDetail::Erase(ciphertext);
        if(!opened || verified.sender_account!=bound_.peer_account ||
           verified.recipient_account!=bound_.self_account ||
           !SecureOfferDetail::Valid(verified,now_ms)) {
            CryptoDetail::Erase(verified.direction_key);
            ResetCurrent();return false;
        }
        // Ensure an epoch/consent change during decryption revokes the offer.
        actual={};
        if(!refresh_(actual,game_state_) || !EqualIdentity(bound_,actual)) {
            CryptoDetail::Erase(verified.direction_key);
            ResetCurrent();return false;
        }
        pending_=verified;
        CryptoDetail::Erase(verified.direction_key);
        sealer_.Clear(); // wrapping key cannot decrypt another offer
        accepted_=true;
        return true;
    }

    // Pending proof is NOT authorization to enable the game UDP route.
    // Caller still needs mutually verified NAT candidates + signed probes,
    // an authenticated current server grant on both directions, encrypted
    // gameplay and safe reliable GameLink ACK handover.
    bool HasCurrentPending(std::uint64_t now_ms) noexcept {
        NativeOfferIdentity actual{};
        if(!active_ || !accepted_ || !refresh_ ||
           !refresh_(actual,game_state_) ||
           !EqualIdentity(bound_,actual) ||
           !SecureOfferDetail::Valid(pending_,now_ms)) {
            ResetCurrent();return false;
        }
        return true;
    }
    // Read-only pending candidate; do not log or serialize the MAC key.
    const SecurePeerOffer* PendingForNat(std::uint64_t now_ms) noexcept {
        return HasCurrentPending(now_ms) ? &pending_ : nullptr;
    }
    void Revoke() noexcept {ResetCurrent();}
    bool IsPending() const noexcept {return active_ && accepted_;}
private:
    static bool ValidIdentity(const NativeOfferIdentity& v) noexcept {
        return v.locally_opted_in && v.self_account && v.peer_account &&
               v.self_account!=v.peer_account && v.session_epoch &&
               v.world_revision;
    }
    static bool EqualIdentity(const NativeOfferIdentity& a,
                              const NativeOfferIdentity& b) noexcept {
        return ValidIdentity(a) && ValidIdentity(b) &&
            a.self_account==b.self_account &&
            a.peer_account==b.peer_account &&
            a.session_epoch==b.session_epoch &&
            a.world_revision==b.world_revision;
    }
    static int Hex(char x) noexcept {
        if(x>='0'&&x<='9')return x-'0';
        if(x>='a'&&x<='f')return x-'a'+10;
        if(x>='A'&&x<='F')return x-'A'+10;
        return -1;
    }
    void ResetCurrent() noexcept {
        CryptoDetail::Erase(pending_.direction_key);
        pending_={};
        sealer_.Clear();bound_={};refresh_=nullptr;game_state_=nullptr;
        active_=false;accepted_=false;
    }
    SealedPeerOffers sealer_{};
    SecurePeerOffer pending_{};
    NativeOfferIdentity bound_{};
    RefreshNativeOfferIdentity refresh_=nullptr;
    void* game_state_=nullptr;
    std::uint64_t last_tls_serial_=0;
    bool active_=false;
    bool accepted_=false;
};
} // namespace SeamlessHunt::Hybrid
