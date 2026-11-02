// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V286: the missing wire bridge between V241's ORIGINAL YT encrypted
// GameFrame datagram and V264/V265's distinct physical UDP SHDP channel.
// Outer SHDP header is NOT authenticated by itself; V262 MUST still
// verify Noise AEAD, exact sender/epoch/lease and replay before delivery.
#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <vector>
namespace BloodborneCoop::SHYTHybrid {
struct ShdpWireV286 {
    static constexpr std::array<std::uint8_t,9> Header{
        0xff,0xff,0xff,0xff,'S','H','D','P',1
    };
    static constexpr std::size_t MaxPhysicalBytes=1200;
    // Full AEAD payload cannot be zero length and includes a counter,
    // an authentication tag, and an encrypted original GameFrame body.
    static constexpr std::size_t MinEncryptedBytes=32+24+1;
    static constexpr std::size_t MaxEncryptedBytes=MaxPhysicalBytes-Header.size();
    static constexpr bool StartsWithPeerFamily(std::span<const std::uint8_t> bytes) {
        if(bytes.size()<Header.size()-1) return false;
        for(size_t i=0;i<Header.size()-1;++i)
            if(bytes[i]!=Header[i])return false;
        return true;
    }
    static std::optional<std::vector<std::uint8_t>> Wrap(
        std::span<const std::uint8_t> encrypted) {
        if(encrypted.size()<MinEncryptedBytes ||
           encrypted.size()>MaxEncryptedBytes) return std::nullopt;
        std::vector<std::uint8_t> result;
        result.reserve(Header.size()+encrypted.size());
        result.insert(result.end(),Header.begin(),Header.end());
        result.insert(result.end(),encrypted.begin(),encrypted.end());
        return result;
    }
    static std::optional<std::span<const std::uint8_t>> OpenEnvelope(
        std::span<const std::uint8_t> physical) {
        if(!StartsWithPeerFamily(physical) ||
           physical.size()<Header.size()+MinEncryptedBytes ||
           physical.size()>MaxPhysicalBytes ||
           physical[Header.size()-1]!=1)
            return std::nullopt;
        return physical.subspan(Header.size());
    }
};
} // namespace BloodborneCoop::SHYTHybrid
