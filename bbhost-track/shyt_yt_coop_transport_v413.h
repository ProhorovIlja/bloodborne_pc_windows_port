// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

// Original Yharnam Together CoopStream framed transport for the BBHost bridge.
// REQUIRES a separately Noise-NK-authenticated SHLK Coop datagram from the
// pinned server; this adapter does NOT establish authentication or room
// membership. Completed messages are QUARANTINED and never fed to game NetSync.
// The caller must validate TeamStart, accepted party Welcome, identity, world
// epoch and current membership before any future gameplay application.
#include "coop/coop_stream.h"

#include <cstddef>
#include <cstdint>
#include <deque>
#include <span>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace SeamlessHunt {

class CoopTransportV413 final {
public:
    static constexpr std::size_t MaxMessageBytes = 64u * 1024u;
    static constexpr std::size_t MaxUnackedBytes = 128u * 1024u;
    static constexpr std::size_t MaxHeldBytes = 128u * 1024u;
    static constexpr std::size_t MaxFrameBytes = 2048u;
    static constexpr std::size_t MaxQuarantinedBytes = 128u * 1024u;
    static constexpr std::size_t MaxQuarantinedMessages = 16u;

    explicit CoopTransportV413(std::string identity, u32 run)
        : stream_(CheckIdentity(std::move(identity)), CheckRun(run), Limits()) {}

    // Queue only an envelope already approved by the higher-level caller.
    // A full queue refuses rather than allocating without bound.
    bool QueueOutgoing(std::span<const u8> message, s64 now_ms) {
        if (failed_ || message.size() > MaxMessageBytes) return false;
        const std::size_t chunks = message.empty() ? 1u :
            1u + (message.size() - 1u) / BloodborneCoop::CoopStream::ChunkBytes;
        const std::size_t bytes = message.size() + chunks;
        if (stream_.UnackedBytes() > MaxUnackedBytes ||
            bytes > MaxUnackedBytes - stream_.UnackedBytes()) return false;
        stream_.Send(message, now_ms);
        return true;
    }

    // Returns YT GameFrame bodies only. The caller still must wrap them as
    // SHLK kind Coop and seal/send with the authenticated server session.
    std::vector<std::vector<u8>> Flush(s64 now_ms) {
        // A transport ACK would assert reliable delivery before a room/world
        // consumer has processed an envelope. Do not ACK quarantined events.
        if (failed_ || !quarantine_.empty()) return {};
        auto frames = stream_.Flush(now_ms);
        for (const auto& frame : frames) {
            if (frame.size() > MaxFrameBytes) {
                Fail();
                return {};
            }
        }
        return frames;
    }

    // Must be called only AFTER the configured server address, Noise NK MAC
    // and anti-replay checks succeeded. No caller-controlled trust boolean:
    // integrate this at the existing V408 authenticated decrypt boundary.
    bool ReceiveAfterServerAuth(std::span<const u8> frame, s64 now_ms) {
        if (failed_ || frame.empty() || frame.size() > MaxFrameBytes ||
            !BloodborneCoop::DecodeGameFrame(frame)) return false;
        auto messages = stream_.Receive(frame, now_ms);
        if (stream_.Broken()) {
            Fail();
            return false;
        }
        if (stream_.TakeRestarted()) {
            // The previous world epoch may be incomplete. A fresh original
            // YT party Welcome/snapshot is required, never silently retain
            // the old transport or acknowledge queued events.
            peer_restarted_ = true;
            Invalidate();
            return false;
        }
        for (const auto& message : messages) {
            if (message.size() > MaxMessageBytes ||
                quarantine_.size() >= MaxQuarantinedMessages ||
                quarantined_bytes_ > MaxQuarantinedBytes ||
                message.size() > MaxQuarantinedBytes - quarantined_bytes_) {
                Fail();
                return false;
            }
            quarantined_bytes_ += message.size();
            quarantine_.push_back(message);
        }
        return true;
    }

    // Quarantined bytes are NOT authorization to execute a world event or
    // inject a game packet. A future validated team/world handler owns them.
    bool TakeQuarantined(std::vector<u8>& result) {
        result.clear();
        if (failed_ || quarantine_.empty()) return false;
        result = std::move(quarantine_.front());
        quarantined_bytes_ -= result.size();
        quarantine_.pop_front();
        return true;
    }

    bool TakePeerRestarted() {
        const bool was = peer_restarted_;
        peer_restarted_ = false;
        return was;
    }
    // Idempotent lifecycle invalidation on disconnect, stale session,
    // membership overflow or new peer run. A new bridge is required.
    bool Invalidate() {
        if (failed_) return false;
        Fail();
        return true;
    }
    bool Failed() const { return failed_; }
    std::size_t Quarantined() const { return quarantine_.size(); }
    std::size_t UnackedBytes() const { return stream_.UnackedBytes(); }
    u64 Resends() const { return stream_.Resends(); }

private:
    static std::string CheckIdentity(std::string name) {
        if (name.empty() || name.size() > 64u) throw std::invalid_argument("bad coop identity");
        return name;
    }
    static u32 CheckRun(u32 run) {
        if (run == 0u) throw std::invalid_argument("bad coop run");
        return run;
    }
    static BloodborneCoop::CoopStream::Limits Limits() {
        BloodborneCoop::CoopStream::Limits limits{};
        limits.message_bytes = MaxMessageBytes;
        limits.chunk_bytes = BloodborneCoop::CoopStream::ChunkBytes + 1u;
        limits.held_bytes = MaxHeldBytes;
        limits.unreliable_channels = 0u;
        return limits;
    }
    void Fail() {
        failed_ = true;
        quarantine_.clear();
        quarantined_bytes_ = 0;
    }

    BloodborneCoop::CoopStream stream_;
    std::deque<std::vector<u8>> quarantine_;
    std::size_t quarantined_bytes_ = 0;
    bool peer_restarted_ = false;
    bool failed_ = false;
};

} // namespace SeamlessHunt
