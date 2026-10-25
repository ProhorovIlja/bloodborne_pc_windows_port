// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "sh_native_direct_rx.hpp"
#include <array>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <span>
#include <string_view>

// V71: fail-closed Direct/Relay *send* boundary for the original
// P2PTransport::SendFrame. The REAL game creates this router, with ZERO
// installed peers. A future authenticated encrypted control channel must
// own the server grant, directional key, NAT candidate, replay/rekey logic
// and authenticated SHP1 encoder/same-socket send callback before calling Arm.
// No "peer said so" flags from UDP, friends list or local JSON are accepted.
namespace SeamlessHunt::Hybrid {

using AuthenticatedDirectTransmit = bool (*)(
    PhysicalV4 peer, std::span<const std::uint8_t> complete_native_frame,
    std::int64_t now_ms, void* trusted_crypto_socket_owner) noexcept;
// The runtime must consult an authenticated, MAC-verified reverse path from
// NativeDirectReceiver, not a client-supplied "connected" boolean.
using VerifiedReversePath = bool (*)(const PeerTicket& outbound_ticket,
    PhysicalV4 physical_peer, VirtualV4 virtual_peer,
    std::int64_t now_ms, void* trusted_native_receiver) noexcept;

enum class NativeTxStatus : std::uint8_t {
    RelayRequired, DirectSubmitted
};

class NativeDirectSender final {
public:
    static constexpr std::size_t kMaxAuthorizedPeers=8;
    static constexpr std::int64_t kFailureCooldownMs=10000;

    // Must be called ONLY after authenticated server grant + NAT candidate +
    // mutual consent and direct packet authentication, not before probe ACKs.
    // The caller must serialize Arm/Revoke/Send with the game transport lock.
    bool Arm(std::size_t slot, const PeerTicket& server_ticket,
             const Grant& server_grant, VirtualV4 virtual_peer,
             PhysicalV4 physical_peer, std::string_view local_native_sender,
             CurrentWorld refresh_authority, void* authority_ctx,
             AuthenticatedDirectTransmit send_authenticated,
             void* crypto_socket_owner,
             VerifiedReversePath verified_reverse, void* receiver_owner,
             std::int64_t now_ms) noexcept {
        if(slot>=kMaxAuthorizedPeers) return false;
        auto& link=links_[slot];
        link.Reset();
        if(!server_ticket.server_grant_verified ||
           !server_ticket.both_consented ||
           !server_ticket.version_compatible ||
           !server_ticket.session_epoch || !server_ticket.pair_binding ||
           !server_ticket.authenticated_sender || !server_ticket.local_receiver ||
           server_ticket.authenticated_sender==server_ticket.local_receiver ||
           server_ticket.expires_at_ms<=now_ms ||
           server_grant.session_epoch!=server_ticket.session_epoch ||
           server_grant.peer_binding!=server_ticket.pair_binding ||
           server_grant.valid_until_ms!=server_ticket.expires_at_ms ||
           !server_grant.verified_server_authorization ||
           !server_grant.local_consent || !server_grant.peer_consent ||
           !server_grant.protocol_compatible ||
           !virtual_peer.addr_nbo || !virtual_peer.port_nbo ||
           !physical_peer.addr_nbo || !physical_peer.port_nbo ||
           local_native_sender.empty() || local_native_sender.size()>255 ||
           !refresh_authority || !authority_ctx ||
           !send_authenticated || !crypto_socket_owner ||
           !verified_reverse || !receiver_owner)
            return false;
        link.virtual_peer=virtual_peer;
        link.physical_peer=physical_peer;
        link.sender=local_native_sender;
        link.refresh=refresh_authority;
        link.authority_ctx=authority_ctx;
        link.transmit=send_authenticated;
        link.crypto_ctx=crypto_socket_owner;
        link.outbound_ticket=server_ticket;
        link.verified_reverse=verified_reverse;
        link.receiver_ctx=receiver_owner;
        link.expires_at_ms=server_ticket.expires_at_ms;
        link.active=true;
        return true;
    }

    // Invoked ONLY for a virtual peer for which the ORIGINAL game would
    // route a frame through shadNet. On any doubt return RelayRequired.
    // No direct+relay duplicate for a submitted frame.
    NativeTxStatus TrySend(VirtualV4 intended_peer,
                           std::span<const std::uint8_t> complete_native_frame,
                           std::int64_t now_ms) noexcept {
        for(auto& link:links_) {
            if(!link.active || link.virtual_peer.addr_nbo!=intended_peer.addr_nbo ||
               link.virtual_peer.port_nbo!=intended_peer.port_nbo)
                continue;
            if(now_ms<0 || now_ms>=link.expires_at_ms) {
                link.Reset();
                return NativeTxStatus::RelayRequired;
            }
            if(now_ms<link.cooldown_until_ms)
                return NativeTxStatus::RelayRequired;
            ChannelAuthority current{}; // DENY until refreshed by server
            if(!link.refresh || !link.refresh(current,link.authority_ctx)) {
                link.Reset();
                return NativeTxStatus::RelayRequired;
            }
            if(!link.verified_reverse ||
               !link.verified_reverse(link.outbound_ticket,link.physical_peer,
                                      link.virtual_peer,now_ms,link.receiver_ctx))
                return NativeTxStatus::RelayRequired;
            if(complete_native_frame.empty() ||
               complete_native_frame.size()>DirectReceiver::kMaxPayloadBytes ||
               !EligibleNativeWireFrame(complete_native_frame,link.sender,
                                        current,
                                        false /* no actual reliable stream handover */).direct_eligible)
                return NativeTxStatus::RelayRequired;
            // The trusted callback must sign the *whole* frame as SHP1, use
            // the actual P2PTransport physical UDP socket, and accurately
            // indicate whether it submitted that datagram.
            if(link.transmit && link.transmit(
                link.physical_peer,complete_native_frame,now_ms,link.crypto_ctx))
                return NativeTxStatus::DirectSubmitted;
            // A send failure must fall back once via original shadNet. No
            // repeated Direct retries per frame during cooldown.
            if(now_ms>std::numeric_limits<std::int64_t>::max()-kFailureCooldownMs)
                link.Reset();
            else
                link.cooldown_until_ms=now_ms+kFailureCooldownMs;
            return NativeTxStatus::RelayRequired;
        }
        return NativeTxStatus::RelayRequired;
    }

    void Revoke(std::size_t slot) noexcept {
        if(slot<kMaxAuthorizedPeers)links_[slot].Reset();
    }
    void RevokeAll() noexcept {
        for(auto& link:links_)link.Reset();
    }

private:
    struct Link {
        VirtualV4 virtual_peer{};
        PhysicalV4 physical_peer{};
        PeerTicket outbound_ticket{};
        VerifiedReversePath verified_reverse=nullptr;
        void* receiver_ctx=nullptr;
        std::string_view sender{}; // borrowed from trusted owner: must outlive Arm
        CurrentWorld refresh=nullptr;
        void* authority_ctx=nullptr;
        AuthenticatedDirectTransmit transmit=nullptr;
        void* crypto_ctx=nullptr;
        std::int64_t expires_at_ms=0;
        std::int64_t cooldown_until_ms=0;
        bool active=false;
        void Reset() noexcept {
            virtual_peer={};physical_peer={};sender={};
            outbound_ticket={};verified_reverse=nullptr;receiver_ctx=nullptr;
            refresh=nullptr;authority_ctx=nullptr;transmit=nullptr;
            crypto_ctx=nullptr;expires_at_ms=0;cooldown_until_ms=0;
            active=false;
        }
    };
    std::array<Link,kMaxAuthorizedPeers> links_{};
};
} // namespace SeamlessHunt::Hybrid
