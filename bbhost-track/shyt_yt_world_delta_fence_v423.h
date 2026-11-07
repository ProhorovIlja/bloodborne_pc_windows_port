// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V423: fail-closed, READ-ONLY original YT world-log ordering fence.
// It sees only MAC-authenticated server messages already validated by
// original CoopStream and the bounded V421/V422 protobuf decoder.
// It NEVER applies events, writes saves, grants guest NetSync or P2P.
#include <cstdint>

namespace SeamlessHunt {
class YtWorldDeltaFenceV423 final {
public:
    enum class Verdict : std::uint8_t {
        Unbound, Heartbeat, Replay, Advanced, Gap, EpochChanged, Invalid
    };
    struct Counters {
        std::uint64_t heartbeats=0;
        std::uint64_t replays=0;
        std::uint64_t advanced=0;
        std::uint64_t gaps=0;
        std::uint64_t epoch_changes=0;
        std::uint64_t invalid=0;
        std::uint64_t unbound=0;
        std::uint64_t contexts_revoked=0;
    };

    // Arm only when the correlated V419 Welcome's epoch/last is reconciled
    // with an explicitly requested, structurally validated V421 Snapshot.
    // No rearm in the same authenticated party link after a stale/gapped
    // world. The future game consumer must establish a NEW safe snapshot.
    bool Arm(std::uint64_t epoch,std::uint64_t snapshot_last) noexcept {
        if(armed_ || ever_armed_ || epoch==0u)return false;
        epoch_=epoch;
        cursor_=snapshot_last;
        server_last_=snapshot_last;
        ever_armed_=armed_=true;
        return true;
    }

    // These batch ranges are already structurally verified against exact
    // original YT v1.4.0 protobuf. No payload is consumed or forwarded.
    Verdict Observe(std::uint64_t epoch,std::uint64_t announced_last,
                    std::uint64_t first,std::uint64_t tail,
                    std::uint32_t count) noexcept {
        if(!armed_) {
            ++stats_.unbound;
            return Verdict::Unbound;
        }
        if(epoch!=epoch_) {
            ++stats_.epoch_changes;
            Revoke();
            return Verdict::EpochChanged;
        }
        if(count>256u || (count==0u && (first!=0u || tail!=0u)) ||
           (count!=0u && (first==0u || tail<first ||
                           tail-first!=static_cast<std::uint64_t>(count-1u) ||
                           tail>announced_last))) {
            ++stats_.invalid;
            Revoke();
            return Verdict::Invalid;
        }

        // An older authenticated batch can arrive after a newer Snapshot
        // without rolling back the cursor. Its log must not be reapplied.
        if(announced_last<cursor_ || (count!=0u && tail<=cursor_)) {
            ++stats_.replays;
            return Verdict::Replay;
        }
        if(count==0u) {
            if(announced_last>cursor_) {
                ++stats_.gaps;
                Revoke();
                return Verdict::Gap; // heartbeat exposes a missing delta
            }
            ++stats_.heartbeats;
            return Verdict::Heartbeat;
        }
        if(cursor_==UINT64_MAX || first>cursor_+1u) {
            ++stats_.gaps;
            Revoke();
            return Verdict::Gap;
        }
        // Overlaps from the bounded server replay/resend window are okay:
        // advance only the genuinely new tail, never replay old seqs.
        cursor_=tail;
        if(announced_last>server_last_)server_last_=announced_last;
        ++stats_.advanced;
        return Verdict::Advanced;
    }

    void Revoke() noexcept {
        if(armed_)++stats_.contexts_revoked;
        armed_=false;
        epoch_=cursor_=server_last_=0u;
    }
    bool Armed() const noexcept {return armed_;}
    std::uint64_t Epoch() const noexcept {return epoch_;}
    std::uint64_t Cursor() const noexcept {return cursor_;}
    std::uint64_t ServerLast() const noexcept {return server_last_;}
    bool Behind() const noexcept {return armed_ && cursor_<server_last_;}
    Counters Stats() const noexcept {return stats_;}
private:
    Counters stats_{};
    std::uint64_t epoch_=0u,cursor_=0u,server_last_=0u;
    bool armed_=false,ever_armed_=false;
};
} // namespace SeamlessHunt
