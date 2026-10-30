// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V134: the missing link between an authenticated V84 paired mTLS lease,
// completed V91 SAME-SOCKET signed NAT handshake, V106 direction-separated
// SHY2 crypto, and the ORIGINAL native Game P2PTransport direct egress router.
//
// DEV/RESEARCH ONLY. It MUST NOT self-authorize a peer or auto-run on launch.
// The game caller must own and synchronize all referenced state for the full
// lifetime of a slot, must keep gameplay Direct DISABLED by default, and must
// invalidate all three slots on server/session/party/host/map/consent changes.
// The native sender still routes every reliable/ACK and world message to shadNet;
// a failed encrypted direct callback returns RelayRequired to the ORIGINAL route.
#include "sh_native_shy2_grant_cutover_v106.hpp"
#include "sh_native_direct_tx.hpp"
#include <cstdint>
#include <limits>
#include <string_view>

namespace SeamlessHunt::Hybrid {

struct SignedNatRouteLeaseV134 final {
    NativeSealedGrantInboxV84* verified_inbox=nullptr;
    const NatProbeProofV91* signed_nat_proof=nullptr;
    CurrentWorld refresh_world=nullptr;
    void* world_ctx=nullptr;

    // NativeDirectSender invokes this EVERY candidate SEND, not once during
    // install. The original game owns the inbox and proof, and must guard
    // against concurrent revoke/handshake/session replacement while called.
    static bool ReversePathReady(const PeerTicket& ticket,
        PhysicalV4 physical, VirtualV4 virtual_peer,
        std::int64_t now_ms, void* context) noexcept {
        auto* self=static_cast<SignedNatRouteLeaseV134*>(context);
        if(!self || !self->verified_inbox || !self->signed_nat_proof ||
           !self->refresh_world || !self->world_ctx || now_ms<=0 ||
           ticket.expires_at_ms<=now_ms ||
           !ticket.server_grant_verified || !ticket.both_consented ||
           !ticket.version_compatible)
            return false;
        const auto* offer=self->verified_inbox->PendingForNat(
            static_cast<std::uint64_t>(now_ms));
        if(!offer || !self->signed_nat_proof->VerifiedFor(
               *offer,static_cast<std::uint64_t>(now_ms)) ||
           ticket.session_epoch!=offer->world_revision ||
           ticket.pair_binding!=offer->pair_binding ||
           ticket.expires_at_ms!=static_cast<std::int64_t>(offer->expires_ms) ||
           ticket.authenticated_sender!=AeadDetail::Load64(
               offer->recipient_account.data()) ||
           ticket.local_receiver!=AeadDetail::Load64(
               offer->sender_account.data()) ||
           physical.addr_nbo!=offer->peer_ipv4_nbo ||
           physical.port_nbo!=offer->peer_port_nbo ||
           virtual_peer.addr_nbo!=offer->peer_virtual_ipv4_nbo ||
           virtual_peer.port_nbo!=offer->peer_virtual_port_nbo)
            return false;
        ChannelAuthority world{};
        if(!self->refresh_world(world,self->world_ctx))
            return false;
        return world.session_grant_verified && world.both_peers_consented &&
               world.peer_binding_verified &&
               world.both_on_same_authorized_team &&
               world.protocol_compatible && world.map_known &&
               world.map_epoch_verified && world.both_on_same_map;
    }

    // Call ONLY after NativeShy2GrantCutoverV106::Install returned true.
    // An absent SHY2 crypto slot is harmless: actual authenticated transmit
    // fails and the sender falls back via shadNet. Never derive a Grant from
    // a client flag, raw IP or untrusted UDP; derive only from live V84 inbox.
    static bool ArmAfterVerifiedCrypto(
        NativeDirectSender& router, std::size_t slot,
        SignedNatRouteLeaseV134& stable_lease,
        std::string_view server_verified_native_sender,
        AuthenticatedDirectTransmit send_encrypted_shy2,
        void* actual_game_socket,
        std::int64_t now_ms) noexcept {
        if(slot>=NativeGameAeadEgress::kMaxRemoteHunters ||
           !send_encrypted_shy2 || !actual_game_socket ||
           server_verified_native_sender.empty() ||
           !stable_lease.verified_inbox || !stable_lease.signed_nat_proof ||
           !stable_lease.refresh_world || !stable_lease.world_ctx ||
           now_ms<=0)
            return false;
        const auto* offer=stable_lease.verified_inbox->PendingForNat(
            static_cast<std::uint64_t>(now_ms));
        if(!offer || !stable_lease.signed_nat_proof->VerifiedFor(
               *offer,static_cast<std::uint64_t>(now_ms)) ||
           offer->expires_ms>static_cast<std::uint64_t>(
               std::numeric_limits<std::int64_t>::max()))
            return false;
        const auto self=AeadDetail::Load64(offer->recipient_account.data());
        const auto peer=AeadDetail::Load64(offer->sender_account.data());
        if(!self || !peer || self==peer)
            return false;
        const PeerTicket ticket{
            .session_epoch=offer->world_revision,
            .pair_binding=offer->pair_binding,
            .authenticated_sender=self,
            .local_receiver=peer,
            .expires_at_ms=static_cast<std::int64_t>(offer->expires_ms),
            .server_grant_verified=true,
            .both_consented=true,
            .version_compatible=true
        };
        const Grant grant{
            .session_epoch=ticket.session_epoch,
            .peer_binding=ticket.pair_binding,
            .valid_until_ms=ticket.expires_at_ms,
            .verified_server_authorization=true,
            .local_consent=true,
            .peer_consent=true,
            .protocol_compatible=true
        };
        const PhysicalV4 physical{offer->peer_ipv4_nbo,offer->peer_port_nbo};
        const VirtualV4 virtual_peer{
            offer->peer_virtual_ipv4_nbo,offer->peer_virtual_port_nbo};
        if(!ReversePathReady(ticket,physical,virtual_peer,now_ms,&stable_lease))
            return false;
        return router.Arm(slot,ticket,grant,virtual_peer,physical,
                          server_verified_native_sender,
                          stable_lease.refresh_world,stable_lease.world_ctx,
                          send_encrypted_shy2,actual_game_socket,
                          ReversePathReady,&stable_lease,now_ms);
    }
};
} // namespace SeamlessHunt::Hybrid
