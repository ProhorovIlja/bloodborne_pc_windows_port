// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V415: bounded read-only decoder of original YT protobuf authority fields.
// Never authenticates a UDP sender or accesses a game. Call ONLY after the
// pinned server's Noise-NK and original CoopStream checks.
// The actual generated bbcoop::Envelope is the cross-check in CI.
#include "shyt_yt_team_authority_v414.h"
#include <cstddef>
#include <cstdint>
#include <span>
#include <string>
#include <utility>

namespace SeamlessHunt {
class YtTeamWireLiteV415 final {
public:
    enum class Kind { Invalid, Other, Lobby, Start, Welcome, Snapshot };
    struct Message {
        Kind kind = Kind::Invalid;
        YtTeamAuthorityV414::Lobby lobby{};
        bool lobby_has_team = false; // valid default YT lobby: player has no team
        YtTeamAuthorityV414::Start start{};
        bool accepted = false;
        std::uint64_t epoch = 0, last = 0;
    };
    static constexpr std::size_t MaxEnvelope = 64u * 1024u;

    static Message Decode(std::span<const std::uint8_t> wire) {
        Message result;
        if (wire.empty() || wire.size() > MaxEnvelope) return result;
        Reader reader(wire);
        Field field;
        bool seen = false;
        while (reader.Next(field)) {
            // The original Envelope is a oneof. No ambiguous multiple
            // bodies are accepted, even if protobuf's parser allows them.
            if (seen || field.wire != 2u) return {};
            seen = true;
            switch (field.number) {
            case 2u:
                result.kind = Kind::Welcome;
                if (!ReadWelcome(field.bytes,result)) return {};
                break;
            case 7u:
                result.kind = Kind::Snapshot;
                if (!ReadSnapshotMetadata(field.bytes,result)) return {};
                break;
            case 25u:
                result.kind = Kind::Lobby;
                if (!ReadLobby(field.bytes,result.lobby,result.lobby_has_team)) return {};
                break;
            case 26u:
                result.kind = Kind::Start;
                if (!ReadStart(field.bytes,result.start)) return {};
                break;
            default:
                result.kind = Kind::Other;
                break;
            }
        }
        return seen && reader.Valid() ? result : Message{};
    }

private:
    struct Field {
        std::uint32_t number = 0, wire = 0;
        std::uint64_t number_value = 0;
        std::span<const std::uint8_t> bytes{};
    };
    class Reader {
    public:
        explicit Reader(std::span<const std::uint8_t> bytes):bytes_(bytes){}
        bool Valid() const { return valid_; }
        bool Next(Field& f) {
            if (!valid_ || pos_ == bytes_.size()) return false;
            std::uint64_t tag = 0;
            if (!Varint(tag) || tag >> 3u == 0u ||
                tag >> 3u >= (1ull << 29u)) return Fail();
            f = {};
            f.number = static_cast<std::uint32_t>(tag >> 3u);
            f.wire = static_cast<std::uint32_t>(tag & 7u);
            switch (f.wire) {
            case 0u:
                if (!Varint(f.number_value)) return Fail();
                break;
            case 1u:
                if (bytes_.size()-pos_ < 8u) return Fail();
                pos_ += 8u;
                break;
            case 2u: {
                std::uint64_t n = 0;
                if (!Varint(n) || n > bytes_.size()-pos_) return Fail();
                f.bytes = bytes_.subspan(pos_,static_cast<std::size_t>(n));
                pos_ += static_cast<std::size_t>(n);
                break;
            }
            case 5u:
                if (bytes_.size()-pos_ < 4u) return Fail();
                pos_ += 4u;
                break;
            default:
                return Fail();
            }
            return true;
        }
    private:
        bool Fail() {valid_=false;return false;}
        bool Varint(std::uint64_t& out) {
            out=0;
            for(unsigned i=0;i<10u;++i) {
                if (pos_==bytes_.size()) return false;
                const std::uint8_t byte=bytes_[pos_++];
                if(i==9u && byte>1u) return false;
                out|=static_cast<std::uint64_t>(byte&0x7fu)<<(7u*i);
                if(!(byte&0x80u)) return i==0u || byte!=0u;
            }
            return false;
        }
        std::span<const std::uint8_t> bytes_;
        std::size_t pos_=0;
        bool valid_=true;
    };
    static bool Text(std::string& dst,const Field& f) {
        if(f.wire!=2u || f.bytes.size()>255u)return false;
        if(f.bytes.empty())dst.clear();
        else dst.assign(reinterpret_cast<const char*>(f.bytes.data()),f.bytes.size());
        return true;
    }
    static bool UInt(std::uint32_t& dst,const Field& f) {
        if(f.wire!=0u || f.number_value>UINT32_MAX)return false;
        dst=static_cast<std::uint32_t>(f.number_value);
        return true;
    }
    static bool Bool(bool& dst,const Field& f) {
        if(f.wire!=0u || f.number_value>1u)return false;
        dst=f.number_value==1u;
        return true;
    }
    static bool ReadMember(std::span<const std::uint8_t> bytes,
                           YtTeamAuthorityV414::Member& member) {
        Reader r(bytes);Field f;std::uint32_t seen=0;
        while(r.Next(f)) {
            const std::uint32_t bit=f.number==1u?1u:f.number==4u?2u:
                                    f.number==5u?4u:f.number==7u?8u:0u;
            if(bit && (seen&bit))return false;
            seen|=bit;
            switch(f.number) {
            case 1u:if(!Text(member.id,f))return false;break;
            case 4u:if(!Bool(member.ready,f))return false;break;
            case 5u:if(!UInt(member.slot,f))return false;break;
            case 7u:if(!UInt(member.sign,f))return false;break;
            default:break;
            }
        }
        return r.Valid() && !member.id.empty();
    }
    static bool ReadTeam(std::span<const std::uint8_t> bytes,
                         YtTeamAuthorityV414::Lobby& lobby) {
        Reader r(bytes);Field f;std::uint32_t seen=0;
        while(r.Next(f)) {
            const std::uint32_t bit=f.number==1u?1u:f.number==2u?2u:
                f.number==4u?4u:f.number==6u?8u:f.number==7u?16u:0u;
            if(bit && (seen&bit))return false;
            seen|=bit;
            switch(f.number) {
            case 1u:if(!Text(lobby.team,f))return false;break;
            case 2u:if(!Text(lobby.leader,f))return false;break;
            case 3u:{
                if(f.wire!=2u ||
                   lobby.members.size()>=YtTeamAuthorityV414::MaxTeam)return false;
                YtTeamAuthorityV414::Member member;
                if(!ReadMember(f.bytes,member))return false;
                lobby.members.push_back(std::move(member));
                break;
            }
            case 4u:if(!Bool(lobby.started,f))return false;break;
            case 6u:if(!Text(lobby.world,f))return false;break;
            case 7u:if(!Text(lobby.party,f))return false;break;
            default:break;
            }
        }
        return r.Valid() && !lobby.team.empty();
    }
    static bool ReadLobby(std::span<const std::uint8_t> bytes,
                          YtTeamAuthorityV414::Lobby& lobby,bool& has_team) {
        Reader r(bytes);Field f;bool seen=false;
        while(r.Next(f)) {
            if(f.number==1u) {
                if(seen || f.wire!=2u || !ReadTeam(f.bytes,lobby))return false;
                seen=true;
            }
        }
        has_team=seen;
        // Original LobbyState.team is optional: a signed-in hunter not
        // yet in a team legitimately receives one without this field.
        // That message revokes world access, but MUST NOT be rejected as
        // malformed, or the first lobby response deadlocks the stream.
        return r.Valid();
    }
    static bool ReadStart(std::span<const std::uint8_t> bytes,
                          YtTeamAuthorityV414::Start& start) {
        Reader r(bytes);Field f;std::uint32_t seen=0;
        while(r.Next(f)) {
            const std::uint32_t bit=f.number==1u?1u:f.number==2u?2u:
                f.number==3u?4u:f.number==4u?8u:f.number==5u?16u:0u;
            if(bit && (seen&bit))return false;
            seen|=bit;
            switch(f.number) {
            case 1u:if(!Text(start.team,f))return false;break;
            case 2u:if(!Text(start.party,f))return false;break;
            case 3u:if(!Text(start.host,f))return false;break;
            case 4u:if(!UInt(start.slot,f))return false;break;
            case 5u:if(!Text(start.world,f))return false;break;
            default:break;
            }
        }
        return r.Valid() && (seen&23u)==23u; // proto3 omits slot=0
    }
    // Only the top-level original Snapshot.epoch/last are decoded. The
    // nested kills/flags/map/HpReport payloads remain opaque and quarantined
    // until a separately verified world application consumer exists.
    static bool ReadSnapshotMetadata(std::span<const std::uint8_t> bytes,Message& msg) {
        Reader r(bytes);Field f;std::uint32_t seen=0;
        while(r.Next(f)) {
            if(f.number==1u || f.number==2u) {
                if(f.wire!=0u || (seen & (1u<<(f.number-1u))))return false;
                seen |= 1u<<(f.number-1u);
                if(f.number==1u)msg.epoch=f.number_value;
                else msg.last=f.number_value;
            }
        }
        // Proto3 serializes last=0 by omission. A valid world epoch cannot
        // be zero for this read-only admission gate.
        return r.Valid() && (seen&1u)!=0u && msg.epoch!=0u;
    }
    static bool ReadWelcome(std::span<const std::uint8_t> bytes,Message& msg) {
        Reader r(bytes);Field f;std::uint32_t seen=0;
        while(r.Next(f)) {
            const std::uint32_t bit=f.number==1u?1u:
                f.number==3u?2u:f.number==4u?4u:0u;
            if(bit && (seen&bit))return false;
            seen|=bit;
            switch(f.number) {
            case 1u:if(!Bool(msg.accepted,f))return false;break;
            case 3u:if(f.wire!=0u)return false;
                    msg.epoch=f.number_value;break;
            case 4u:if(f.wire!=0u)return false;
                    msg.last=f.number_value;break;
            default:break;
            }
        }
        return r.Valid() && (seen&1u)!=0u;
    }
};
} // namespace SeamlessHunt
