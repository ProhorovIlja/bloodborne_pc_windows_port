// SPDX-License-Identifier: GPL-2.0-or-later
#include "net_p2p_log_budget_v116.h"
#include <atomic>
#include <cstdio>
#include <thread>
#include <vector>
using Libraries::Net::PacketLogBudget::Take;
#define CHECK(x) do { if (!(x)) {std::fprintf(stderr,"failed line %d: %s\n",__LINE__,#x);return 1;} } while (0)
int main() {
    std::atomic<std::uint32_t> short_logs{0}, long_logs{0};
    for (unsigned i=0; i<500000; ++i) {
        CHECK(Take(short_logs,3000)==(i<3000));
        CHECK(Take(long_logs,3000)==(i<3000));
    }
    CHECK(short_logs.load()==3000 && long_logs.load()==3000);
    // After saturation the old code performed an atomic write per packet
    // forever, eventually wrapping and re-enabling diagnostic logs.
    CHECK(!Take(short_logs,3000));
    CHECK(short_logs.load()==3000);
    std::atomic<std::uint32_t> contended{0};
    std::atomic<unsigned> accepted{0};
    std::vector<std::thread> threads;
    for (int i=0;i<8;++i) threads.emplace_back([&] {
        for (int j=0;j<6000;++j)
            if (Take(contended,3000))
                ++accepted;
    });
    for (auto& thread:threads) thread.join();
    CHECK(contended.load()==3000 && accepted.load()==3000);
    std::atomic<std::uint32_t> none{0};
    CHECK(!Take(none,0) && none.load()==0);
    std::puts("YT130_V116_NATIVE_UDP_PACKET_LOG_BUDGET_PASS");
    return 0;
}
