// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "sh_direct_datagram.hpp"
#include "sh_game_frame_offload.hpp"
#include "sh_hybrid_selector.hpp"
#include <cstdint>
#include <span>
#include <string>
#include <string_view>

// V59: connect the authenticated UDP envelope with the existing native SHAD
// game packet policy and the Direct/Relay selector. This is NOT plugged into
// the Yharnam Together runtime sockets yet, and supplies no MAC or NAT code.
// All inputs marked server-verified MUST originate in actual authenticated
// server rendezvous / current world authority, not from untrusted peer JSON.
namespace SeamlessHunt::Hybrid {

enum class IngressStatus : std::uint8_t {
    Reject, AuthenticatedProbeOrHeartbeat, AuthenticatedGame
};

class DirectIngress final {
public:
    bool Arm(const PeerTicket& peer, const Grant& selector_grant,
             std::string_view server_verified_game_sender,
             std::int64_t now_ms) {
        Reset();
        // One atomic grant identity and lifetime for MAC, selector and game.
        if (peer.session_epoch != selector_grant.session_epoch ||
            peer.pair_binding != selector_grant.peer_binding ||
            peer.expires_at_ms != selector_grant.valid_until_ms ||
            !peer.server_grant_verified ||
            !selector_grant.verified_server_authorization ||
            !peer.both_consented || !selector_grant.local_consent ||
            !selector_grant.peer_consent ||
            !peer.version_compatible || !selector_grant.protocol_compatible ||
            server_verified_game_sender.empty() ||
            server_verified_game_sender.size() > 255)
            return false;
        if (!receiver_.Arm(peer, now_ms))
            return false;
        if (!selector_.Begin(selector_grant, now_ms)) {
            receiver_.Reset();
            return false;
        }
        verified_sender_ = server_verified_game_sender;
        inbound_ticket_ = peer;
        epoch_ = peer.session_epoch;
        return true;
    }

    // The game payload is borrowed from bytes and may only be used while
    // those original bytes remain alive. Reject never reaches GameLink.
    IngressStatus Receive(std::span<const std::uint8_t> bytes,
                          std::int64_t now_ms,
                          VerifyDirectTag mac_verifier, void* crypto_context,
                          const ChannelAuthority& current_world_authority,
                          std::span<const std::uint8_t>& game_payload) noexcept {
        game_payload = {};
        DirectFrame packet{};
        if (!receiver_.Receive(bytes, now_ms, mac_verifier, crypto_context, packet))
            return IngressStatus::Reject;
        if (packet.kind == DirectKind::Probe ||
            packet.kind == DirectKind::ProbeAck) {
            return selector_.VerifiedProbe(
                BoundEpoch(), packet.sequence, true, now_ms)
                ? IngressStatus::AuthenticatedProbeOrHeartbeat
                : IngressStatus::Reject;
        }
        if (packet.kind == DirectKind::Heartbeat) {
            return selector_.VerifiedDirectHeartbeat(
                BoundEpoch(), packet.sequence, true, now_ms)
                ? IngressStatus::AuthenticatedProbeOrHeartbeat
                : IngressStatus::Reject;
        }
        if (packet.kind != DirectKind::GameData ||
            selector_.Choose(true, now_ms) != Path::Direct)
            return IngressStatus::Reject;

        // Validation of the entire SHAD frame (including mixed packet classes)
        // takes place AFTER the UDP MAC, anti-replay and pair binding checks.
        if (!EligibleNativeWireFrame(packet.payload, verified_sender_,
                                     current_world_authority,
                                     false /* GameLink reliable migration not wired */).direct_eligible)
            return IngressStatus::Reject;
        game_payload = packet.payload;
        return IngressStatus::AuthenticatedGame;
    }

    Path CurrentPath(std::int64_t now_ms) noexcept {
        return selector_.Choose(true, now_ms);
    }

    // A direct sender can only share this link after the opposite direction
    // was authenticated for EXACTLY the same server-approved session/pair,
    // with sender/receiver IDs reversed. Different pairs/epochs fail closed.
    bool MatchesReverse(const PeerTicket& outbound) const noexcept {
        return receiver_.armed() &&
               inbound_ticket_.session_epoch != 0 &&
               inbound_ticket_.session_epoch == outbound.session_epoch &&
               inbound_ticket_.pair_binding == outbound.pair_binding &&
               inbound_ticket_.expires_at_ms == outbound.expires_at_ms &&
               inbound_ticket_.authenticated_sender == outbound.local_receiver &&
               inbound_ticket_.local_receiver == outbound.authenticated_sender &&
               inbound_ticket_.authenticated_sender !=
                   inbound_ticket_.local_receiver &&
               inbound_ticket_.server_grant_verified &&
               inbound_ticket_.both_consented &&
               inbound_ticket_.version_compatible &&
               outbound.server_grant_verified && outbound.both_consented &&
               outbound.version_compatible;
    }

    // A local sendto() failure immediately prevents further direct attempts.
    // Existing shadNet routing remains available; retry needs an explicit
    // re-probe after the cooldown and a still-valid server-issued grant.
    void DirectTransmitFailed(std::int64_t now_ms) noexcept {
        selector_.Fallback(now_ms);
    }

    void Reset() noexcept {
        receiver_.Reset();
        selector_.Reset();
        verified_sender_.clear();
        inbound_ticket_ = {};
        epoch_ = 0;
    }

private:
    std::uint64_t BoundEpoch() const noexcept { return epoch_; }
    DirectReceiver receiver_{};
    Selector selector_{};
    std::string verified_sender_{};
    PeerTicket inbound_ticket_{};
    std::uint64_t epoch_ = 0;
};

} // namespace SeamlessHunt::Hybrid
