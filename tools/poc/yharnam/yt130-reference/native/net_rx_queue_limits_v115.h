// SPDX-License-Identifier: GPL-2.0-or-later
// Bounded native game UDP receive queue, original YT Protocol8 client.
// Used by the actual P2PSocket::EnqueuePacket, not an unused simulation.
#pragma once
#include <cstddef>
#include <deque>
#include <utility>

namespace Libraries::Net::RxBudget {
inline constexpr std::size_t MaxPackets = 4096;
inline constexpr std::size_t MaxPayloadBytes = 8 * 1024 * 1024;

struct Insert {
    bool accepted;
    std::size_t evicted;
};

// Bounded queue of datagrams with a .payload vector. Preserve newest UDP
// information when the game stops consuming packets; instead of building
// minutes of stale backlog, discard oldest *only on actual saturation*.
// This policy is transport-level, not an attempt to ACK reliable game data.
template<class Datagram>
Insert Enqueue(std::deque<Datagram>& queue, std::size_t& queued_bytes, Datagram packet) {
    const std::size_t added = packet.payload.size();
    if (added > MaxPayloadBytes)
        return {false, 0};
    std::size_t evicted = 0;
    while (!queue.empty() &&
           (queue.size() >= MaxPackets || queued_bytes > MaxPayloadBytes - added)) {
        queued_bytes -= queue.front().payload.size();
        queue.pop_front();
        ++evicted;
    }
    if (queue.size() >= MaxPackets || queued_bytes > MaxPayloadBytes - added)
        return {false, evicted};
    queue.emplace_back(std::move(packet));
    queued_bytes += added;
    return {true, evicted};
}

template<class Datagram>
void Consumed(const Datagram& front, std::size_t& queued_bytes) {
    const std::size_t consumed = front.payload.size();
    // Defensive: no negative accounting even if a future caller changes
    // recv semantics; original data-consumption path owns the lock.
    queued_bytes = consumed <= queued_bytes ? queued_bytes - consumed : 0;
}
} // namespace Libraries::Net::RxBudget
