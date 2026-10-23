#ifdef NDEBUG
#undef NDEBUG
#endif
#include "sh_hunter_tools_policy.hpp"
#include <cassert>
#include <cstdint>
#include <limits>
#include <iostream>
using namespace SeamlessHunt::HunterTools;

int main(){
    static_assert(!AllowLocalEdit(false,false,true));
    static_assert(!AllowLocalEdit(true,true,true));
    static_assert(!AllowLocalEdit(true,false,false));
    static_assert(AllowLocalEdit(true,false,true));
    constexpr std::int32_t original[]{10,10,10,10,10,10};
    constexpr std::int32_t increased[]{50,10,10,10,10,10};
    static_assert(LevelAfter(40,original,increased,6)==80);
    constexpr std::int32_t extreme[]{INT32_MAX,INT32_MAX,INT32_MAX,INT32_MAX,INT32_MAX,INT32_MAX};
    constexpr std::int32_t lowest[]{INT32_MIN,INT32_MIN,INT32_MIN,INT32_MIN,INT32_MIN,INT32_MIN};
    static_assert(LevelAfter(INT32_MAX,lowest,extreme,6)==544);
    static_assert(LevelAfter(INT32_MIN,extreme,lowest,6)==1);
    static_assert(LevelAfter(544,original,original,6)==544);
    std::cout<<"PASS: offline-only local editing policy; 64-bit safe level arithmetic\\n";
}
