// SPDX-License-Identifier: GPL-2.0-or-later
// Standalone safety test of the two targeted ServerLink::Hub relay hotpath
// changes, no Qt headers or game data. Not a real game performance benchmark.
#include <algorithm>
#include <array>
#include <cassert>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <string>
#include <string_view>
#include <vector>

bool OldIsGamePacket(std::string_view frame, bool hasRoutes, unsigned char gameType) {
    return hasRoutes && frame.size() >= 9 &&
           frame.substr(4, 4) == "SHAD" &&
           static_cast<unsigned char>(frame[8]) == gameType;
}
bool NewIsGamePacket(std::string_view frame, bool hasRoutes, unsigned char gameType) {
    return hasRoutes && frame.size() >= 9 &&
           std::memcmp(frame.data() + 4, "SHAD", 4) == 0 &&
           static_cast<unsigned char>(frame[8]) == gameType;
}

std::vector<std::uint64_t> LoggedCountsOriginal(int limit, int packets) {
    std::uint64_t count = 0;
    std::vector<std::uint64_t> result;
    for (int n = 0; n < packets; ++n) {
        ++count;
        if (count <= static_cast<std::uint64_t>(limit)) result.push_back(count);
    }
    return result;
}
std::vector<std::uint64_t> LoggedCountsOptimized(int limit, int packets) {
    std::uint64_t count = 0;
    std::vector<std::uint64_t> result;
    for (int n = 0; n < packets; ++n) {
        if (limit > 0 && count < static_cast<std::uint64_t>(limit)) {
            ++count;
            result.push_back(count);
        }
    }
    return result;
}

int main() {
    // Compare behavior for malformed, short, exact-boundary, and longer
    // frames. The memcmp is only reachable after frame.size() >= 9.
    for (int size = 0; size < 256; ++size) {
        std::string frame(static_cast<std::size_t>(size), 'Z');
        for (int magic = 0; magic < 4; ++magic) {
            for (int hasRoutes = 0; hasRoutes < 2; ++hasRoutes) {
                if (size >= 9) {
                    frame.replace(4, 4, magic == 0 ? "SHAD" :
                                         magic == 1 ? "SHLK" :
                                         magic == 2 ? "shad" : "SHAX");
                    frame[8] = static_cast<char>(magic & 1 ? 0x40 : 0x41);
                }
                assert(OldIsGamePacket(frame, hasRoutes != 0, 0x40) ==
                       NewIsGamePacket(frame, hasRoutes != 0, 0x40));
                assert(OldIsGamePacket(frame, hasRoutes != 0, 0x41) ==
                       NewIsGamePacket(frame, hasRoutes != 0, 0x41));
            }
        }
    }
    // Keeping only N pair-start debug messages must not remove any
    // actual game datagrams, nor change logging of the first N frames.
    for (int limit : {0, 1, 2, 20, 200}) {
        for (int packets : {0, 1, 2, 20, 200, 2500}) {
            assert(LoggedCountsOriginal(limit, packets) ==
                   LoggedCountsOptimized(limit, packets));
        }
    }
    std::cout << "SHYT_V45_CPP_SERVER_RELAY_SEMANTICS_PASS\n";
    return 0;
}
