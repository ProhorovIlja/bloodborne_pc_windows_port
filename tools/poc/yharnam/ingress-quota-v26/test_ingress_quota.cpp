#ifdef NDEBUG
#undef NDEBUG
#endif
#include "sh_ingress_quota.hpp"
#include <cassert>
#include <iostream>
using SeamlessHunt::Ingress::Budget;
int main() {
    Budget b;
    for(int i=0;i<240;++i) assert(b.Accept(1,1000));
    assert(!b.Accept(1,1000));
    assert(b.Accept(1,1010)); // fractional refill (120/s)
    assert(b.Accept(8*1024*1024,5000));
    assert(b.Accept(8*1024*1024,5000));
    assert(!b.Accept(1,5000)); // byte budget exhausted
    assert(b.Accept(1,5001)); // tiny refill, even after a traffic burst
    assert(!b.Accept(9*1024*1024,10000)); // one message >8MiB
    // A long idle period can refill but cannot exceed cap.
    assert(b.Accept(8*1024*1024,20000));
    assert(b.AvailableBytes() <= Budget::BurstBytes);
    // Time going backward must not mint extra tokens.
    const auto before=b.AvailableBytes();
    assert(b.Accept(1,100)); // consumes, but cannot refill
    assert(b.AvailableBytes()==before-1);
    std::cout<<"PASS: burst messages, weighted bytes, idle refill, clock regression\n";
}
