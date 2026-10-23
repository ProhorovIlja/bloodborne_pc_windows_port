#ifdef NDEBUG
#undef NDEBUG
#endif
#include "sh_message_bounds.hpp"
#include <array>
#include <cassert>
#include <cstdint>
#include <iostream>
#include <vector>
using SeamlessHunt::StreamBounds::Assembler;
int main() {
    Assembler a; std::vector<std::uint8_t> complete;
    const std::array<std::uint8_t,2> p{'a','b'},q{'c','d'};
    assert(!a.Push(p,false,complete) && a.Buffered()==2);
    assert(a.Push(q,true,complete));
    assert(complete==std::vector<std::uint8_t>({'a','b','c','d'}));
    assert(a.Buffered()==0);
    std::vector<std::uint8_t> huge(Assembler::MaxMessageBytes-1,7);
    assert(!a.Push(huge,false,complete) && a.Buffered()==huge.size());
    assert(!a.Push(p,false,complete));
    assert(a.Discarding() && a.Buffered()==0);
    assert(!a.Push(q,false,complete) && a.Discarding());
    assert(!a.Push(q,true,complete) && !a.Discarding());
    assert(a.Push(q,true,complete) && complete.size()==2);
    assert(!a.Push(huge,false,complete));
    a.Reset(); assert(a.Buffered()==0 && !a.Discarding());
    assert(a.Push(q,true,complete));
    std::vector<std::uint8_t> over(Assembler::MaxMessageBytes+1,1);
    assert(!a.Push(over,true,complete));
    assert(!a.Discarding() && a.Buffered()==0);
    std::cout<<"PASS: bounded multipart stream, drop-until-last, reset and recovery\n";
}
