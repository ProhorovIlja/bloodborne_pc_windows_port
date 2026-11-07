// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V419: correlate a MAC-authenticated original YT protobuf Welcome with an
// EXPLICITLY issued V418 party Hello on the SAME already-authenticated link.
// A correlated reply is merely a candidate for a later world/snapshot check:
// NEVER grant guest NetSync, P2P access, save writes or room authority here.
#include <cstdint>
#include <string>
#include <utility>

namespace SeamlessHunt {
class YtPartyReplyV419 final {
public:
    static constexpr std::uint64_t ReplyWindowMs = 15000u;
    struct Counters {
        std::uint64_t party_hellos_sent = 0;
        std::uint64_t replies_correlated = 0;
        std::uint64_t replies_refused = 0;
        std::uint64_t replies_unbound = 0;
        std::uint64_t contexts_revoked = 0;
    };
    enum class Reply { Unbound, CorrelatedCandidate, Refused };

    // Caller must have independently verified a MAC-authenticated server
    // TeamStart and its selected loaded save slot before arming. The tracked
    // run is a local context fence, NOT a server-issued token in Welcome.
    bool Arm(std::string party, std::uint32_t slot, std::uint32_t run,
             std::uint64_t now_ms) {
        if (pending_ || candidate_ || party.empty() || party.size() > 255u ||
            run == 0u || counters_.party_hellos_sent != 0u) return false;
        party_ = std::move(party);
        slot_ = slot;
        run_ = run;
        sent_at_ms_ = now_ms;
        pending_ = true;
        ++counters_.party_hellos_sent;
        return true;
    }
    // A roster, team, world, save, stream or link change irrevocably fences
    // both pending and previously correlated responses. Never auto-rearm.
    void Revoke() noexcept {
        if (pending_ || candidate_) ++counters_.contexts_revoked;
        pending_ = false;
        candidate_ = false;
        party_.clear();
        slot_ = run_ = 0;
        sent_at_ms_ = 0;
    }
    // still_prepared must be revalidated by V414 from the currently
    // authenticated lobby/TeamStart, for the ORIGINAL party and slot.
    // The Welcome protobuf does NOT echo either party or run: never describe
    // this as cryptographic proof of a world or grant gameplay authority.
    Reply OnAuthenticatedWelcome(bool accepted, std::uint64_t now_ms,
                                 bool still_prepared) noexcept {
        if (!pending_ || !still_prepared || now_ms < sent_at_ms_ ||
            now_ms - sent_at_ms_ > ReplyWindowMs) {
            Revoke();
            ++counters_.replies_unbound;
            return Reply::Unbound;
        }
        pending_ = false; // exactly one reply per explicitly issued Hello
        if (!accepted) {
            ++counters_.replies_refused;
            return Reply::Refused;
        }
        candidate_ = true;
        ++counters_.replies_correlated;
        return Reply::CorrelatedCandidate;
    }
    bool Pending() const noexcept { return pending_; }
    bool CandidateAwaitingSnapshot() const noexcept { return candidate_; }
    const std::string& Party() const noexcept { return party_; }
    std::uint32_t Slot() const noexcept { return slot_; }
    std::uint32_t Run() const noexcept { return run_; }
    Counters Stats() const noexcept { return counters_; }
private:
    Counters counters_{};
    std::string party_;
    std::uint32_t slot_ = 0, run_ = 0;
    std::uint64_t sent_at_ms_ = 0;
    bool pending_ = false, candidate_ = false;
};
} // namespace SeamlessHunt
