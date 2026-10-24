#ifdef NDEBUG
#undef NDEBUG
#endif
#include "sh_endpoint_rebind.hpp"
#include <cassert>
#include <string_view>
#include <iostream>
using SeamlessHunt::LinkRebind::MustRetire;
int main() {
    static_assert(!MustRetire(false,std::string_view{"hunterA"},std::string_view{"hunterB"}));
    static_assert(!MustRetire(true,std::string_view{"hunterA"},std::string_view{"hunterA"}));
    static_assert(MustRetire(true,std::string_view{"hunterA"},std::string_view{"hunterB"}));
    assert(MustRetire(true,std::string_view{"alive"},std::string_view{""}));
    std::cout<<"PASS: same identity reconnect preserved, changed identity retires routes\n";
}
