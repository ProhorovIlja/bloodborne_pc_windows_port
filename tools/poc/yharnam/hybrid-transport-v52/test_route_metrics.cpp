// SPDX-License-Identifier: GPL-2.0-or-later
#include "sh_route_metrics.hpp"
#include <array>
#include <atomic>
#include <cassert>
#include <cstdint>
#include <limits>
#include <thread>
#include <vector>
using namespace SeamlessHunt::Hybrid;
int main(){
    RouteMetrics m;
    const std::array<std::uint8_t,9> valid{0xff,0xff,0xff,0xff,'S','H','A','D',0x40};
    assert(IsNativeShadGamePacket(valid.data(), valid.size()));
    assert(!IsNativeShadGamePacket(valid.data(), 8));
    assert(!IsNativeShadGamePacket(nullptr, 9));
    auto broken=valid;broken[8]=0x30;
    assert(!IsNativeShadGamePacket(broken.data(), broken.size()));
    m.NoteServerSend(200,true);
    m.NoteRelayReceive(180);
    m.NoteDirectSend(100);
    m.NoteSendFailure();
    auto disabled=m.Snapshot();
    assert(disabled.relay_out_packets==0 && disabled.send_failures==0);
    assert(!m.ShouldEmit(1));
    m.SetEnabled(true);
    assert(m.ShouldEmit(0));
    assert(!m.ShouldEmit(0));
    assert(!m.ShouldEmit(29999));
    assert(m.ShouldEmit(30000));
    assert(!m.ShouldEmit(30000));
    assert(!m.ShouldEmit(-1));
    assert(!m.ShouldEmit(30001,0));
    // Two threads must never emit on the same interval.
    RouteMetrics simultaneous(true);
    std::atomic<unsigned> emitted{0};
    std::vector<std::thread> threads;
    for(int i=0;i<8;++i) threads.emplace_back([&]{
        if(simultaneous.ShouldEmit(42))
            emitted.fetch_add(1,std::memory_order_relaxed);
    });
    for(auto& t:threads)t.join();
    assert(emitted.load()==1);
    m.NoteServerSend(250,true);
    m.NoteServerSend(30,false);
    m.NoteRelayReceive(170);
    m.NoteDirectSend(120);
    m.NoteDirectReceive(80);
    m.NoteSendFailure();
    auto snap=m.Snapshot();
    assert(snap.relay_out_packets==2 && snap.relay_out_bytes==280);
    assert(snap.relay_out_game_packets==1 && snap.relay_out_game_bytes==250);
    assert(snap.relay_in_packets==1 && snap.relay_in_bytes==170);
    assert(snap.native_direct_out_packets==1 && snap.native_direct_out_bytes==120);
    assert(snap.native_direct_in_packets==1 && snap.native_direct_in_bytes==80);
    assert(snap.send_failures==1);
    m.SetEnabled(false);
    m.NoteServerSend(7,true);
    assert(m.Snapshot().relay_out_packets==2);
    return 0;
}
