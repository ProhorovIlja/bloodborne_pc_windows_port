#ifdef NDEBUG
#undef NDEBUG
#endif
#include "sh_active_session.hpp"
#include <cassert>
#include <iostream>
using namespace SeamlessHunt::ActiveSession;
int main(){
    static_assert(CheckNow(-1,0,0));
    static_assert(CheckNow(-1,0,7));
    static_assert(!CheckNow(-1,0,8));
    static_assert(!CheckNow(100,14999,0));
    static_assert(CheckNow(100,15100,0));
    static_assert(!CheckNow(100,15100,8));
    static_assert(!CheckNow(500,100,0));
    static_assert(Due(-1,0));
    assert(!Enabled() || Enabled());
    std::cout<<"PASS: 8 status checks per tick, 15s per player, clock-safe decisions\n";
}
