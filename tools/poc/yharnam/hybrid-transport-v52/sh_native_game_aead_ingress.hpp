// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// SHY2 encrypted native-game receive boundary. This class does NOT grant
// authority: its caller must install a CURRENT server-verified pair lease
// after reciprocal TLS/NAT-ready proofs and map/owner/role validation.
// The real game's P2PTransport owns it, but installs NO routes by default.
// On absent/revoked grants SHY2 is consumed, NEVER passed to legacy SHLK.
// Reliable GameLink frames/ACK always stay on the authoritative relay.
#include "sh_native_game_aead.hpp"
#include "sh_native_direct_rx.hpp"
#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include <string_view>
#include <vector>

namespace SeamlessHunt::Hybrid {

struct NativeShy2Result final {
    NativeRxStatus status=NativeRxStatus::NotDirect;
    VirtualV4 sender{}; // from server-verified pair slot, NEVER UDP payload
    std::vector<std::uint8_t> native_game_frame{};
};

inline bool IsSHY2(std::span<const std::uint8_t> bytes) noexcept {
    return bytes.size()>=4 && bytes[0]=='S' && bytes[1]=='H' &&
           bytes[2]=='Y' && bytes[3]=='2';
}

class NativeGameAeadIngress final {
public:
    static constexpr std::size_t kMaxRemoteHunters=4; // five-person party

    bool Arm(std::size_t slot,const PeerTicket& server_ticket,
             std::span<const std::uint8_t> inbound_key,
             std::span<const std::uint8_t> inbound_salt,
             PhysicalV4 physical,VirtualV4 virtual_sender,
             std::string_view server_verified_game_sender,
             CurrentWorld refresh_authority,void* world_state,
             std::int64_t now_ms) noexcept {
        if(slot>=kMaxRemoteHunters || slots_[slot].active ||
           !physical.addr_nbo || !physical.port_nbo ||
           !virtual_sender.addr_nbo || !virtual_sender.port_nbo ||
           server_verified_game_sender.empty() ||
           server_verified_game_sender.size()>255 ||
           !refresh_authority || !world_state)
            return false;
        for(std::size_t i=0;i<kMaxRemoteHunters;++i) {
            if(i==slot || !slots_[i].active)continue;
            const auto& other=slots_[i];
            if((other.physical.addr_nbo==physical.addr_nbo &&
                other.physical.port_nbo==physical.port_nbo) ||
               (other.virtual_sender.addr_nbo==virtual_sender.addr_nbo &&
                other.virtual_sender.port_nbo==virtual_sender.port_nbo) ||
               (other.epoch==server_ticket.session_epoch &&
                other.pair==server_ticket.pair_binding))
                return false; // avoid ambiguous NAT, spoofed virtual peers, replayed pairs
        }
        Link& link=slots_[slot];
        if(!link.opener.Arm(server_ticket,inbound_key,inbound_salt,now_ms))
            return false;
        link.physical=physical;
        link.virtual_sender=virtual_sender;
        std::copy(server_verified_game_sender.begin(),
                  server_verified_game_sender.end(),link.sender.begin());
        link.sender_len=static_cast<std::uint8_t>(
            server_verified_game_sender.size());
        link.refresh=refresh_authority;
        link.world=world_state;
        link.epoch=server_ticket.session_epoch;
        link.pair=server_ticket.pair_binding;
        link.expires=server_ticket.expires_at_ms;
        link.active=true;
        return true;
    }

    NativeShy2Result Receive(PhysicalV4 actual_source,
                             std::span<const std::uint8_t> datagram,
                             std::int64_t now_ms) {
        if(!IsSHY2(datagram))
            return {};
        NativeShy2Result denied{};
        denied.status=NativeRxStatus::Dropped;
        if(datagram.size()>AeadDetail::MaxBytes || now_ms<0)
            return denied;
        for(auto& link:slots_) {
            if(!link.active || link.physical.addr_nbo!=actual_source.addr_nbo ||
               link.physical.port_nbo!=actual_source.port_nbo)
                continue;
            if(now_ms>=link.expires) {
                link.Revoke();
                return denied;
            }
            ChannelAuthority current{}; // deny until ORIGINAL server/world refresh
            if(!link.refresh || !link.refresh(current,link.world)) {
                link.Revoke(); // revoked consent/session/owner, never revive automatically
                return denied;
            }
            if(!link.opener.OpenGame(datagram,now_ms,denied.native_game_frame))
                return denied;
            // Both encrypted identity AND nested native SHAD sender/channel
            // must be server-authorized, with the actual GameLink ACK lane
            // deliberately left on shadNet (no hypothetical handover flag).
            if(!EligibleNativeWireFrame(
                  denied.native_game_frame,
                  std::string_view(link.sender.data(),link.sender_len),
                  current,false).direct_eligible) {
                AeadDetail::Erase(denied.native_game_frame);
                denied.native_game_frame.clear();
                return denied;
            }
            denied.status=NativeRxStatus::Game;
            denied.sender=link.virtual_sender;
            return denied;
        }
        return denied; // unsolicited encrypted traffic never reaches game
    }

    void Revoke(std::size_t slot) noexcept {
        if(slot<kMaxRemoteHunters)slots_[slot].Revoke();
    }
    void RevokeAll() noexcept {
        for(auto& link:slots_)link.Revoke();
    }

private:
    struct Link final {
        NativeGameAeadOpener opener{};
        PhysicalV4 physical{};
        VirtualV4 virtual_sender{};
        std::array<char,255> sender{};
        std::uint8_t sender_len=0;
        CurrentWorld refresh=nullptr;
        void* world=nullptr;
        std::uint64_t epoch=0,pair=0;
        std::int64_t expires=0;
        bool active=false;
        void Revoke() noexcept {
            opener.Revoke();
            physical={};virtual_sender={};
            std::fill(sender.begin(),sender.end(),char(0));
            sender_len=0;refresh=nullptr;world=nullptr;
            epoch=0;pair=0;expires=0;active=false;
        }
    };
    std::array<Link,kMaxRemoteHunters> slots_{};
};
} // namespace SeamlessHunt::Hybrid
