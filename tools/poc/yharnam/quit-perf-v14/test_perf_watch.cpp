#ifdef NDEBUG
#undef NDEBUG
#endif
#include "perf_watch.hpp"
#include <cassert>
#include <iostream>
#include <limits>
using namespace SeamlessHunt::Perf;
int main(){
 Watch w;
 for(int i=0;i<20;++i){
  Sample s;s.timestamp_ms=i*10000;s.map_id=123;
  s.frame_ms=16.6f+(i>8?float(i-8)*0.8f:0);
  s.process_bytes=(200ull+i*30)*1048576;
  s.gpu_bytes=(600ull+i*20)*1048576;
  assert(w.Add(s));assert(!w.Add(s));
 }
 auto t=w.Compare();assert(t.comparable&&t.slowdown&&t.process_growth&&t.gpu_growth);
 assert(t.rss_mib_delta==570);
 Watch changed;
 for(int i=0;i<15;++i){Sample s;s.timestamp_ms=i*10000;s.map_id=(i<5?1:2);s.frame_ms=16;assert(changed.Add(s));}
 assert(changed.Size()==10 && !changed.Compare().comparable);
 for(int i=15;i<18;++i){Sample s;s.timestamp_ms=i*10000;s.map_id=2;s.frame_ms=16;assert(changed.Add(s));}
 assert(changed.Size()==13 && changed.Compare().comparable);
 Watch stable;
 for(int i=0;i<15;++i){Sample s;s.timestamp_ms=i*10000;s.map_id=1;s.frame_ms=16.7f;
  s.process_bytes=1ull<<30;s.gpu_bytes=1ull<<30;assert(stable.Add(s));}
 assert(stable.Compare().comparable&&!stable.Compare().slowdown&&!stable.Compare().process_growth);
 Sample bad;bad.timestamp_ms=200000;bad.frame_ms=std::numeric_limits<float>::quiet_NaN();
 assert(!stable.Add(bad));
 Watch ring;
 for(int i=0;i<70;++i){Sample s;s.timestamp_ms=i*10000;s.map_id=7;s.frame_ms=17;assert(ring.Add(s));}
 assert(ring.Size()==Watch::Capacity&&ring.Latest().timestamp_ms==690000);
 Sample gap;gap.timestamp_ms=810000;gap.map_id=7;gap.frame_ms=17;
 assert(ring.Add(gap));assert(ring.Size()==1);assert(!ring.Compare().comparable);
 Sample reversed=gap;reversed.timestamp_ms=809000;
 assert(!ring.Add(reversed));assert(ring.Size()==1);
 ring.Clear();assert(ring.Size()==0);
 std::cout<<"PASS: bounded performance history, drift detection, map change, sample validation\n";
}
