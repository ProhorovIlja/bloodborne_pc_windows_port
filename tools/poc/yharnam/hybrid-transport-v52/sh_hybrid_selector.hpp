// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <cstdint>

// Source-only V52 transport selector for future *authenticated* shadNet peer
// rendezvous. It does not create sockets, authenticate packets or enable P2P.
// The game still uses shadNet UDP relay until session-bound, consented,
// server-authorized candidate exchange and live 2-PC tests are implemented.
namespace SeamlessHunt::Hybrid {

enum class Path : std::uint8_t { Relay, Direct };
enum class Phase : std::uint8_t { RelayOnly, Probing, DirectReady, Cooldown };

struct Grant {
    std::uint64_t session_epoch = 0; // invalid after leave / host migration
    std::uint64_t peer_binding = 0;  // server-verified peer, not character name
    std::int64_t valid_until_ms = 0;
    bool verified_server_authorization = false; // provided ONLY by validated ticket handler
    bool local_consent = false;
    bool peer_consent = false;
    bool protocol_compatible = false;
};

class Selector final {
public:
    static constexpr std::int64_t kProbeWindowMs = 5000;
    static constexpr std::int64_t kPathSilenceMs = 2000;
    static constexpr std::int64_t kCooldownMs = 10000;
    static constexpr unsigned kRequiredProbes = 3;

    // Always starts on relay, regardless of connection history.
    bool Begin(const Grant& candidate, std::int64_t now_ms) noexcept {
        Reset();
        if (candidate.session_epoch == 0 || candidate.peer_binding == 0 ||
            candidate.valid_until_ms <= now_ms ||
            !candidate.verified_server_authorization || !candidate.local_consent ||
            !candidate.peer_consent || !candidate.protocol_compatible)
            return false;
        grant_ = candidate;
        phase_ = Phase::Probing;
        probe_started_ms_ = now_ms;
        return true;
    }

    // The CALLER must verify the packet MAC/session ticket, peer endpoint,
    // session generation, and replay sequence BEFORE setting authenticated.
    // An untrusted client-controlled "ack" is not a verified probe.
    bool VerifiedProbe(std::uint64_t session_epoch, std::uint64_t sequence,
                       bool authenticated, std::int64_t now_ms) noexcept {
        if (phase_ != Phase::Probing || !authenticated ||
            !StillGranted(now_ms) || session_epoch != grant_.session_epoch ||
            sequence == 0 || sequence <= last_sequence_ ||
            now_ms < probe_started_ms_ ||
            now_ms - probe_started_ms_ > kProbeWindowMs)
            return false;
        last_sequence_ = sequence;
        ++probes_;
        last_verified_ms_ = now_ms;
        if (probes_ >= kRequiredProbes)
            phase_ = Phase::DirectReady;
        return true;
    }

    // An established direct route needs recurring authenticated liveness.
    // Replayed acknowledgements and callbacks for another match do nothing.
    bool VerifiedDirectHeartbeat(std::uint64_t session_epoch, std::uint64_t sequence,
                                 bool authenticated, std::int64_t now_ms) noexcept {
        if (phase_ != Phase::DirectReady || !authenticated ||
            !StillGranted(now_ms) || session_epoch != grant_.session_epoch ||
            sequence == 0 || sequence <= last_sequence_ ||
            now_ms < last_verified_ms_ ||
            now_ms - last_verified_ms_ > kPathSilenceMs)
            return false;
        last_sequence_ = sequence;
        last_verified_ms_ = now_ms;
        return true;
    }

    // The channel predicate must agree with V10's Pass-only native packet gate.
    // Direct can NEVER carry enemy/world owner/map-sensitive game traffic.
    Path Choose(bool entire_frame_is_direct_safe, std::int64_t now_ms) noexcept {
        if (!StillGranted(now_ms)) {
            Reset();
            return Path::Relay;
        }
        // An abandoned NAT probe must not remain in Probing indefinitely.
        if (phase_ == Phase::Probing &&
            (now_ms < probe_started_ms_ ||
             now_ms - probe_started_ms_ > kProbeWindowMs))
            Fallback(now_ms);
        if (phase_ == Phase::DirectReady &&
            (now_ms < last_verified_ms_ ||
             now_ms - last_verified_ms_ > kPathSilenceMs)) {
            Fallback(now_ms);
        }
        return phase_ == Phase::DirectReady && entire_frame_is_direct_safe
                   ? Path::Direct : Path::Relay;
    }

    void Fallback(std::int64_t now_ms) noexcept {
        // Immediate fallback, and no rapid direct/relay oscillation.
        if (phase_ == Phase::DirectReady || phase_ == Phase::Probing) {
            phase_ = Phase::Cooldown;
            cooldown_until_ms_ = now_ms + kCooldownMs;
            probes_ = 0;
            last_sequence_ = 0;
        }
    }

    bool Retry(std::int64_t now_ms) noexcept {
        if (!StillGranted(now_ms)) {
            Reset();
            return false;
        }
        if (phase_ != Phase::Cooldown || now_ms < cooldown_until_ms_)
            return false;
        phase_ = Phase::Probing;
        probes_ = 0;
        last_sequence_ = 0;
        probe_started_ms_ = now_ms;
        last_verified_ms_ = 0;
        return true;
    }

    // Called immediately for room departure, revoked consent, peer ban,
    // credentials change, mismatched game version or host/session migration.
    void Reset() noexcept {
        grant_ = {};
        phase_ = Phase::RelayOnly;
        probes_ = 0;
        last_sequence_ = 0;
        last_verified_ms_ = 0;
        probe_started_ms_ = 0;
        cooldown_until_ms_ = 0;
    }

    Phase phase() const noexcept { return phase_; }

private:
    bool StillGranted(std::int64_t now_ms) const noexcept {
        return phase_ != Phase::RelayOnly &&
               grant_.verified_server_authorization && grant_.local_consent &&
               grant_.peer_consent && grant_.protocol_compatible &&
               now_ms <= grant_.valid_until_ms;
    }

    Grant grant_{};
    Phase phase_ = Phase::RelayOnly;
    unsigned probes_ = 0;
    std::uint64_t last_sequence_ = 0;
    std::int64_t probe_started_ms_ = 0;
    std::int64_t last_verified_ms_ = 0;
    std::int64_t cooldown_until_ms_ = 0;
};

} // namespace SeamlessHunt::Hybrid
