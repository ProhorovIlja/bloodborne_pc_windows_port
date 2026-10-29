// SPDX-License-Identifier: GPL-2.0-or-later
// Builds the SAME header consumed by real native YT1.3 P2PSocket.
#include <cstddef>
#include <deque>
#include <vector>
#include <cstdio>
#include "net_rx_queue_limits_v115.h"

using namespace Libraries::Net;
struct Packet { std::vector<unsigned char> payload; unsigned seq=0; };
#define VERIFY(e) do { if (!(e)) {std::fprintf(stderr, "FAIL %d %s\n", __LINE__, #e);return 1;} } while (0)

int main() {
    std::deque<Packet> queue;
    std::size_t bytes=0;
    for (unsigned i=0;i<RxBudget::MaxPackets;i++){
       auto r=RxBudget::Enqueue(queue,bytes,Packet{{1,2,3,4},i});
       VERIFY(r.accepted && r.evicted==0);
    }
    VERIFY(queue.size()==RxBudget::MaxPackets);
    VERIFY(bytes==RxBudget::MaxPackets*4);
    auto overflow=RxBudget::Enqueue(queue,bytes,Packet{{1,2,3,4},99999});
    VERIFY(overflow.accepted && overflow.evicted==1);
    VERIFY(queue.front().seq==1 && queue.back().seq==99999);
    VERIFY(bytes==queue.size()*4);
    while(!queue.empty()){
       RxBudget::Consumed(queue.front(),bytes);
       queue.pop_front();
    }
    VERIFY(bytes==0);
    auto rejected=RxBudget::Enqueue(queue,bytes,Packet{std::vector<unsigned char>(RxBudget::MaxPayloadBytes+1),77});
    VERIFY(!rejected.accepted && rejected.evicted==0 && queue.empty() && bytes==0);
    for(unsigned i=0;i<100;i++){
       auto r=RxBudget::Enqueue(queue,bytes,Packet{std::vector<unsigned char>(128*1024),i});
       VERIFY(r.accepted);
       VERIFY(queue.size()<=RxBudget::MaxPackets);
       VERIFY(bytes<=RxBudget::MaxPayloadBytes);
    }
    VERIFY(queue.size()==64);
    VERIFY(queue.front().seq==36 && queue.back().seq==99);
    VERIFY(bytes==RxBudget::MaxPayloadBytes);
    for(unsigned i=0;i<5000;i++){
       auto r=RxBudget::Enqueue(queue,bytes,Packet{{},i});
       VERIFY(r.accepted);
       VERIFY(queue.size()<=RxBudget::MaxPackets);
       VERIFY(bytes<=RxBudget::MaxPayloadBytes);
    }
    VERIFY(queue.size()==RxBudget::MaxPackets);
    std::puts("YT130_V115_NATIVE_GAME_UDP_BOUNDED_QUEUE_PASS");
    return 0;
}
