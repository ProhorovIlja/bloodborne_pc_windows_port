/* SPDX-License-Identifier: GPL-2.0-or-later */
#include "arena_check_v589.h"
#include "arena_seed_v577.h"
#include <cassert>
#include <cstdlib>
#include <memory>
#include <new>
extern "C" void *bb_engine_regular_heap_allocate_02485730(engine::regular_heap::Heap *,uint64_t);
int main() {
    using namespace engine::regular_heap;
    constexpr size_t n=BB_ARENA_SIZE_V577, a=BB_ARENA_ALIGN_V577;
    std::unique_ptr<void,decltype(&std::free)> raw(std::calloc(1,n+a),&std::free);
    void *p=raw.get(); size_t space=n+a;
    assert(p && std::align(a,n,p,space));
    alignas(Heap) unsigned char obj[BB_ARENA_OBJECT_V577]={};
    auto *h=new (obj+0x28) Heap{};
    auto *m=static_cast<unsigned char *>(p);
    assert(bb_arena_seed_v577(obj,sizeof obj,m,n,0));
    const uintptr_t base=address_of(m), end=base+n-32;
    auto check=[&](uintptr_t value) { return bb_arena_check_v589(h,value); };
    assert(!check(base).accepted && !check(base+17).accepted && !check(end+16).accepted);
    assert(check(base+16).accepted && !check(base+16).bad_word);
    bb_arena_qword_v577(m+8,2);
    assert(check(base+16).bad_word==base+8);
    bb_arena_qword_v577(m+8,end|2);
    bb_arena_qword_v577(m+n-32,0);
    assert(check(base+16).bad_word==end);
    bb_arena_qword_v577(m+n-32,base);
    bb_arena_qword_v577(m+16,1);
    assert(check(base+16).bad_word==base+16);
    assert(bb_arena_seed_v577(obj,sizeof obj,m,n,0));
    assert(bb_engine_regular_heap_allocate_02485730(h,24)==m+16);
    assert(!check(base+16).bad_word && !check(base+48).bad_word);
    bb_arena_qword_v577(m+40,end);
    assert(check(base+16).bad_word==base+40);
}
