// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V264: physical shadPS4/YT UDP demux. The server-only original SHAD
// transport stays untouched. Only a previously server-approved endpoint
// may send the independent authenticated SHDP movement wire format.
//
// This is deliberately only a TRANSPORT gate. Cryptographic verification,
// replay defense and server party/epoch checks happen in V262 BEFORE
// GameLinkPeer::Receive. Never treat an address or this header as identity.
#include <array>
#include <cstddef>
#include <cstdint>
#include <span>
#include <utility>

namespace BloodborneCoop::SHYTHybrid {

struct DirectPhysicalEndpointV264 {
    std::uint32_t addr_nbo=0;
    std::uint16_t port_nbo=0;
    std::int64_t valid_until_ms=0;
};

class DirectPhysicalGateV264 {
public:
    static constexpr std::size_t MaxPeerEndpoints=4; // five-person party
    static constexpr std::size_t MaxWire=1200;
    static constexpr std::size_t MaxQueued=128;
    static constexpr std::array<std::uint8_t,9> WireHeader{
        0xff,0xff,0xff,0xff,'S','H','D','P',1
    };

    static bool CorrectWire(std::span<const std::uint8_t> packet) {
        // Nine-byte unauthenticated outer header, encrypted body and
        // original LinkAuth::Session 24-byte counter+tag minimum.
        if (packet.size()<WireHeader.size()+32+24+1 ||
            packet.size()>MaxWire) return false;
        for(std::size_t i=0;i<WireHeader.size();++i)
            if(packet[i]!=WireHeader[i]) return false;
        return true;
    }

    // Only call from the real authenticated server-grant/Noise lifecycle,
    // on the owning transport thread or while holding its gate mutex.
    // Caller must independently validate party, map, epoch and the
    // verified Noise session. A "true" opt-in is NOT authorization.
    bool InstallAuthenticatedEndpoint(DirectPhysicalEndpointV264 endpoint,
                                      std::int64_t now_ms) {
        if (!endpoint.addr_nbo || !endpoint.port_nbo ||
            now_ms<0 || endpoint.valid_until_ms<=now_ms)
            return false;
        // First update the existing exact endpoint. Otherwise an earlier
        // expired slot could create a duplicate route and waste one of
        // the four places available in a five-player session.
        for (auto& item : endpoints_) {
            if (item.addr_nbo==endpoint.addr_nbo &&
                item.port_nbo==endpoint.port_nbo) {
                item=endpoint;
                return true;
            }
        }
        for (auto& item : endpoints_) {
            if (item.addr_nbo==0 || item.valid_until_ms<=now_ms) {
                item=endpoint;
                return true;
            }
        }
        return false; // never silently evict another live hunter
    }

    bool Allows(DirectPhysicalEndpointV264 source,
                std::int64_t now_ms,
                std::span<const std::uint8_t> encrypted) const {
        if (now_ms<0 || !CorrectWire(encrypted) ||
            !source.addr_nbo || !source.port_nbo)
            return false;
        for(const auto& item:endpoints_)
            if(item.addr_nbo==source.addr_nbo &&
               item.port_nbo==source.port_nbo &&
               item.valid_until_ms>now_ms)
                return true;
        return false;
    }

    void Revoke(DirectPhysicalEndpointV264 source) {
        for(auto& item:endpoints_)
            if(item.addr_nbo==source.addr_nbo &&
               item.port_nbo==source.port_nbo)
                item={};
    }
    void RevokeAll() { endpoints_.fill({}); }
private:
    std::array<DirectPhysicalEndpointV264,MaxPeerEndpoints> endpoints_{};
};
} // namespace BloodborneCoop::SHYTHybrid
