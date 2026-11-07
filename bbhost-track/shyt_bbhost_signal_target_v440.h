// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
// V440: strictly bounded recipient and wire-shape gate for BBHost PR217
// kSignalMagic UDP signaling. This does NOT authenticate "from", the
// source IP/port, room membership, or who may establish a game transport.
// Sender is controlled text. Only separately authenticated peer metadata
// plus a server-approved route can establish P2P authority.
// Pinned original PR217 src/hle/np_signaling.cpp Git blob
// 4668783f279c9e6c65e48b3c31c956c29056bf61; net_p2p.h
// ed846bfc67919a7d492c98b9b5d866e56b35916b.
#include <cstddef>
#include <cstdint>
#include <span>
#include <string_view>

namespace SeamlessHunt {
struct BbhostSignalTargetV440 final {
    static constexpr std::size_t MagicLen=4u;
    static constexpr std::size_t IdLen=16u;
    static constexpr std::size_t FromAt=6u, ToAt=22u;
    static constexpr std::size_t NonceAt=38u, WireLen=46u;
    static constexpr std::uint8_t Magic[4]={0xfe,'b','b','s'};
    enum class Reason : std::uint8_t {
        Accepted, Malformed, WrongRecipient, EmptyIdentity, NotPeerProof
    };
    static bool ValidName(std::string_view s) noexcept {
        if(s.size()<3u || s.size()>IdLen)return false;
        for(const unsigned char ch:s)
            if(!((ch>='0'&&ch<='9') || (ch>='A'&&ch<='Z') ||
                 (ch>='a'&&ch<='z') || ch=='-' || ch=='_'))return false;
        return true;
    }
    static bool DecodePaddedId(std::span<const std::uint8_t> b,
                               std::string_view* out) noexcept {
        if(b.size()!=IdLen || !out)return false;
        std::size_t end=0;
        while(end<b.size() && b[end]!=0u)++end;
        // Reject non-zero garbage after an early NUL: the peer identity
        // parser in upstream otherwise discards those bytes silently.
        for(std::size_t i=end;i<b.size();++i)if(b[i]!=0u)return false;
        *out=std::string_view(reinterpret_cast<const char*>(b.data()),end);
        return ValidName(*out);
    }
    static bool KnownKind(std::uint8_t kind) noexcept {
        return kind==1u || kind==2u || kind==3u || kind==4u ||
               (kind>=0x11u && kind<=0x14u);
    }
    static Reason Inspect(std::span<const std::uint8_t> b,
                          std::string_view local) noexcept {
        if(!ValidName(local))return Reason::EmptyIdentity;
        if(b.size()!=WireLen)return Reason::Malformed;
        for(std::size_t i=0;i<MagicLen;++i)
            if(b[i]!=Magic[i])return Reason::Malformed;
        if(!KnownKind(b[4]))return Reason::Malformed;
        std::string_view from,to;
        if(!DecodePaddedId(b.subspan(FromAt,IdLen),&from) ||
           !DecodePaddedId(b.subspan(ToAt,IdLen),&to) ||
           from==to)return Reason::Malformed;
        if(to!=local)return Reason::WrongRecipient;
        // "Accepted" only means recipient + wire shape match. It is NOT
        // a validated source, a room grant, or proof of P2P ownership.
        return Reason::Accepted;
    }
};
} // namespace SeamlessHunt
