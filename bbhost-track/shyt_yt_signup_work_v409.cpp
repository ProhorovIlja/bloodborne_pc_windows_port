// SPDX-License-Identifier: GPL-2.0-or-later
// V409: real original YT SHA-256 work on a cancellable BACKGROUND thread.
// Not a custom PoW algorithm; links exactly pinned original link_auth.h.
// Does NOT open any network socket or capture owner account credentials.
#include "shyt_yt_signup_work_v409.h"
#include "coop/link_auth.h"
#include <algorithm>
#include <array>
#include <atomic>
#include <cstdint>
#include <new>
#include <string>
#include <thread>
#include <utility>

struct ShytYtSignupWorkV409 {
    LinkAuth::Cookie cookie{};
    std::string online_id;
    int bits=0;
    uint64_t budget=0;
    std::thread worker;
    std::atomic<bool> cancelled{false};
    // 0: running, 1: completed, -1: exhausted, -2: cancelled
    std::atomic<int> status{0};
    uint64_t nonce=0; // written before status release, read after acquire
};
namespace {
static constexpr uint64_t kMaxWork=uint64_t{1}<<29;
static constexpr uint64_t kBatch=4096u;
bool valid_online_id(const char *str) noexcept {
    if(!str)return false;
    for(size_t i=0;i<=255u;++i)
        if(str[i]=='\0')return i>0;
    return false;
}
void solve_work(ShytYtSignupWorkV409* w) noexcept {
    try {
        uint64_t start=0;
        while(start<w->budget) {
            if(w->cancelled.load(std::memory_order_relaxed)) {
                w->status.store(-2,std::memory_order_release);
                return;
            }
            const uint64_t size=std::min(kBatch,w->budget-start);
            const auto result=LinkAuth::SolveWork(
                w->cookie,w->online_id,w->bits,start,size);
            if(result) {
                w->nonce=*result;
                w->status.store(1,std::memory_order_release);
                return;
            }
            start+=size;
        }
        w->status.store(-1,std::memory_order_release);
    }catch(...) {
        w->status.store(-1,std::memory_order_release);
    }
}
}
extern "C" ShytYtSignupWorkV409* shyt_yt_work_start_v409(
    const uint8_t cookie[16],const char* online_id,
    int bits,uint64_t max_attempts) {
    // A server may demand up to 40 bits; a hostile/overloaded server must
    // never monopolize the user's machine indefinitely. Anything above
    // 28 is an explicit unsupported challenge, not a skipped challenge.
    if(!cookie || !valid_online_id(online_id) ||
       bits<1 || bits>28 || bits>LinkAuth::MaxWorkBits ||
       !max_attempts || max_attempts>kMaxWork)
        return nullptr;
    ShytYtSignupWorkV409* w=nullptr;
    try {
        w=new(std::nothrow) ShytYtSignupWorkV409{};
        if(!w)return nullptr;
        std::copy_n(cookie,w->cookie.size(),w->cookie.begin());
        w->online_id=online_id;
        w->bits=bits;
        w->budget=max_attempts;
        w->worker=std::thread([w](){solve_work(w);});
        return w;
    }catch(...) {
        delete w;
        return nullptr;
    }
}
extern "C" int shyt_yt_work_poll_v409(
    const ShytYtSignupWorkV409* w,uint64_t* nonce) {
    if(nonce)*nonce=0;
    if(!w || !nonce)return -1;
    const int state=w->status.load(std::memory_order_acquire);
    if(state==1)*nonce=w->nonce;
    return state;
}
extern "C" void shyt_yt_work_cancel_v409(ShytYtSignupWorkV409* w) {
    if(w)w->cancelled.store(true,std::memory_order_release);
}
extern "C" void shyt_yt_work_free_v409(ShytYtSignupWorkV409* w) {
    if(!w)return;
    shyt_yt_work_cancel_v409(w);
    if(w->worker.joinable())w->worker.join();
    std::fill(w->online_id.begin(),w->online_id.end(),'\0');
    delete w;
}
