// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
namespace SeamlessHunt::Perf {
struct Sample {
 std::int64_t timestamp_ms=0;
 unsigned map_id=0;
 float frame_ms=0;
 std::uint64_t process_bytes=0,image_bytes=0,live_images=0,gpu_bytes=0,gc_freed=0;
};
struct Trend {
 bool comparable=false,slowdown=false,process_growth=false,gpu_growth=false;
 float frame_percent=0;
 std::int64_t rss_mib_delta=0,gpu_mib_delta=0;
};
class Watch {
public:
 static constexpr unsigned Capacity=36;
 bool Add(Sample s){
  if(s.timestamp_ms<0||!std::isfinite(s.frame_ms)||s.frame_ms<=0||s.frame_ms>500)return false;
  if(size_&&s.timestamp_ms<Latest().timestamp_ms+10000)return false;
  samples_[next_]=s; next_=(next_+1)%Capacity;size_=std::min(size_+1,Capacity);return true;
 }
 const Sample& Latest() const{return samples_[(next_+Capacity-1)%Capacity];}
 unsigned Size() const{return size_;}
 Trend Compare() const{
  Trend result;
  if(size_<12)return result;
  const Sample& first=At(0);
  const Sample& last=Latest();
  if(first.map_id==0||first.map_id!=last.map_id||
     last.timestamp_ms-first.timestamp_ms<110000)return result;
  for(unsigned i=0;i<size_;++i)if(At(i).map_id!=first.map_id)return result;
  float early=0,late=0;
  constexpr unsigned group=4;
  for(unsigned i=0;i<group;++i){
    early+=At(i).frame_ms;late+=At(size_-group+i).frame_ms;
  }
  early/=group;late/=group;
  result.comparable=true;
  result.frame_percent=(late/early-1.0f)*100.0f;
  result.slowdown=result.frame_percent>25;
  result.rss_mib_delta=static_cast<std::int64_t>(last.process_bytes/1048576)-
                       static_cast<std::int64_t>(first.process_bytes/1048576);
  result.gpu_mib_delta=static_cast<std::int64_t>(last.gpu_bytes/1048576)-
                       static_cast<std::int64_t>(first.gpu_bytes/1048576);
  result.process_growth=result.rss_mib_delta>256;
  result.gpu_growth=result.gpu_mib_delta>256;
  return result;
 }
private:
 const Sample& At(unsigned i)const{return samples_[(next_+Capacity-size_+i)%Capacity];}
 std::array<Sample,Capacity> samples_{};
 unsigned next_=0,size_=0;
};
} // namespace SeamlessHunt::Perf
