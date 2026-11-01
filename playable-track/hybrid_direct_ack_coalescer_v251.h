// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V251: suppress redundant reliable-stream ACK copies when YT's original
// GameLinkPeer::Flush piggybacks the *same* cumulative ack on every movement.
// ACKs still traverse existing authenticated shadNet server link at first
// observation, on advancement/epoch change and periodically under packet loss.
// This wrapper changes NO source sequence, shadNet route or original GameFrame.
#include "hybrid_direct_egress_v240.h"
#include <cstdint>
#include <string>
#include <string_view>
#include <utility>

namespace BloodborneCoop::SHYTHybrid {

class DirectAckCoalescerV251 {
public:
    static constexpr s64 AckRefreshMs = 750;
    struct Scope {
        std::string party, sender, receiver;
        u32 sender_instance = 0;
        u32 receiver_instance = 0;
        u64 epoch = 0;
        bool operator==(const Scope&) const = default;
    };

    // Never call Reset() or access an instance concurrently with a Send:
    // caller owns exactly one tracker per ordered peer pair/connection thread.
    void Reset() {
        scope_ = {};
        valid_ = false;
        sent_ = false;
        last_ack_ = 0;
        last_sent_ms_ = 0;
    }

    bool MustForward(const Scope& scope, u32 ack, s64 now_ms) {
        // Invalid/surprising values fail open to SERVER, never drop an ACK.
        if (scope.party.empty() || scope.sender.empty() ||
            scope.receiver.empty() || !scope.sender_instance ||
            !scope.receiver_instance || !scope.epoch || now_ms < 0)
            return true;
        if (!valid_ || scope != scope_ || !sent_ ||
            ack != last_ack_ || now_ms < last_sent_ms_ ||
            now_ms - last_sent_ms_ >= AckRefreshMs)
            return true;
        return false;
    }

    void Sent(const Scope& scope, u32 ack, s64 now_ms) {
        if (scope.party.empty() || scope.sender.empty() ||
            scope.receiver.empty() || !scope.sender_instance ||
            !scope.receiver_instance || !scope.epoch || now_ms < 0) {
            Reset();
            return;
        }
        scope_ = scope;
        valid_ = true;
        sent_ = true;
        last_ack_ = ack;
        last_sent_ms_ = now_ms;
    }

private:
    Scope scope_{};
    bool valid_ = false;
    bool sent_ = false;
    u32 last_ack_ = 0;
    s64 last_sent_ms_ = 0;
};

// A single original YT GameLinkPeer and exact original frame still own all
// sequences and retransmissions. The tracker is an optional optimization:
// on any uncertainty the wrapper sends through existing shadNet instead.
template<typename SecureDirectSend, typename ExistingServerSend>
EgressResult SendExistingGameFrameV251(
    const GameFrame& frame, const PacketEnds& ends,
    const PeerRouteLease& lease, const DirectEgressIdentity& identity,
    DirectAckCoalescerV251& tracker,
    SecureDirectSend&& direct_send,
    ExistingServerSend&& existing_server_send)
{
    const DirectAckCoalescerV251::Scope scope{
        std::string(lease.granted_party_session_id),
        std::string(lease.granted_sender_id),
        std::string(lease.granted_receiver_id),
        lease.granted_sender_instance,
        lease.granted_receiver_instance,
        lease.authority_epoch
    };
    // Only intercept V240's ACK-only relay call, not user data or server
    // keepalives and not a full-frame fallback after a direct send failure.
    const auto relay = [&](const GameFrame& outgoing) -> bool {
        const bool ack_only = outgoing.entries.empty() &&
                              frame.entries.size() == 1 &&
                              outgoing.ack != 0 &&
                              outgoing.sender == frame.sender &&
                              outgoing.instance == frame.instance &&
                              outgoing.peer_instance == frame.peer_instance;
        if (ack_only && !tracker.MustForward(scope, outgoing.ack, lease.now_ms))
            return true;
        const bool sent = existing_server_send(outgoing);
        if (sent && outgoing.ack != 0)
            tracker.Sent(scope, outgoing.ack, lease.now_ms);
        return sent;
    };
    return SendExistingGameFrameV240(frame, ends, lease, identity,
        std::forward<SecureDirectSend>(direct_send), relay);
}
} // namespace BloodborneCoop::SHYTHybrid
