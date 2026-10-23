#ifdef NDEBUG
#undef NDEBUG
#endif
#include "sh_map_cache.hpp"
#include <cassert>
#include <iostream>
using SeamlessHunt::MapCache::Budget;
int main() {
    Budget b(100);
    assert(b.Record(8, 40).empty());
    assert(b.Record(16, 40).empty());
    assert(b.Touch(8));
    auto evicted = b.Record(24, 30);
    assert(evicted.size()==1 && evicted[0]==16);
    assert(b.Used()==70 && b.Size()==2);
    assert(!b.Touch(16));
    assert(b.Record(8, 50).empty());
    assert(b.Used()==80 && b.Size()==2);
    evicted = b.Record(32, 250);
    assert(evicted.size()==2 && evicted[0]==24 && evicted[1]==8);
    assert(b.Size()==1 && b.Used()==250 && b.Touch(32));
    evicted = b.Record(8, 1);
    assert(evicted.size()==1 && evicted[0]==32);
    assert(b.Used()==1 && b.Size()==1);
    std::cout << "PASS: bounded CPU map cache, recency, repeated inserts, oversized item\n";
}
