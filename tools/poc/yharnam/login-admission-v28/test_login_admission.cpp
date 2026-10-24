#ifdef NDEBUG
#undef NDEBUG
#endif
#include "sh_login_admission.hpp"
#include <cassert>
#include <cstdint>
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
    std::cout << "PASS: bounded login admission per IP + globally, refill and clock safety\n";
}
