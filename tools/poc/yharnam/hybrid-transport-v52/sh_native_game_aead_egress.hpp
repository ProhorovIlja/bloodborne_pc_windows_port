// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// Server-authorized SHY2 send boundary for the EXISTING Yharnam Together
// P2PTransport::SendFrame, using the SAME native host_socket and its
// NativeDirectSender reverse-NAT authority barrier. No auto-Arm exists.
// Direct gameplay remains OFF until a live trusted reciprocal grant installs
// matching sender/receiver directional keys and both-side NAT-ready proof.
// In particular shared reliable ACK or channel-class 1 is always RELAY.
#include "sh_native_game_aead_ingress.hpp"
#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include <string_view>
#include <vector>

namespace SeamlessHunt::Hybrid {

class NativeGameAeadEgress final {
public:
    static constexpr std::size_t kMaxRemoteHunters=4;

    bool Arm(std::size_t slot,const PeerTicket& server_ticket,
             std::span<const std::uint8_t> outbound_key,
             std::span<const std::uint8_t> outbound_salt,
             PhysicalV4 peer_physical,VirtualV4 peer_virtual,
             std::string_view server_verified_game_sender,
             CurrentWorld refresh_authority,void* world_state,
             std::int64_t now_ms) noexcept {
        if(slot>=kMaxRemoteHunters || slots_[slot].active ||
           !peer_physical.addr_nbo || !peer_physical.port_nbo ||
           !peer_virtual.addr_nbo || !peer_virtual.port_nbo ||
           server_verified_game_sender.empty() ||
           server_verified_game_sender.size()>255 ||
           !refresh_authority || !world_state)
            return false;
        for(std::size_t i=0;i<kMaxRemoteHunters;++i) {
            if(i==slot || !slots_[i].active)continue;
            const auto& other=slots_[i];
            if((other.physical.addr_nbo==peer_physical.addr_nbo &&
                other.physical.port_nbo==peer_physical.port_nbo) ||
               (other.virtual_peer.addr_nbo==peer_virtual.addr_nbo &&
                other.virtual_peer.port_nbo==peer_virtual.port_nbo) ||
               (other.epoch==server_ticket.session_epoch &&
                other.pair==server_ticket.pair_binding))
                return false;
        }
        Link& link=slots_[slot];
        if(!link.sealer.Arm(server_ticket,outbound_key,outbound_salt,now_ms))
            return false;
        link.physical=peer_physical;
        link.virtual_peer=peer_virtual;
        std::copy(server_verified_game_sender.begin(),
                  server_verified_game_sender.end(),link.sender.begin());
        link.sender_len=static_cast<std::uint8_t>(
            server_verified_game_sender.size());
        link.refresh=refresh_authority;
        link.world=world_state;
        link.expires=server_ticket.expires_at_ms;
        link.epoch=server_ticket.session_epoch;
        link.pair=server_ticket.pair_binding;
        link.active=true;
        return true;
    }

    // Only the actual game's NativeDirectSender authenticated callback may
    // call this: that parent MUST have already proven signed reverse NAT and
    // server ticket. A failed seal requires the unmodified shadNet send path.
    bool Seal(PhysicalV4 expected_physical,
              std::span<const std::uint8_t> complete_native_frame,
              std::int64_t now_ms,std::vector<std::uint8_t>& wire) {
        wire.clear();
        for(auto& link:slots_) {
            if(!link.active || link.physical.addr_nbo!=expected_physical.addr_nbo ||
               link.physical.port_nbo!=expected_physical.port_nbo)
                continue;
            if(now_ms<0 || now_ms>=link.expires) {
                link.Revoke();
                return false;
            }
            ChannelAuthority world{}; // always refreshed, never cached
            if(!link.refresh || !link.refresh(world,link.world)) {
                link.Revoke();
                return false;
            }
            if(!EligibleNativeWireFrame(
                   complete_native_frame,
                   std::string_view(link.sender.data(),link.sender_len),
                   world,false /* never offload shared ACK lane */).direct_eligible)
                return false;
            return link.sealer.SealGame(complete_native_frame,now_ms,wire);
        }
        return false; // no authenticated server-installed SHY2 slot
    }

    void Revoke(std::size_t slot) noexcept {
        if(slot<kMaxRemoteHunters)slots_[slot].Revoke();
    }
    void RevokeAll() noexcept {
        for(auto& link:slots_)link.Revoke();
    }

private:
    struct Link final {
        NativeGameAeadSealer sealer{};
        PhysicalV4 physical{};
        VirtualV4 virtual_peer{};
        std::array<char,255> sender{};
        std::uint8_t sender_len=0;
        CurrentWorld refresh=nullptr;
        void* world=nullptr;
        std::uint64_t epoch=0,pair=0;
        std::int64_t expires=0;
        bool active=false;
        void Revoke() noexcept {
            sealer.Revoke();
            physical={};virtual_peer={};
            std::fill(sender.begin(),sender.end(),char(0));
            sender_len=0;refresh=nullptr;world=nullptr;
            epoch=0;pair=0;expires=0;active=false;
        }
    };
    std::array<Link,kMaxRemoteHunters> slots_{};
};
} // namespace SeamlessHunt::Hybrid
