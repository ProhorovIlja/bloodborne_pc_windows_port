// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <cstddef>
#include <cstdint>
#include <span>

// V58: bounded authenticated-direct UDP envelope and anti-replay receiver.
// This is an independent native component, not wired to game sockets yet.
// A real server-verified rendezvous grant and an audited keyed HMAC-SHA256
// implementation (16-byte tag truncation) MUST be supplied by the caller.
// Never use a plain hash or the synthetic tag used in test_direct_datagram.cpp.
namespace SeamlessHunt::Hybrid {

enum class DirectKind : std::uint8_t { Probe = 1, ProbeAck = 2, GameData = 3, Heartbeat = 4 };

struct PeerTicket {
    std::uint64_t session_epoch = 0;
    std::uint64_t pair_binding = 0;
    std::uint64_t authenticated_sender = 0;
    std::uint64_t local_receiver = 0;
    std::int64_t expires_at_ms = 0;
    // These flags are set only after verifying the SERVER-issued grant.
    // Never deserialize them from an untrusted UDP datagram.
    bool server_grant_verified = false;
    bool both_consented = false;
    bool version_compatible = false;
};

struct DirectFrame {
    DirectKind kind = DirectKind::Probe;
    std::uint64_t sequence = 0;
    std::span<const std::uint8_t> payload{};
};

using VerifyDirectTag = bool (*)(std::span<const std::uint8_t> authenticated_bytes,
                                  std::span<const std::uint8_t> tag,
                                  void* crypto_context) noexcept;

class DirectReceiver final {
public:
    static constexpr std::size_t kHeaderBytes = 52;
    static constexpr std::size_t kTagBytes = 16;
    static constexpr std::size_t kMaxDatagramBytes = 1232; // avoid common MTU fragmentation
    static constexpr std::size_t kMaxPayloadBytes =
        kMaxDatagramBytes - kHeaderBytes - kTagBytes;

    // A complete authenticated grant creates a fresh, per-direction replay window.
    // Never re-arm using a sender-controlled packet: that would reopen replay.
    bool Arm(const PeerTicket& ticket, std::int64_t now_ms) noexcept {
        Reset();
        if (ticket.session_epoch == 0 || ticket.pair_binding == 0 ||
            ticket.authenticated_sender == 0 || ticket.local_receiver == 0 ||
            ticket.authenticated_sender == ticket.local_receiver ||
            ticket.expires_at_ms <= now_ms || !ticket.server_grant_verified ||
            !ticket.both_consented || !ticket.version_compatible)
            return false;
        ticket_ = ticket;
        started_at_ms_ = now_ms;
        armed_ = true;
        return true;
    }

    // Run *before* any game-frame decoder, game state mutation or selector
    // VerifiedProbe/VerifiedDirectHeartbeat call. The MAC callback must verify
    // a fixed-key, constant-time HMAC-SHA256 truncated to 16 bytes with a
    // per-direction, per-session key established by authenticated rendezvous.
    // It must NOT trust the unverified packet or accept an empty/zero tag.
    bool Receive(std::span<const std::uint8_t> bytes, std::int64_t now_ms,
                 VerifyDirectTag verify, void* context, DirectFrame& out) noexcept {
        out = {};
        if (!armed_ || verify == nullptr || now_ms < started_at_ms_)
            return false;
        if (now_ms > ticket_.expires_at_ms) {
            Reset();
            return false;
        }
        if (bytes.size() < kHeaderBytes + kTagBytes ||
            bytes.size() > kMaxDatagramBytes)
            return false;
        if (bytes[0] != 'S' || bytes[1] != 'H' ||
            bytes[2] != 'P' || bytes[3] != '1' ||
            bytes[4] != 1 || bytes[6] != 0 || bytes[7] != 0 ||
            bytes[50] != 0 || bytes[51] != 0)
            return false;
        const auto kind = bytes[5];
        if (kind < 1 || kind > 4)
            return false;
        if (U64(bytes, 8) != ticket_.session_epoch ||
            U64(bytes, 16) != ticket_.pair_binding ||
            U64(bytes, 24) != ticket_.authenticated_sender ||
            U64(bytes, 32) != ticket_.local_receiver)
            return false;
        const std::uint64_t seq = U64(bytes, 40);
        if (seq == 0)
            return false;
        const std::size_t size = U16(bytes, 48);
        if (size > kMaxPayloadBytes ||
            bytes.size() != kHeaderBytes + size + kTagBytes)
            return false;
        if (kind == static_cast<std::uint8_t>(DirectKind::GameData) ?
            size == 0 : size != 0)
            return false;
        // Crucial order: reject bad tags BEFORE touching the replay window.
        if (!verify(bytes.first(kHeaderBytes + size),
                    bytes.last(kTagBytes), context))
            return false;
        if (!Fresh(seq))
            return false;
        out.kind = static_cast<DirectKind>(kind);
        out.sequence = seq;
        out.payload = bytes.subspan(kHeaderBytes, size);
        return true;
    }

    void Reset() noexcept {
        ticket_ = {};
        armed_ = false;
        started_at_ms_ = 0;
        highest_sequence_ = 0;
        seen_window_ = 0;
    }

    bool armed() const noexcept { return armed_; }

private:
    static std::uint16_t U16(std::span<const std::uint8_t> b,
                             std::size_t offset) noexcept {
        return static_cast<std::uint16_t>(
            std::uint16_t(b[offset]) | (std::uint16_t(b[offset + 1]) << 8));
    }
    static std::uint64_t U64(std::span<const std::uint8_t> b,
                             std::size_t offset) noexcept {
        std::uint64_t value = 0;
        for (unsigned i = 0; i < 8; ++i)
            value |= std::uint64_t(b[offset + i]) << (8U * i);
        return value;
    }
    // Sliding window permits benign UDP reordering while rejecting duplicates.
    // No mutation occurs until the MAC has been verified.
    bool Fresh(std::uint64_t seq) noexcept {
        if (seq > highest_sequence_) {
            const auto jump = seq - highest_sequence_;
            seen_window_ = jump >= 64 ? 1ULL : ((seen_window_ << jump) | 1ULL);
            highest_sequence_ = seq;
            return true;
        }
        const auto distance = highest_sequence_ - seq;
        if (distance >= 64)
            return false;
        const auto bit = std::uint64_t{1} << distance;
        if ((seen_window_ & bit) != 0)
            return false;
        seen_window_ |= bit;
        return true;
    }

    PeerTicket ticket_{};
    bool armed_ = false;
    std::int64_t started_at_ms_ = 0;
    std::uint64_t highest_sequence_ = 0;
    std::uint64_t seen_window_ = 0;
};

} // namespace SeamlessHunt::Hybrid
