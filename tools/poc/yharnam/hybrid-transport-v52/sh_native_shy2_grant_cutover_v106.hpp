// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V106: one trusted mTLS inbox -> signed NAT proof -> TWO independent
// direction-separated AES-256-GCM native game slots, each in original SHY2
// ingress/egress. This is a reusable STRICT CUTOVER GATE; it does not enable
// production Direct, accept UDP as a grant, install sender callbacks, or
// modify GameLink reliable/ACK sequence ownership. Caller must own the
// original game grant/world locks and use a current server/party/owner check.
#include "sh_nat_probe_v91.hpp"
#include "sh_native_grant_inbox_v84.hpp"
#include "sh_native_game_aead_egress.hpp"
#include "sh_pair_aead_keys.hpp"
#include <cstddef>
#include <cstdint>
#include <limits>
#include <string_view>

namespace SeamlessHunt::Hybrid {
class NativeShy2GrantCutoverV106 final {
public:
    static bool Install(
        NativeSealedGrantInboxV84& verified_tls_inbox,
        const NatProbeProofV91& original_same_socket_nat_proof,
        std::size_t slot, NativeGameAeadIngress& inbound,
        NativeGameAeadEgress& outbound,
        std::string_view local_native_sender,
        std::string_view remote_native_sender,
        CurrentWorld live_original_game_world,void* world_ctx,
        std::uint64_t now_ms) noexcept {
        // All four game-peer slots are bounded, never dynamically expanded.
        if(slot>=NativeGameAeadIngress::kMaxRemoteHunters ||
           slot>=NativeGameAeadEgress::kMaxRemoteHunters ||
           !now_ms || now_ms>static_cast<std::uint64_t>(
               std::numeric_limits<std::int64_t>::max()) ||
           !live_original_game_world || !world_ctx ||
           local_native_sender.empty() || local_native_sender.size()>255 ||
           remote_native_sender.empty() || remote_native_sender.size()>255 ||
           local_native_sender==remote_native_sender)
            return false;
        // Verify not just the presence of a pending secret but ALSO that the
        // exact signed nonce handshake completed for this SAME mTLS pair,
        // time/endpoint, world and key. Neither client flag authorizes it.
        const auto* offer=verified_tls_inbox.PendingForNat(now_ms);
        if(!offer || !original_same_socket_nat_proof.VerifiedFor(*offer,now_ms) ||
           offer->expires_ms>static_cast<std::uint64_t>(
               std::numeric_limits<std::int64_t>::max()))
            return false;
        ChannelAuthority authority{};
        if(!live_original_game_world(authority,world_ctx) ||
           !authority.session_grant_verified ||
           !authority.both_peers_consented ||
           !authority.peer_binding_verified ||
           !authority.both_on_same_authorized_team ||
           !authority.protocol_compatible ||
           !authority.map_known ||
           !authority.map_epoch_verified ||
           !authority.both_on_same_map)
            return false;
        // Do NOT copy mutable server-verified booleans from any UDP payload.
        // World revision is shared between the reciprocal SHG2 recipients
        // even when their separate account-login session epochs differ.
        // This shared epoch and the CSPRNG pair bind the AEAD wire header.
        const auto self=AeadDetail::Load64(offer->recipient_account.data());
        const auto remote=AeadDetail::Load64(offer->sender_account.data());
        if(!self || !remote || self==remote)return false;
        PeerTicket tx{};
        tx.session_epoch=offer->world_revision;
        tx.pair_binding=offer->pair_binding;
        tx.authenticated_sender=self;
        tx.local_receiver=remote;
        tx.expires_at_ms=static_cast<std::int64_t>(offer->expires_ms);
        tx.server_grant_verified=tx.both_consented=
           tx.version_compatible=true;
        PeerTicket rx=tx;
        rx.authenticated_sender=remote;
        rx.local_receiver=self;
        NativePairAeadMaterial outbound_material;
        NativePairAeadMaterial inbound_material;
        if(!NativePairAeadKeys::DeriveFromVerifiedInbox(
               *offer,true,now_ms,outbound_material) ||
           !NativePairAeadKeys::DeriveFromVerifiedInbox(
               *offer,false,now_ms,inbound_material) ||
           outbound_material.key==inbound_material.key ||
           outbound_material.salt==inbound_material.salt)
            return false;
        const PhysicalV4 physical{offer->peer_ipv4_nbo,offer->peer_port_nbo};
        const VirtualV4 virtual_peer{
            offer->peer_virtual_ipv4_nbo,offer->peer_virtual_port_nbo};
        const auto when=static_cast<std::int64_t>(now_ms);
        if(!outbound.Arm(slot,tx,outbound_material.key,
                         outbound_material.salt,physical,virtual_peer,
                         local_native_sender,live_original_game_world,
                         world_ctx,when))
            return false;
        if(!inbound.Arm(slot,rx,inbound_material.key,
                        inbound_material.salt,physical,virtual_peer,
                        remote_native_sender,live_original_game_world,
                        world_ctx,when)) {
            outbound.Revoke(slot); // fail closed on partial installation
            return false;
        }
        return true;
    }
};
} // namespace SeamlessHunt::Hybrid
