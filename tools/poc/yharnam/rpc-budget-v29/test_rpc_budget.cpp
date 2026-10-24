#ifdef NDEBUG
#undef NDEBUG
#endif
#include "sh_rpc_budget.hpp"
#include <cassert>
#include <cstdint>
#include <limits>
#include <iostream>
using namespace SeamlessHunt::RpcBudget;
int main() {
    static_assert(Fits(0, MaxBufferedRpcBytes));
    static_assert(!Fits(0, MaxBufferedRpcBytes + 1));
    static_assert(Fits(MaxBufferedRpcBytes - 10, 10));
    static_assert(!Fits(MaxBufferedRpcBytes - 10, 11));
    static_assert(!Fits(std::numeric_limits<std::size_t>::max(), 1));
    static_assert(!Fits(MaxBufferedRpcBytes + 1, 0));
    static_assert(!MustEvictAuthCache(2047));
    static_assert(MustEvictAuthCache(2048));
    static_assert(MustEvictAuthCache(2049));
    std::cout << "PASS: bounded 2 MiB RPC pending and socket-write queue; 2048 cached auth entries\n";
}
