// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "sh_direct_crypto.hpp"
#include "sh_direct_ingress.hpp"
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include <string_view>

// V70: Boundary for the EXISTING Yharnam Together physical UDP ReceiveMain.
// It never creates a socket, broadcasts peer IPs, or modifies shadNet relay.
// An authenticated, encrypted server control plane MUST supply the pair ticket,
// per-direction HMAC key, physical candidate, virtual peer address and current
// authoritative world callback. The native client DOES NOT call Arm yet.
//
// Direct packets without a bound, authenticated path are consumed/dropped;
// they must NEVER fall back into generic virtual-socket delivery.
//
// This is integrity/authentication ONLY. HMAC does not encrypt gameplay.
// Implement transport confidentiality separately before a public rollout.
namespace SeamlessHunt::Hybrid {

struct PhysicalV4 {
    std::uint32_t addr_nbo=0;
    std::uint16_t port_nbo=0;
};
struct VirtualV4 {
    std::uint32_t addr_nbo=0;
    std::uint16_t port_nbo=0;
};
using CurrentWorld = bool (*)(ChannelAuthority& authority, void* context) noexcept;

enum class NativeRxStatus : std::uint8_t { NotDirect, Dropped, Control, Game };

struct NativeRxResult {
    NativeRxStatus status=NativeRxStatus::NotDirect;
    VirtualV4 sender{}; // from VERIFIED server ticket, never from packet source
    std::span<const std::uint8_t> native_game_frame{};
};

inline bool IsSHP1(std::span<const std::uint8_t> datagram) noexcept {
    return datagram.size()>=4 && datagram[0]=='S' && datagram[1]=='H' &&
           datagram[2]=='P' && datagram[3]=='1';
}

class NativeDirectReceiver final {
public:
    static constexpr std::size_t kMaxAuthorizedPeers=8;

    bool Arm(std::size_t slot, const PeerTicket& from_remote,
             const Grant& session_grant,
             std::span<const std::uint8_t> directional_hmac_key,
             PhysicalV4 peer_physical, VirtualV4 peer_virtual,
             std::string_view server_verified_sender,
             CurrentWorld refresh_authority, void* authority_ctx,
             std::int64_t now_ms) {
        if (slot >= kMaxAuthorizedPeers) return false;
        auto& link=links_[slot];
        link.Reset(); // no old replay state or keys survive a regrant
        if (!peer_physical.addr_nbo || !peer_physical.port_nbo ||
            !peer_virtual.addr_nbo || !peer_virtual.port_nbo ||
            refresh_authority==nullptr ||
            !link.mac.InstallKey(directional_hmac_key))
            return false;
        if (!link.ingress.Arm(from_remote,session_grant,
                              server_verified_sender,now_ms)) {
            link.Reset();
            return false;
        }
        link.physical=peer_physical;
        link.virtual_peer=peer_virtual;
        link.refresh=refresh_authority;
        link.context=authority_ctx;
        link.active=true;
        return true;
    }

    void Revoke(std::size_t slot) noexcept {
        if (slot < kMaxAuthorizedPeers) links_[slot].Reset();
    }
    void RevokeAll() noexcept {
        for(auto& link:links_) link.Reset();
    }

    // Intended to run on the existing game's UDP receive thread. The caller
    // must synchronize ALL Arm/Revoke mutations against concurrent Receive.
    // The returned span borrows bytes from the ORIGINAL recvfrom() buffer,
    // valid only until that buffer is overwritten.
    NativeRxResult Receive(PhysicalV4 actual_source,
                            std::span<const std::uint8_t> datagram,
                            std::int64_t now_ms) noexcept {
        if (!IsSHP1(datagram)) return {NativeRxStatus::NotDirect,{},{}};
        if (datagram.size()>DirectReceiver::kMaxDatagramBytes)
            return {NativeRxStatus::Dropped,{},{}};
        for (auto& link:links_) {
            if (!link.active || link.physical.addr_nbo!=actual_source.addr_nbo ||
                link.physical.port_nbo!=actual_source.port_nbo)
                continue;
            ChannelAuthority authority{}; // defaults to deny
            if (!link.refresh || !link.refresh(authority,link.context)) {
                link.Reset(); // revocation or unreachable authority
                return {NativeRxStatus::Dropped,{},{}};
            }
            std::span<const std::uint8_t> native{};
            const auto status=link.ingress.Receive(
                datagram,now_ms,DirectionMac::VerifyCallback,
                &link.mac,authority,native);
            if (status==IngressStatus::AuthenticatedGame)
                return {NativeRxStatus::Game,link.virtual_peer,native};
            if (status==IngressStatus::AuthenticatedProbeOrHeartbeat)
                return {NativeRxStatus::Control,{},{}};
            return {NativeRxStatus::Dropped,{},{}};
        }
        return {NativeRxStatus::Dropped,{},{}}; // unknown endpoint
    }

private:
    struct Link final {
        DirectIngress ingress{};
        DirectionMac mac{};
        PhysicalV4 physical{};
        VirtualV4 virtual_peer{};
        CurrentWorld refresh=nullptr;
        void* context=nullptr;
        bool active=false;
        void Reset() noexcept {
            active=false;
            ingress.Reset();
            mac.Clear();
            physical={};virtual_peer={};refresh=nullptr;context=nullptr;
        }
    };
    std::array<Link,kMaxAuthorizedPeers> links_{};
};
} // namespace SeamlessHunt::Hybrid
