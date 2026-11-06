// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V420: source-backed original YT party world snapshot metadata fence.
// Runs ONLY after a MAC-authenticated V419 party Welcome on the single
// original CoopStream. This does NOT decode/apply kills, flags, NPC state,
// saves, or even validate a snapshot's full protobuf payload. Never grants
// guest NetSync, P2P, team authorization or writable game memory.
#include <cstdint>

namespace SeamlessHunt {
class YtWorldSnapshotV420 final {
public:
    struct Counters {
        std::uint64_t requests_sent=0;
        std::uint64_t metadata_matching=0;
        std::uint64_t metadata_rejected=0;
        std::uint64_t metadata_unbound=0;
        std::uint64_t contexts_revoked=0;
    };
    // A Welcome is not itself a world grant: no party/run fields in its
    // protobuf. Caller must already hold a correlated V419 candidate.
    bool Arm(std::uint64_t epoch,std::uint64_t last) noexcept {
        if(armed_ || ever_armed_ || epoch==0u) return false;
        epoch_=epoch;
        last_=last;
        armed_=ever_armed_=true;
        return true;
    }
    bool CanAsk() const noexcept {
        return armed_ && !requested_ && !metadata_matching_;
    }
    // Called ONLY after the canonical SnapshotRequest has been queued in
    // the reliable outbound CoopStream. The first request asks for a full
    // snapshot with {epoch:0,seq:0}, matching an empty local game world.
    bool MarkRequested() noexcept {
        if(!CanAsk())return false;
        requested_=true;
        ++stats_.requests_sent;
        return true;
    }
    // Read-only metadata check on the server-authenticated snapshot field.
    // The application must parse/apply the COMPLETE payload, check epoch,
    // all parts, and audit game hook state in a future version.
    bool Observe(std::uint64_t epoch,std::uint64_t last) noexcept {
        if(!armed_ || !requested_ || metadata_matching_) {
            ++stats_.metadata_unbound;
            return false;
        }
        if(epoch==0u || epoch!=epoch_ || last<last_) {
            ++stats_.metadata_rejected;
            Revoke();
            return false;
        }
        metadata_matching_=true;
        ++stats_.metadata_matching;
        return true;
    }
    void Revoke() noexcept {
        if(armed_)++stats_.contexts_revoked;
        armed_=requested_=metadata_matching_=false;
        epoch_=last_=0;
        // One party Hello per link: no automatic rearm on the same link.
    }
    bool AwaitingGameSnapshotConsumer() const noexcept {
        return armed_ && metadata_matching_;
    }
    bool Armed() const noexcept {return armed_;}
    Counters Stats() const noexcept {return stats_;}
private:
    Counters stats_{};
    std::uint64_t epoch_=0,last_=0;
    bool armed_=false,ever_armed_=false,requested_=false,metadata_matching_=false;
};
} // namespace SeamlessHunt
