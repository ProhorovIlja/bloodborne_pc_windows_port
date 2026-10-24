#ifdef NDEBUG
#undef NDEBUG
#endif
#include "sh_login_admission.hpp"
#include <cassert>
#include <cstdint>
#include <array>
#include <limits>
#include <iostream>
using SeamlessHunt::LoginAdmission::Gate;
int main() {
    Gate ip;
    for (int n=0; n<8; ++n) assert(ip.Allow(0x7f000001,100));
    assert(!ip.Allow(0x7f000001,100));
    assert(!ip.Allow(0x7f000001,400));
    assert(ip.Allow(0x7f000001,600));
    Gate global;
    for (std::uint32_t n=0; n<24; ++n) assert(global.Allow(n+1,100));
    assert(!global.Allow(200,100));
    assert(global.Allow(200,267));
    assert(!global.Allow(201,50));
    assert(global.Allow(201,60100));
    assert(global.Allow(201,60600));
    // 4-way fixed table: colliding IPv4 addresses cannot allocate unlimited state.
    auto group = [](std::uint32_t ip) {
        ip ^= ip >> 16;
        ip *= 0x7feb352du;
        ip ^= ip >> 15;
        ip *= 0x846ca68bu;
        ip ^= ip >> 16;
        return ip % Gate::Groups;
    };
    std::array<std::uint32_t,5> ips{};
    std::size_t found=0;
    const auto want=group(7);
    for(std::uint32_t ip4=1; ip4<100000 && found<ips.size(); ++ip4) {
        if(group(ip4)==want) ips[found++]=ip4;
    }
    assert(found==ips.size());
    Gate collision;
    for(std::size_t i=0;i<Gate::Ways;++i) assert(collision.Allow(ips[i],100));
    assert(!collision.Allow(ips[4],100));
    assert(collision.Allow(ips[4],30100)); // 30-second idle lease
    // Monotonic millis at the signed limit cannot overflow during refill.
    assert(collision.Allow(ips[4],std::numeric_limits<std::int64_t>::max()));
    std::cout << "PASS: bounded login admission per IP + globally, refill and clock safety\n";
}
