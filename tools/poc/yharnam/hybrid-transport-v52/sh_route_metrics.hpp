// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <atomic>
#include <cstddef>
#include <cstdint>

// V69 small runtime counters for the ACTUAL original native P2PTransport.
// No per-packet logs, allocations, IPs, account ids or game payload capture.
// Fast disabled path is a single cached runtime check. Samples are monotonic.
namespace SeamlessHunt::Hybrid {

struct RouteMetricsSnapshot {
    std::uint64_t relay_out_packets=0;
    std::uint64_t relay_out_bytes=0;
    std::uint64_t relay_out_game_packets=0;
    std::uint64_t relay_out_game_bytes=0;
    std::uint64_t relay_in_packets=0;
    std::uint64_t relay_in_bytes=0;
    std::uint64_t native_direct_out_packets=0;
    std::uint64_t native_direct_out_bytes=0;
    std::uint64_t native_direct_in_packets=0;
    std::uint64_t native_direct_in_bytes=0;
    std::uint64_t send_failures=0;
};

class RouteMetrics final {
public:
    explicit RouteMetrics(bool enabled=false) noexcept : enabled_(enabled) {}
    void SetEnabled(bool enabled) noexcept { enabled_.store(enabled,std::memory_order_relaxed); }
    bool enabled() const noexcept { return enabled_.load(std::memory_order_relaxed); }
    void NoteServerSend(std::size_t bytes, bool game_packet) noexcept {
        if (!enabled()) return;
        relay_out_packets_.fetch_add(1,std::memory_order_relaxed);
        relay_out_bytes_.fetch_add(bytes,std::memory_order_relaxed);
        if (game_packet) {
            relay_out_game_packets_.fetch_add(1,std::memory_order_relaxed);
            relay_out_game_bytes_.fetch_add(bytes,std::memory_order_relaxed);
        }
    }
    void NoteRelayReceive(std::size_t bytes) noexcept {
        if (!enabled()) return;
        relay_in_packets_.fetch_add(1,std::memory_order_relaxed);
        relay_in_bytes_.fetch_add(bytes,std::memory_order_relaxed);
    }
    void NoteDirectSend(std::size_t bytes) noexcept {
        if (!enabled()) return;
        native_direct_out_packets_.fetch_add(1,std::memory_order_relaxed);
        native_direct_out_bytes_.fetch_add(bytes,std::memory_order_relaxed);
    }
    void NoteDirectReceive(std::size_t bytes) noexcept {
        if (!enabled()) return;
        native_direct_in_packets_.fetch_add(1,std::memory_order_relaxed);
        native_direct_in_bytes_.fetch_add(bytes,std::memory_order_relaxed);
    }
    void NoteSendFailure() noexcept {
        if(enabled())send_failures_.fetch_add(1,std::memory_order_relaxed);
    }
    RouteMetricsSnapshot Snapshot() const noexcept {
        return {relay_out_packets_.load(std::memory_order_relaxed),
                relay_out_bytes_.load(std::memory_order_relaxed),
                relay_out_game_packets_.load(std::memory_order_relaxed),
                relay_out_game_bytes_.load(std::memory_order_relaxed),
                relay_in_packets_.load(std::memory_order_relaxed),
                relay_in_bytes_.load(std::memory_order_relaxed),
                native_direct_out_packets_.load(std::memory_order_relaxed),
                native_direct_out_bytes_.load(std::memory_order_relaxed),
                native_direct_in_packets_.load(std::memory_order_relaxed),
                native_direct_in_bytes_.load(std::memory_order_relaxed),
                send_failures_.load(std::memory_order_relaxed)};
    }
    // Only one thread may emit each 30s interval. The configured metrics are
    // opt-in; compare cumulative values across successive snapshots.
    bool ShouldEmit(std::int64_t now_ms,
                    std::int64_t period_ms=30000) noexcept {
        if (!enabled() || now_ms < 0 || period_ms <= 0) return false;
        auto prev=last_emitted_ms_.load(std::memory_order_relaxed);
        while (prev < 0 || (now_ms>=prev && now_ms-prev>=period_ms)) {
            if (last_emitted_ms_.compare_exchange_weak(
                prev,now_ms,std::memory_order_relaxed))
                return true;
        }
        return false;
    }
private:
    std::atomic<bool> enabled_{false};
    std::atomic<std::int64_t> last_emitted_ms_{-1};
    std::atomic<std::uint64_t> relay_out_packets_{0}, relay_out_bytes_{0};
    std::atomic<std::uint64_t> relay_out_game_packets_{0}, relay_out_game_bytes_{0};
    std::atomic<std::uint64_t> relay_in_packets_{0}, relay_in_bytes_{0};
    std::atomic<std::uint64_t> native_direct_out_packets_{0}, native_direct_out_bytes_{0};
    std::atomic<std::uint64_t> native_direct_in_packets_{0}, native_direct_in_bytes_{0};
    std::atomic<std::uint64_t> send_failures_{0};
};

// Determines the *native* SHAD/0x40 game packet without parsing user data.
// Native frame carries two 16-bit virtual ports in the first four bytes.
inline bool IsNativeShadGamePacket(const void* frame,
                                   std::size_t size) noexcept {
    if (!frame || size < 9) return false;
    const auto* p=static_cast<const std::uint8_t*>(frame);
    return p[4]=='S' && p[5]=='H' && p[6]=='A' && p[7]=='D' && p[8]==0x40;
}

} // namespace SeamlessHunt::Hybrid
