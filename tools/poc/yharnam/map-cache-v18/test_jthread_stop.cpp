#ifdef NDEBUG
#undef NDEBUG
#endif
#include <thread>
#include <mutex>
#include <condition_variable>
#include <stop_token>
#include <atomic>
#include <cassert>
#include <iostream>
int main(){
  std::mutex mutex; std::condition_variable_any wake; std::atomic<bool> exited{false};
  {
    std::jthread worker([&](std::stop_token stop){
      std::unique_lock lock{mutex};
      if(!wake.wait(lock,stop, []{return false;})) exited.store(true);
    });
  }
  assert(exited.load());
  std::cout<<"PASS: stoppable worker exits from idle wait without explicit notify\n";
}
