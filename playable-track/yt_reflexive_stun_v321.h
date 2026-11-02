// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V321: RFC 8489-compatible IPv4 STUN discovery from the SAME original
// YT game UDP socket. Standard public STUN responses are NOT authenticated
// peer identity, reachability proof, consent, or game transport permission.
// Never install a physical SHDP endpoint from a STUN response alone.
// Reuses the parsing ideas of bbhost/src/net/stun.cpp (MIT-licensed logic
// reimplemented here independently), but excludes bbhost-specific relay.
// See RFC 8489 sections 5 and 14, RFC 8445 section 7.2.5.3.
#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <optional>
#include <span>

namespace BloodborneCoop::SHYTHybrid::ReflexiveStunV321 {
using u8=std::uint8_t;
using s64=std::int64_t;
struct Endpoint {
    std::uint32_t address_nbo=0;
    std::uint16_t port_nbo=0;
    friend bool operator==(const Endpoint&,const Endpoint&)=default;
};
class Binding {
public:
    static constexpr std::size_t RequestBytes=20;
    static constexpr std::size_t MaxResponseBytes=512;
    static constexpr s64 TimeoutMs=2500;
    static constexpr std::array<u8,4> Cookie{0x21,0x12,0xa4,0x42};

    // The 12-byte transaction ID is supplied by a platform OS CSPRNG.
    // Never use a predictable source, a server packet or a static ID.
    std::optional<std::array<u8,RequestBytes>> Start(
        Endpoint server,std::span<const u8,12> secret_txid,s64 now)
    {
        if(active_ || !server.address_nbo || !server.port_nbo ||
           now<0 || now>INT64_MAX-TimeoutMs ||
           std::all_of(secret_txid.begin(),secret_txid.end(),
                       [](u8 b){return b==0;}))
            return std::nullopt;
        server_=server;
        expires_=now+TimeoutMs;
        std::copy(secret_txid.begin(),secret_txid.end(),txid_.begin());
        active_=true;
        std::array<u8,RequestBytes> request{};
        request[1]=1; // STUN Binding request, no attributes
        std::copy(Cookie.begin(),Cookie.end(),request.begin()+4);
        std::copy(txid_.begin(),txid_.end(),request.begin()+8);
        return request;
    }

    // The mapped endpoint is merely an advisory candidate. A separate
    // authenticated Noise connectivity check and signed server team grant
    // are REQUIRED before any direct GameFrame send/receive.
    std::optional<Endpoint> Take(
        Endpoint source,std::span<const u8> bytes,s64 now)
    {
        if(!active_ || now<0 || now>expires_ ||
           source!=server_ || bytes.size()<RequestBytes ||
           bytes.size()>MaxResponseBytes ||
           bytes[0]!=0x01 || bytes[1]!=0x01 ||
           !std::equal(Cookie.begin(),Cookie.end(),bytes.begin()+4) ||
           !std::equal(txid_.begin(),txid_.end(),bytes.begin()+8))
            return std::nullopt;
        const auto be16=[&](std::size_t pos)->std::uint16_t {
            return static_cast<std::uint16_t>(
                (static_cast<unsigned>(bytes[pos])<<8)|bytes[pos+1]);
        };
        const std::size_t payload_length=be16(2);
        if((payload_length&3)!=0 ||
           payload_length!=bytes.size()-RequestBytes)
            return std::nullopt;
        std::optional<Endpoint> chosen;
        for(std::size_t at=RequestBytes;at<bytes.size();) {
            if(bytes.size()-at<4)return std::nullopt;
            const auto type=be16(at),n=be16(at+2);
            at+=4;
            if(n>bytes.size()-at)return std::nullopt;
            if(type==0x0020) { // XOR-MAPPED-ADDRESS, RFC 8489
                if(chosen || n!=8 || bytes[at]!=0 || bytes[at+1]!=1)
                    return std::nullopt;
                const std::array<u8,4> ip{
                    static_cast<u8>(bytes[at+4]^Cookie[0]),
                    static_cast<u8>(bytes[at+5]^Cookie[1]),
                    static_cast<u8>(bytes[at+6]^Cookie[2]),
                    static_cast<u8>(bytes[at+7]^Cookie[3])};
                const std::array<u8,2> port{
                    static_cast<u8>(bytes[at+2]^Cookie[0]),
                    static_cast<u8>(bytes[at+3]^Cookie[1])};
                Endpoint mapped{};
                std::memcpy(&mapped.address_nbo,ip.data(),4);
                std::memcpy(&mapped.port_nbo,port.data(),2);
                if(!mapped.address_nbo || !mapped.port_nbo)
                    return std::nullopt;
                chosen=mapped;
            }
            const std::size_t padded=(static_cast<std::size_t>(n)+3)&~std::size_t{3};
            if(padded>bytes.size()-at)return std::nullopt;
            at+=padded;
        }
        if(chosen) {
            active_=false; // transaction is single-use; replay denied
            return chosen;
        }
        return std::nullopt;
    }

    void Revoke() {
        active_=false;
        txid_.fill(0);
        server_={};
        expires_=0;
    }
    [[nodiscard]] bool Pending(s64 now) const {
        return active_ && now>=0 && now<=expires_;
    }
private:
    Endpoint server_{};
    std::array<u8,12> txid_{};
    s64 expires_=0;
    bool active_=false;
};
} // namespace BloodborneCoop::SHYTHybrid::ReflexiveStunV321
