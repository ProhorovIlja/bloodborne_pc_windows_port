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
    // V421: strict bounded structural audit of the COMPLETE original
    // v1.4.0 Snapshot protobuf, not just epoch/last. Validate known fields,
    // nested scalar wire types, packed/unpacked MapKills handles, duplicate
    // singular fields and a shared item budget. The world remains read-only
    // and quarantined; this is NOT a game state decoder or an auth grant.
    static constexpr std::uint32_t MaxWorldItemsV421=8192u;
    static constexpr std::size_t MaxMapStateBytesV421=16384u;
    static bool PackedWorldHandlesV421(std::span<const std::uint8_t> bytes,
                                      std::uint32_t& items) {
        std::size_t pos=0;
        while(pos<bytes.size()) {
            if(items>=MaxWorldItemsV421)return false;
            std::uint32_t value=0;
            bool ended=false;
            for(unsigned i=0u;i<5u && pos<bytes.size();++i) {
                const std::uint8_t b=bytes[pos++];
                if(i==4u && b>0x0fu)return false;
                value|=static_cast<std::uint32_t>(b&0x7fu)<<(7u*i);
                if(!(b&0x80u)) {
                    // Reject noncanonical varints and redundant zeros.
                    if(i!=0u && b==0u)return false;
                    ended=true;
                    break;
                }
            }
            if(!ended)return false;
            ++items;
            (void)value;
        }
        return true;
    }
    // kind: 1 MapKills, 2 ShownCharacter, 3 HpReport, 4 HpEnemy,
    // 5 Entry. Nested recursion is fixed at depth <=2.
    static bool WorldRecordV421(std::span<const std::uint8_t> bytes,
                                unsigned kind,std::uint32_t& items,
                                std::uint64_t last) {
        if(items>=MaxWorldItemsV421)return false;
        ++items;
        Reader r(bytes);Field f;std::uint32_t seen=0u;
        bool has_seq=false;
        std::uint64_t seq=0u;
        while(r.Next(f)) {
            const unsigned max=kind==1u?2u:kind==2u?2u:
                               kind==3u?3u:kind==4u?3u:5u;
            if(f.number==0u || f.number>max)return false;
            const bool repeated=(kind==1u && f.number==2u) ||
                                (kind==3u && f.number==3u);
            const std::uint32_t bit=1u<<f.number;
            if(!repeated && (seen&bit))return false;
            seen|=bit;
            if(kind==1u && f.number==2u) {
                if(f.wire==2u) {
                    if(!PackedWorldHandlesV421(f.bytes,items))return false;
                } else if(f.wire==0u && f.number_value<=UINT32_MAX) {
                    if(items>=MaxWorldItemsV421)return false;
                    ++items;
                } else return false;
            } else if(kind==3u && f.number==3u) {
                if(f.wire!=2u || !WorldRecordV421(f.bytes,4u,items,last))
                    return false;
            } else if(f.wire!=0u)return false;
            else if(kind==3u && f.number==1u) {
                // uint64 source: all wire-0 values permitted.
            } else if(kind==5u && f.number==1u) {
                has_seq=true;
                seq=f.number_value;
            } else if(f.number_value>UINT32_MAX) {
                // uint32 and sint32 (zigzag) fields cannot exceed 32 bits.
                return false;
            }
        }
        return r.Valid() && (kind!=5u || (has_seq && seq>0u && (last==UINT64_MAX || seq<=last)));
    }
    static bool ReadSnapshotMetadata(std::span<const std::uint8_t> bytes,
                                     Message& msg) {
        // Protobuf wire fields can legally arrive out of field-number order.
        // Resolve and check epoch/last in a bounded first pass so a later
        // recent_flags Entry never compares to an uninitialized last=0.
        Reader header(bytes);Field h;std::uint32_t header_seen=0u;
        while(header.Next(h)) {
            if(h.number==1u || h.number==2u) {
                const std::uint32_t bit=1u<<h.number;
                if(h.wire!=0u || (header_seen&bit))return false;
                header_seen|=bit;
                if(h.number==1u)msg.epoch=h.number_value;
                else msg.last=h.number_value;
            }
        }
        if(!header.Valid() || !(header_seen&(1u<<1u)) ||
           msg.epoch==0u)return false;
        Reader r(bytes);Field f;std::uint32_t seen=0u,items=0u;
        while(r.Next(f)) {
            if(f.number==0u || f.number>12u)return false;
            const bool repeated=f.number==3u || f.number==5u ||
                                f.number==10u || f.number==11u;
            const std::uint32_t bit=1u<<f.number;
            if(!repeated && (seen&bit))return false;
            seen|=bit;
            if(repeated) {
                const unsigned kind=f.number==3u?1u:f.number==5u?2u:
                                    f.number==10u?3u:5u;
                if(f.wire!=2u ||
                   !WorldRecordV421(f.bytes,kind,items,msg.last))
                    return false;
                continue;
            }
            if(f.number==7u) {
                if(f.wire!=2u || f.bytes.size()>MaxMapStateBytesV421)
                    return false;
                continue;
            }
            if(f.wire!=0u)return false;
            switch(f.number) {
            case 1u:msg.epoch=f.number_value;break;
            case 2u:msg.last=f.number_value;break;
            case 12u:
                if(f.number_value>1u)return false;
                break;
            default:
                if(f.number_value>UINT32_MAX)return false;
                break;
            }
        }
        // Epoch is mandatory, last=0 is a legitimate proto3 default.
        // An empty snapshot after reset is valid; its opaque payload still
        // cannot be applied to the owner's game.
        return r.Valid() && (seen&(1u<<1u))!=0u && msg.epoch!=0u;
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
