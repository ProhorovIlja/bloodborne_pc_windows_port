// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V425: bounded immutable staging of original server-authenticated YT
// v1.4.0 Snapshot + consecutive Entries. This is NOT a game world
// consumer; never applies flags, HP, kills, saves, actors or NetSync.
// Caller must FIRST verify Noise-NK MAC, original CoopStream, explicit
// V419 party Welcome, V420 request and V423 epoch/cursor admission.
#include "shyt_yt_team_wire_lite_v415.h"
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <span>
#include <vector>

namespace SeamlessHunt {
class YtWorldStagingV425 final {
public:
    using Kind=YtTeamWireLiteV415::Kind;
    struct Record {
        Kind kind=Kind::Invalid;
        std::uint64_t epoch=0,last=0,first=0,tail=0,skip_through=0;
        std::uint32_t count=0;
        std::vector<std::uint8_t> wire;
    };
    struct Counters {
        std::uint64_t snapshots=0,delta_batches=0;
        std::uint64_t rejected=0,revoked=0;
    };
    static constexpr std::size_t MaxStagedBytes=128u*1024u;
    static constexpr std::size_t MaxDeltaBatches=32u;
    static constexpr std::size_t MaxEnvelopeBytes=64u*1024u;

    // The COMPLETE original protobuf is validated again before a copy.
    // No partial write on a rejected record. Only ONE initial snapshot
    // per authenticated link; a restart must create a fresh session.
    bool StageSnapshot(std::span<const std::uint8_t> wire,
                       std::uint64_t epoch,std::uint64_t last) {
        if(active_ || ever_active_ || !epoch || wire.empty() ||
           wire.size()>MaxEnvelopeBytes)return Reject();
        const auto decoded=YtTeamWireLiteV415::Decode(wire);
        if(decoded.kind!=Kind::Snapshot || decoded.epoch!=epoch ||
           decoded.last!=last)return Reject();
        Record prepared;
        prepared.kind=Kind::Snapshot;
        prepared.epoch=epoch;prepared.last=last;
        prepared.wire.assign(wire.begin(),wire.end());
        snapshot_=std::move(prepared);
        staged_bytes_=wire.size();
        epoch_=epoch;cursor_=last;
        active_=ever_active_=true;
        ++stats_.snapshots;
        return true;
    }
    // Stage ONLY a V423::Advanced batch, never a heartbeat/replay.
    // Overlapping batches retain their original bytes and carry an
    // explicit skip_through fence for the future typed consumer.
    // Cursor is a STAGED high-water mark, not game-applied progress.
    bool StageEntries(std::span<const std::uint8_t> wire,
                      std::uint64_t epoch,std::uint64_t last,
                      std::uint64_t first,std::uint64_t tail,
                      std::uint32_t count) {
        if(!active_ || epoch!=epoch_ || !count || wire.empty() ||
           wire.size()>MaxEnvelopeBytes || batches_.size()>=MaxDeltaBatches ||
           wire.size()>MaxStagedBytes-staged_bytes_ ||
           cursor_==UINT64_MAX || first>cursor_+1u || tail<=cursor_)
            return Reject();
        const auto decoded=YtTeamWireLiteV415::Decode(wire);
        if(decoded.kind!=Kind::Entries || decoded.epoch!=epoch ||
           decoded.last!=last || decoded.entry_count!=count ||
           decoded.first_entry_seq!=first ||
           decoded.last_entry_seq!=tail)return Reject();
        Record prepared;
        prepared.kind=Kind::Entries;
        prepared.epoch=epoch;prepared.last=last;
        prepared.first=first;prepared.tail=tail;
        prepared.skip_through=cursor_;prepared.count=count;
        prepared.wire.assign(wire.begin(),wire.end());
        batches_.push_back(std::move(prepared));
        staged_bytes_+=wire.size();
        cursor_=tail;
        ++stats_.delta_batches;
        return true;
    }
    void Revoke() noexcept {
        if(active_)++stats_.revoked;
        active_=false;epoch_=cursor_=0;
        Wipe(snapshot_.wire);
        snapshot_={};
        for(auto& batch:batches_)Wipe(batch.wire);
        batches_.clear();
        staged_bytes_=0;
    }
    bool Active() const noexcept{return active_;}
    std::uint64_t Epoch() const noexcept{return epoch_;}
    std::uint64_t StagedCursor() const noexcept{return cursor_;}
    std::size_t StagedBytes() const noexcept{return staged_bytes_;}
    std::size_t PendingPackets() const noexcept {
        return (active_?1u:0u)+batches_.size();
    }
    Counters Stats() const noexcept{return stats_;}
    const Record* Peek(std::size_t index) const noexcept {
        if(!active_)return nullptr;
        if(index==0u)return &snapshot_;
        if(index-1u>=batches_.size())return nullptr;
        return &batches_[index-1u];
    }
private:
    static void Wipe(std::vector<std::uint8_t>& b) noexcept {
        std::fill(b.begin(),b.end(),std::uint8_t{0});
        b.clear();
    }
    bool Reject() noexcept {++stats_.rejected;return false;}
    Record snapshot_{};
    std::deque<Record> batches_{};
    Counters stats_{};
    std::uint64_t epoch_=0,cursor_=0;
    std::size_t staged_bytes_=0;
    bool active_=false,ever_active_=false;
};
} // namespace SeamlessHunt
