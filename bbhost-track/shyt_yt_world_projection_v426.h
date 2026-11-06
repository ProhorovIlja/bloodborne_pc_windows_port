// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V426: typed, bounded, READ-ONLY reconstruction of the original YT
// v1.4.0 world log from V425's authenticated immutable staging.
// This model owns NO game hooks. It NEVER mutates a guest, save, reward,
// world event flag, remote actor, HP bar or NetSync authority.
// Semantics checked against original server/coop/world_log.cpp/h.
#include "shyt_yt_world_staging_v425.h"
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <map>
#include <set>
#include <span>
#include <utility>
#include <vector>

namespace SeamlessHunt {
class YtWorldProjectionV426 final {
public:
    struct Entry {
        std::uint64_t seq=0;
        std::uint32_t map=0,kind=0,subject=0,value=0;
    };
    struct EnemyHp {
        std::int32_t value=0,max=0;
    };
    struct HpReport {
        std::uint32_t map=0;
        std::map<std::uint32_t,EnemyHp> enemies;
    };
    struct State {
        std::uint64_t epoch=0,applied=0,game_applied=0;
        std::map<std::uint32_t,std::set<std::uint32_t>> kills;
        std::uint32_t shown_map=0;
        std::map<std::uint32_t,std::uint32_t> shown;
        std::uint32_t map_state_map=0;
        std::vector<std::uint8_t> map_state_bits;
        std::int32_t return_point=0;
        std::uint32_t return_point_map=0;
        std::map<std::uint64_t,HpReport> hp;
        std::uint64_t current_hp_source=0;
        std::vector<Entry> snapshot_recent_flags;
        std::uint64_t live_flags_seen=0;
        std::uint64_t unknown_kinds=0;
        bool after_wipe=false;
        std::size_t CountKilled() const noexcept {
            std::size_t total=0;
            for(const auto& [map,ids]:kills) {
                (void)map;
                total+=ids.size();
            }
            return total;
        }
        std::size_t CountHpEnemies() const noexcept {
            std::size_t total=0;
            for(const auto& [src,report]:hp) {
                (void)src;
                total+=report.enemies.size();
            }
            return total;
        }
    };
    bool Rebuild(const YtWorldStagingV425& stage) {
        // Atomic preparation: if ANY record fails, publish nothing.
        ready_=false;
        state_={};
        if(!stage.Active() || !stage.PendingPackets() ||
           stage.PendingPackets()>YtWorldStagingV425::MaxDeltaBatches+1u ||
           stage.StagedBytes()>YtWorldStagingV425::MaxStagedBytes)return false;
        const auto* first=stage.Peek(0u);
        if(!first || first->kind!=YtWorldStagingV425::Kind::Snapshot)return false;
        State candidate{};
        if(!Snapshot(*first,candidate))return false;
        for(std::size_t i=1u;i<stage.PendingPackets();++i) {
            const auto* batch=stage.Peek(i);
            if(!batch || !Batch(*batch,candidate))return false;
        }
        if(candidate.epoch!=stage.Epoch() ||
           candidate.applied!=stage.StagedCursor())return false;
        state_=std::move(candidate);
        ready_=true;
        return true;
    }
    bool Ready() const noexcept {return ready_;}
    // This is a diagnostic read-only projection, NOT guest game state.
    const State& View() const noexcept {return state_;}
    void Reset() noexcept {ready_=false;state_={};}
private:
    struct Field {
        std::uint32_t number=0,wire=0;
        std::uint64_t value=0;
        std::span<const std::uint8_t> bytes{};
    };
    class Reader {
    public:
        explicit Reader(std::span<const std::uint8_t> bytes):bytes_(bytes){}
        bool Valid() const noexcept{return good_;}
        bool Next(Field& f) {
            if(!good_ || pos_==bytes_.size())return false;
            std::uint64_t tag=0;
            if(!Varint(tag) || (tag>>3u)==0u ||
               (tag>>3u)>=(1ull<<29u))return Fail();
            f={};
            f.number=static_cast<std::uint32_t>(tag>>3u);
            f.wire=static_cast<std::uint32_t>(tag&7u);
            if(f.wire==0u)return Varint(f.value)||Fail();
            if(f.wire==2u) {
                std::uint64_t length=0;
                if(!Varint(length) || length>bytes_.size()-pos_)return Fail();
                f.bytes=bytes_.subspan(pos_,static_cast<std::size_t>(length));
                pos_+=static_cast<std::size_t>(length);
                return true;
            }
            return Fail(); // these world fields have no fixed32/64 types
        }
        bool Varint(std::uint64_t& n) {
            n=0;
            for(unsigned i=0u;i<10u;++i) {
                if(pos_==bytes_.size())return Fail();
                const auto ch=bytes_[pos_++];
                if(i==9u && ch>1u)return Fail();
                n|=static_cast<std::uint64_t>(ch&127u)<<(7u*i);
                if(!(ch&128u))return i==0u || ch!=0u || Fail();
            }
            return Fail();
        }
        bool Done() const noexcept{return good_ && pos_==bytes_.size();}
    private:
        bool Fail() noexcept {good_=false;return false;}
        std::span<const std::uint8_t> bytes_;
        std::size_t pos_=0;
        bool good_=true;
    };
    static bool U32(const Field& f,std::uint32_t& value) {
        if(f.wire!=0u || f.value>UINT32_MAX)return false;
        value=static_cast<std::uint32_t>(f.value);
        return true;
    }
    static std::int32_t ZigZag(std::uint32_t n) {
        return static_cast<std::int32_t>((n>>1u) ^ (0u-(n&1u)));
    }
    static bool Payload(std::span<const std::uint8_t> wire,
                        unsigned number,std::span<const std::uint8_t>& out) {
        Reader r(wire);Field f;
        if(!r.Next(f) || f.number!=number || f.wire!=2u)return false;
        out=f.bytes;
        return r.Done();
    }
    static bool EntryData(std::span<const std::uint8_t> bytes,Entry& out) {
        Reader r(bytes);Field f;std::uint32_t seen=0u;
        while(r.Next(f)) {
            if(f.number==0u || f.number>5u ||
               (seen & (1u<<f.number)))return false;
            seen|=1u<<f.number;
            if(f.number==1u) {
                if(f.wire!=0u)return false;
                out.seq=f.value;
            } else {
                std::uint32_t value=0;
                if(!U32(f,value))return false;
                if(f.number==2u)out.map=value;
                else if(f.number==3u)out.kind=value;
                else if(f.number==4u)out.subject=value;
                else out.value=value;
            }
        }
        return r.Done() && (seen&2u)!=0u && out.seq!=0u;
    }
    static bool Handles(std::span<const std::uint8_t> bytes,
                        std::set<std::uint32_t>& dst) {
        Reader r(bytes);
        while(!r.Done()) {
            std::uint64_t value=0;
            if(!r.Varint(value) || value>UINT32_MAX)return false;
            dst.insert(static_cast<std::uint32_t>(value));
        }
        return r.Valid();
    }
    static bool MapKills(std::span<const std::uint8_t> bytes,State& s) {
        Reader r(bytes);Field f;std::uint32_t map=0,seen=0;
        std::set<std::uint32_t> handles;
        while(r.Next(f)) {
            if(f.number==1u) {
                if((seen&1u) || !U32(f,map))return false;
                seen|=1u;
            } else if(f.number==2u) {
                if(f.wire==2u) {
                    if(!Handles(f.bytes,handles))return false;
                } else {
                    std::uint32_t id=0;
                    if(!U32(f,id))return false;
                    handles.insert(id);
                }
            } else return false;
        }
        if(!r.Done())return false;
        auto& ids=s.kills[map];
        ids.insert(handles.begin(),handles.end());
        return true;
    }
    static bool Shown(std::span<const std::uint8_t> bytes,State& s) {
        Reader r(bytes);Field f;std::uint32_t handle=0,bits=0,seen=0;
        while(r.Next(f)) {
            if(f.number==0u || f.number>2u ||
               (seen & (1u<<f.number)))return false;
            seen|=1u<<f.number;
            if(f.number==1u){if(!U32(f,handle))return false;}
            else if(!U32(f,bits))return false;
        }
        if(!r.Done())return false;
        s.shown[handle]=bits;
        return true;
    }
    static bool HpEnemyData(std::span<const std::uint8_t> bytes,
                            std::uint32_t& handle,EnemyHp& value) {
        Reader r(bytes);Field f;std::uint32_t seen=0;
        while(r.Next(f)) {
            if(f.number==0u || f.number>3u ||
               (seen&(1u<<f.number)))return false;
            seen|=1u<<f.number;
            std::uint32_t v=0;
            if(!U32(f,v))return false;
            if(f.number==1u)handle=v;
            else if(f.number==2u)value.value=ZigZag(v);
            else value.max=ZigZag(v);
        }
        return r.Done();
    }
    static bool HpData(std::span<const std::uint8_t> bytes,State& s) {
        Reader r(bytes);Field f;std::uint32_t map=0,seen=0;
        std::uint64_t source=0;
        HpReport report{};
        while(r.Next(f)) {
            if(f.number==1u) {
                if((seen&1u) || f.wire!=0u)return false;
                seen|=1u;
                source=f.value;
            } else if(f.number==2u) {
                if((seen&2u) || !U32(f,map))return false;
                seen|=2u;
            } else if(f.number==3u && f.wire==2u) {
                EnemyHp hp{};
                std::uint32_t handle=0;
                if(!HpEnemyData(f.bytes,handle,hp))return false;
                report.enemies[handle]=hp;
            } else return false;
        }
        if(!r.Done())return false;
        report.map=map;
        s.hp[source]=std::move(report);
        return true;
    }
    static bool Snapshot(const YtWorldStagingV425::Record& record,State& s) {
        const auto meta=YtTeamWireLiteV415::Decode(record.wire);
        if(meta.kind!=YtTeamWireLiteV415::Kind::Snapshot ||
           meta.epoch!=record.epoch || meta.last!=record.last)return false;
        std::span<const std::uint8_t> body;
        if(!Payload(record.wire,7u,body))return false;
        Reader r(body);Field f;
        s.epoch=meta.epoch;s.applied=meta.last;
        while(r.Next(f)) {
            switch(f.number) {
            case 1u:case 2u:
                if(f.wire!=0u)return false;
                break;
            case 3u:
                if(f.wire!=2u || !MapKills(f.bytes,s))return false;
                break;
            case 4u:
                if(!U32(f,s.shown_map))return false;
                break;
            case 5u:
                if(f.wire!=2u || !Shown(f.bytes,s))return false;
                break;
            case 6u:
                if(!U32(f,s.map_state_map))return false;
                break;
            case 7u:
                if(f.wire!=2u)return false;
                s.map_state_bits.assign(f.bytes.begin(),f.bytes.end());
                break;
            case 8u: {
                std::uint32_t packed=0;
                if(!U32(f,packed))return false;
                s.return_point=ZigZag(packed);
                break;
            }
            case 9u:
                if(!U32(f,s.return_point_map))return false;
                break;
            case 10u:
                if(f.wire!=2u || !HpData(f.bytes,s))return false;
                break;
            case 11u: {
                Entry entry{};
                if(f.wire!=2u || !EntryData(f.bytes,entry) ||
                   entry.seq>s.applied)return false;
                s.snapshot_recent_flags.push_back(entry);
                break;
            }
            case 12u:
                if(f.wire!=0u || f.value>1u)return false;
                s.after_wipe=f.value!=0u;
                break;
            default:return false;
            }
        }
        return r.Done();
    }
    static void Apply(const Entry& e,State& s) {
        // Original WorldLogBatch normalizes Shown wire kind 0x10-0x1f
        // (low four bits repeat ShownBits) to WorldLogKind::Shown. Keep
        // exactly the original entry.value as the full shown bitset.
        if((e.kind & ~std::uint32_t{0x0fu})==0x10u) {
            if(e.map==s.shown_map)s.shown[e.subject]=e.value;
            return;
        }
        switch(e.kind) {
        case 0u: // Reset: match WorldLogMember::Apply
            if(!e.map)s.kills.clear();
            else s.kills.erase(e.map);
            if(!e.map || e.map==s.shown_map){s.shown_map=0;s.shown.clear();}
            if(!e.map || e.map==s.map_state_map) {
                s.map_state_map=0;s.map_state_bits.clear();
            }
            if(!e.map)s.hp.clear();
            break;
        case 1u:s.kills[e.map].insert(e.subject);break; // Kill
        case 2u: { // Unkill
            auto it=s.kills.find(e.map);
            if(it!=s.kills.end()) {
                it->second.erase(e.subject);
                if(it->second.empty())s.kills.erase(it);
            }
            break;
        }
        case 3u:s.shown_map=e.map;s.shown.clear();break;
        case 4u:if(e.map==s.shown_map)s.shown.erase(e.subject);break;
        case 5u:case 6u:++s.live_flags_seen;break;
        case 7u:
            s.map_state_map=e.map;
            s.map_state_bits.assign(1250u,0u); // YT MapFlagCount=10000
            break;
        case 8u:case 9u:
            if(e.map==s.map_state_map && e.subject<10000u &&
               s.map_state_bits.size()>=1250u) {
                auto& byte=s.map_state_bits[e.subject/8u];
                const auto mask=static_cast<std::uint8_t>(0x80u>>(e.subject%8u));
                if(e.kind==8u)byte=static_cast<std::uint8_t>(byte|mask);
                else byte=static_cast<std::uint8_t>(byte&static_cast<std::uint8_t>(~mask));
            }
            break;
        case 10u:
            s.current_hp_source=(static_cast<std::uint64_t>(e.subject)<<32u)|e.value;
            s.hp[s.current_hp_source].map=e.map;
            break;
        case 11u:
            s.hp[s.current_hp_source].enemies[e.subject]={
                static_cast<std::int32_t>(e.value),
                static_cast<std::int32_t>(e.map)};
            break;
        case 12u: {
            auto it=s.hp.find(s.current_hp_source);
            if(it!=s.hp.end()) {
                it->second.enemies.erase(e.subject);
                if(it->second.enemies.empty())s.hp.erase(it);
            }
            break;
        }
        case 13u:
            s.hp.erase((static_cast<std::uint64_t>(e.subject)<<32u)|e.value);
            break;
        case 14u:
            s.return_point=static_cast<std::int32_t>(e.subject);
            s.return_point_map=e.map;
            break;
        default:++s.unknown_kinds;break; // original skips unknown kind
        }
    }
    static bool Batch(const YtWorldStagingV425::Record& batch,State& s) {
        const auto meta=YtTeamWireLiteV415::Decode(batch.wire);
        if(meta.kind!=YtTeamWireLiteV415::Kind::Entries ||
           meta.epoch!=s.epoch || meta.last!=batch.last ||
           meta.first_entry_seq!=batch.first ||
           meta.last_entry_seq!=batch.tail ||
           meta.entry_count!=batch.count ||
           batch.skip_through!=s.applied)return false;
        std::span<const std::uint8_t> body;
        if(!Payload(batch.wire,5u,body))return false;
        Reader r(body);Field f;
        std::vector<Entry> changes;
        changes.reserve(batch.count);
        while(r.Next(f)) {
            if(f.number==1u || f.number==2u) {
                if(f.wire!=0u)return false;
            } else if(f.number==3u && f.wire==2u) {
                Entry entry{};
                if(!EntryData(f.bytes,entry))return false;
                if(entry.seq>batch.skip_through)changes.push_back(entry);
            } else return false;
        }
        if(!r.Done() || changes.empty() ||
           changes.back().seq!=batch.tail)return false;
        // Two-phase application: decode and validate full batch BEFORE
        // mutating any projection state. All Apply cases are infallible.
        for(const auto& entry:changes) {
            if(s.applied==UINT64_MAX || entry.seq!=s.applied+1u)return false;
            Apply(entry,s);
            s.applied=entry.seq;
        }
        return true;
    }
    State state_{};
    bool ready_=false;
};
} // namespace SeamlessHunt
