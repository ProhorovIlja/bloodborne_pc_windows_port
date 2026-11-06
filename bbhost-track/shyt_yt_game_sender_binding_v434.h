// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V434: source-compatible, fail-closed inbound GameFrame sender boundary.
// Use only after the ORIGINAL YT Noise-NK server link has authenticated its
// sign-in OnlineID. The sender INSIDE a GameFrame is untrusted metadata:
// original Hub::Routed() in YT v1.4.0 checks channel policy against the
// actual source/target endpoint, but does not bind GameFrame.sender to the
// signed-in source link's OnlineID. A recipient keys its reliable streams
// by GameFrame.sender, so an unbound string is not safe to deliver.
//
// This helper can be attached as a separate pinned server source patch.
// It is NOT a crypto primitive, a direct P2P permission, or a server
// room/map/owner grant. No packet is sent, copied or written to a guest.
// Original source: server/coop/game_link.h SHA Git blob
// 5029581251bfe5decf562c19a10bdd079150cdad.
#include "coop/game_link.h"
#include <cstdint>
#include <string_view>

namespace SeamlessHunt {
struct YtGameSenderBindingV434 final {
    enum class Status : std::uint8_t {
        Accepted, MissingLinkIdentity, SpoofedSender, InvalidRun,
        InvalidEntries, StaleRun
    };
    // GameLinkPeer normally targets 1200 bytes / datagram but admits
    // a single native packet up to 0x6408 bytes. 256 entries is already
    // well above the number of 9-byte entries that fit a 1200B frame;
    // using one bound avoids accidental 65,535-entry parsing storms.
    static constexpr std::size_t MaxEntries=256u;
    static constexpr std::size_t MaxNativeBytes=0x6408u;
    static constexpr std::uint32_t NativeChannelCount=68u;
    static bool CanonicalOnlineId(std::string_view id) noexcept {
        if(id.size()<3u || id.size()>16u)return false;
        for(unsigned char c:id) {
            if(!((c>='0' && c<='9') || (c>='a' && c<='z') ||
                 (c>='A' && c<='Z') || c=='_' || c=='-'))
                return false;
        }
        return true;
    }
    static std::uint32_t Channel(std::span<const std::uint8_t> native) noexcept {
        if(native.size()<8u)return NativeChannelCount+1u;
        return static_cast<std::uint32_t>(native[0]) |
               static_cast<std::uint32_t>(native[1])<<8u |
               static_cast<std::uint32_t>(native[2])<<16u |
               static_cast<std::uint32_t>(native[3])<<24u;
    }
    static std::uint32_t Size(std::span<const std::uint8_t> native) noexcept {
        if(native.size()<8u)return UINT32_MAX;
        return static_cast<std::uint32_t>(native[4]) |
               static_cast<std::uint32_t>(native[5])<<8u |
               static_cast<std::uint32_t>(native[6])<<16u |
               static_cast<std::uint32_t>(native[7])<<24u;
    }
    static Status Inspect(const BloodborneCoop::GameFrame& f,
                          std::string_view authenticated_link_online_id,
                          std::uint32_t authenticated_run=0u) noexcept {
        if(!CanonicalOnlineId(authenticated_link_online_id))
            return Status::MissingLinkIdentity;
        if(!CanonicalOnlineId(f.sender) || f.sender!=authenticated_link_online_id)
            return Status::SpoofedSender;
        // GameLink in original YT initializes a random ODD run instance,
        // never zero. Instance is game-session metadata, not crypto proof.
        if(f.instance==0u || (f.instance&1u)==0u)
            return Status::InvalidRun;
        if(authenticated_run && f.instance!=authenticated_run)
            return Status::StaleRun;
        if(f.entries.size()>MaxEntries)return Status::InvalidEntries;
        for(const auto& entry:f.entries) {
            const auto& p=entry.packet;
            if(p.size()<8u || p.size()>MaxNativeBytes)return Status::InvalidEntries;
            const auto ch=Channel(p), n=Size(p);
            if(n!=p.size()-8u ||
               (ch>=NativeChannelCount &&
                !(ch==NativeChannelCount &&
                  entry.packet_class==BloodborneCoop::PacketClass::Reliable &&
                  p.size()==8u)))
                return Status::InvalidEntries;
        }
        return Status::Accepted;
    }
};
} // namespace SeamlessHunt
