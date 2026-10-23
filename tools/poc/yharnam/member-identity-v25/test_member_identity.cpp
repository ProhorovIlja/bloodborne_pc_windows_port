#ifdef NDEBUG
#undef NDEBUG
#endif
#include "sh_member_identity.hpp"
#include <cassert>
#include <iostream>
using SeamlessHunt::Identity::Admit;
using SeamlessHunt::Identity::Matches;
int main(){
    static_assert(Matches("hunter", "68756e746572"));
    static_assert(Matches("A", "41"));
    static_assert(!Matches("hunter","68756e746573"));
    static_assert(!Matches("hunter","68756E746572"));
    static_assert(!Matches("hunter","hunter"));
    static_assert(!Matches("",""));
    static_assert(Matches(std::string_view{"a\0b",3},"610062"));
    static_assert(!Admit(true,false,"hunter","68756e746572"));
    static_assert(!Admit(true,true,"hunter","abcd"));
    static_assert(Admit(true,true,"hunter","68756e746572"));
    static_assert(Admit(false,false,"old-client","anything"));
    assert(!Matches(std::string(49,'a'), std::string(98,'6')));
    std::cout<<"PASS: transport ID canonical binding, strict-auth fail closed, legacy compatibility\n";
}
