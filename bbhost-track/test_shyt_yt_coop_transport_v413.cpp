// SPDX-License-Identifier: GPL-2.0-or-later
// Uses the real, SHA-pinned original YT CoopStream/game_link headers in CI.
#include "shyt_yt_coop_transport_v413.h"
#include <algorithm>
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <vector>

using SeamlessHunt::CoopTransportV413;
using Bytes = std::vector<u8>;

int main() {
    CoopTransportV413 game("hunter", 11u), server("shadnet", 22u);
    Bytes world(2600u);
    for (std::size_t i = 0; i < world.size(); ++i) world[i] = static_cast<u8>((i * 17u) & 255u);
    assert(game.QueueOutgoing(world, 1000));
    auto frames = game.Flush(1000);
    assert(frames.size() >= 3u);
    assert(server.ReceiveAfterServerAuth(frames.back(), 1001)); // out of order
    assert(server.Quarantined() == 0u);
    for (std::size_t i = 0; i + 1u < frames.size(); ++i)
        assert(server.ReceiveAfterServerAuth(frames[i], 1002));
    assert(server.Quarantined() == 1u);
    // The upper layer has NOT approved/applied the world event: withholding
    // the ACK makes the server retain responsibility for retransmission.
    assert(server.Flush(1003).empty());
    Bytes received;
    assert(server.TakeQuarantined(received) && received == world);
    assert(!server.TakeQuarantined(received));
    // The original reliable stream acknowledges the ordered receive.
    for (const auto& ack : server.Flush(1003))
        assert(game.ReceiveAfterServerAuth(ack, 1004));
    assert(game.UnackedBytes() == 0u);
    // Replayed frames never deliver the same message a second time.
    for (const auto& frame : frames)
        assert(server.ReceiveAfterServerAuth(frame, 1005));
    assert(server.Quarantined() == 0u);

    // Intentionally drop a fragment, then deliver it on upstream resend.
    Bytes second(3300u, 0x7eu);
    assert(game.QueueOutgoing(second, 2000));
    auto lost = game.Flush(2000);
    assert(lost.size() > 2u);
    for (std::size_t i = 1; i < lost.size(); ++i)
        assert(server.ReceiveAfterServerAuth(lost[i], 2001));
    assert(server.Quarantined() == 0u);
    auto resend = game.Flush(2250);
    assert(!resend.empty());
    for (const auto& body : resend)
        assert(server.ReceiveAfterServerAuth(body, 2251));
    assert(server.Quarantined() == 1u);
    assert(server.TakeQuarantined(received) && received == second);
    assert(game.Resends() > 0u);

    // Oversized message and malformed wire fail closed.
    Bytes huge(CoopTransportV413::MaxMessageBytes + 1u, 1u);
    assert(!game.QueueOutgoing(huge, 2300));
    const u8 malformed[] = {0xffu, 0x00u};
    assert(!server.ReceiveAfterServerAuth(malformed, 2300));
    assert(!server.Failed()); // malformed datagram rejected, no damage to stream

    // Full completed inbox must permanently fail closed, never evict an
    // earlier event or silently drop a world event on its way to a game.
    CoopTransportV413 source("source", 101u), sink("sink", 202u);
    for (std::size_t i = 0; i <= CoopTransportV413::MaxQuarantinedMessages; ++i) {
        const Bytes msg{static_cast<u8>(i)};
        assert(source.QueueOutgoing(msg, static_cast<s64>(3000u + i)));
        const auto batch = source.Flush(static_cast<s64>(3000u + i));
        bool accepted = true;
        for (const auto& body : batch)
            accepted = sink.ReceiveAfterServerAuth(body, static_cast<s64>(3000u + i)) && accepted;
        if (i == CoopTransportV413::MaxQuarantinedMessages) assert(!accepted);
    }
    assert(sink.Failed());
    assert(sink.Quarantined() == 0u);
    assert(!sink.TakeQuarantined(received));
    assert(!sink.QueueOutgoing(Bytes{9u}, 5000));
    // Two distinct runs from the same authenticated server identity must
    // never preserve an old quarantined world envelope across restart.
    CoopTransportV413 old_run("shadnet", 801u), new_run("shadnet", 802u),
                      listener("listener", 900u);
    const Bytes old_event{0x41u, 0x42u, 0x43u};
    assert(old_run.QueueOutgoing(old_event, 6100));
    for (const auto& body : old_run.Flush(6100))
        assert(listener.ReceiveAfterServerAuth(body, 6101));
    assert(listener.Quarantined() == 1u);
    assert(new_run.QueueOutgoing(Bytes{0x99u}, 6200));
    bool accepted_restart = true;
    for (const auto& body : new_run.Flush(6200))
        accepted_restart = listener.ReceiveAfterServerAuth(body, 6201) && accepted_restart;
    assert(!accepted_restart);
    assert(listener.TakePeerRestarted());
    assert(listener.Failed());
    assert(listener.Quarantined() == 0u);
    assert(!listener.TakeQuarantined(received));
    assert(!listener.Invalidate());
    assert(listener.Flush(6300).empty());
    std::puts("SHYT_V413_ORIGINAL_YT_RELIABLE_COOP_TRANSPORT_BOUNDED_QUARANTINE_PASS");
}
