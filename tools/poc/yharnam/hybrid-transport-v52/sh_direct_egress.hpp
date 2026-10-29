// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include "sh_direct_crypto.hpp"
#include "sh_direct_ingress.hpp"
#include <cstdint>
#include <span>
#include <string_view>
#include <vector>

// V65: outbound native game-frame transport switch. The caller owns the actual
// Yharnam Together UDP socket (P2PTransport::Transmit) and old shadNet relay
// path. No extra socket, protocol replacement or production grants are created.
// All grant/world/role/crypto inputs MUST come from an authenticated trusted
// server control channel; the local client cannot set them from arbitrary JSON.
//
// It is intentionally not invoked in the real game build yet: real server
// rendezvous/grant keys, NAT probing, source identity and stream migration are
// blocking. This component proves the direct/relay atomic sending boundary.
namespace SeamlessHunt::Hybrid {

using SendDatagram = bool (*)(std::span<const std::uint8_t>, void*) noexcept;

enum class GameSendResult : std::uint8_t {
    DirectSent,
    RelaySent,
    BothFailed,
};

// Statistics are transport-level only. They make no claims about observed
// Fornex savings until the game transport actually uses this component.
struct EgressStats {
    std::uint64_t direct_frames = 0;
    std::uint64_t direct_bytes = 0;
    std::uint64_t relay_frames = 0;
    std::uint64_t relay_bytes = 0;
    std::uint64_t direct_failures = 0;
    std::uint64_t relay_failures = 0;
    std::uint64_t control_datagrams = 0;
};

class DirectEgress final {
public:
    bool Arm(const PeerTicket& local_to_remote, DirectionMac& outbound_mac,
             DirectIngress& authenticated_remote_to_local,
             std::int64_t now_ms) noexcept {
        Reset();
        if (!authenticated_remote_to_local.MatchesReverse(local_to_remote) ||
            !encoder_.Arm(local_to_remote, outbound_mac, now_ms))
            return false;
        authenticated_reverse_ = &authenticated_remote_to_local;
        outbound_ = local_to_remote;
        return true;
    }

    // No route-choice retry is made for a single native game frame. Sending
    // to a peer fails -> send the ORIGINAL frame through old shadNet relay.
    // No packet splitting: GameLink seq/ACK semantics are not violated.
    GameSendResult SendGame(std::span<const std::uint8_t> native_frame,
                            std::string_view server_verified_local_game_sender,
                            const ChannelAuthority& current_authority,
                            std::int64_t now_ms,
                            SendDatagram send_direct, void* direct_ctx,
                            SendDatagram send_relay, void* relay_ctx) {
        if (send_relay == nullptr) {
            ++stats_.relay_failures;
            return GameSendResult::BothFailed;
        }

        if (authenticated_reverse_ && send_direct &&
            authenticated_reverse_->MatchesReverse(outbound_) &&
            authenticated_reverse_->CurrentPath(now_ms) == Path::Direct &&
            native_frame.size() <= DirectReceiver::kMaxPayloadBytes &&
            EligibleNativeWireFrame(native_frame,
                                    server_verified_local_game_sender,
                                    current_authority).direct_eligible) {
            std::vector<std::uint8_t> signed_udp;
            if (encoder_.Encode(DirectKind::GameData, native_frame,
                                now_ms, signed_udp)) {
                if (send_direct(signed_udp, direct_ctx)) {
                    ++stats_.direct_frames;
                    stats_.direct_bytes += signed_udp.size();
                    return GameSendResult::DirectSent;
                }
                ++stats_.direct_failures;
                authenticated_reverse_->DirectTransmitFailed(now_ms);
            }
        }

        // Oversize, mixed-authority, expired, stale map/owner, incomplete
        // reliable-stream handover and missing direct socket all retain
        // the ORIGINAL native SHAD frame for authoritative server handling.
        if (send_relay(native_frame, relay_ctx)) {
            ++stats_.relay_frames;
            stats_.relay_bytes += native_frame.size();
            return GameSendResult::RelaySent;
        }
        ++stats_.relay_failures;
        return GameSendResult::BothFailed;
    }

    // Probes and heartbeat are exchanged only between the two authorized
    // endpoints (no speculative arbitrary peer IPs). The full application
    // must rate-limit probes, schedule expiry and handle NAT candidates.
    bool SendControl(DirectKind kind, std::int64_t now_ms,
                     SendDatagram send_direct, void* direct_ctx) {
        if (kind == DirectKind::GameData || send_direct == nullptr ||
            !authenticated_reverse_ ||
            !authenticated_reverse_->MatchesReverse(outbound_))
            return false;
        std::vector<std::uint8_t> signed_udp;
        if (!encoder_.Encode(kind, {}, now_ms, signed_udp))
            return false;
        if (!send_direct(signed_udp, direct_ctx)) {
            ++stats_.direct_failures;
            authenticated_reverse_->DirectTransmitFailed(now_ms);
            return false;
        }
        ++stats_.control_datagrams;
        return true;
    }

    const EgressStats& stats() const noexcept { return stats_; }

    void Reset() noexcept {
        encoder_.Reset();
        authenticated_reverse_ = nullptr;
        outbound_ = {};
        stats_ = {};
    }

private:
    DirectEncoder encoder_{};
    DirectIngress* authenticated_reverse_ = nullptr; // must outlive egress
    PeerTicket outbound_{};
    EgressStats stats_{};
};
} // namespace SeamlessHunt::Hybrid
