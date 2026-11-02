// SPDX-License-Identifier: GPL-2.0-or-later
// V321: exact transaction source, length, cookie and mapped endpoint.
// This unit does not authorize, probe or open any actual peer traffic.
#include "yt_reflexive_stun_v321.h"
#include <array>
#include <cassert>
#include <cstdio>
#include <cstring>
#include <vector>
using namespace BloodborneCoop::SHYTHybrid::ReflexiveStunV321;
static Endpoint Ep(std::array<u8,4> ip,std::array<u8,2> port) {
    Endpoint x{};
    std::memcpy(&x.address_nbo,ip.data(),4);
    std::memcpy(&x.port_nbo,port.data(),2);
    return x;
}
static std::vector<u8> Response(
    const std::array<u8,20>& req,std::array<u8,4> ip,
    std::array<u8,2> port)
{
    std::vector<u8> r(32);
    r[0]=1;r[1]=1;r[2]=0;r[3]=12;
    std::copy(req.begin()+4,req.end(),r.begin()+4);
    r[20]=0;r[21]=0x20;r[22]=0;r[23]=8;
    r[24]=0;r[25]=1;
    r[26]=port[0]^Binding::Cookie[0];
    r[27]=port[1]^Binding::Cookie[1];
    for(int i=0;i<4;++i) r[28+i]=ip[i]^Binding::Cookie[i];
    return r;
}
int main() {
    // V323: actual platform CSPRNG transaction IDs, no predictable
    // nonce or acceptance when system entropy is unavailable.
    std::array<u8,12> entropy_first{},entropy_second{};
    assert(FreshTransactionIdV323(entropy_first));
    assert(FreshTransactionIdV323(entropy_second));
    assert(entropy_first!=entropy_second);
    Binding binding{};
    const auto server=Ep({192,0,2,7},{13,150});
    const auto rogue=Ep({192,0,2,8},{13,150});
    const auto expected=Ep({198,51,100,18},{182,47});
    std::array<u8,12> id{};
    for(int i=0;i<12;++i)id[i]=static_cast<u8>(i+14);
    std::array<u8,12> zero{};
    assert(!binding.Start(server,zero,1000));
    assert(!binding.Start({},id,1000));
    assert(!binding.Start(server,id,-1));
    const auto req=binding.Start(server,id,1000);
    assert(req && binding.Pending(1000) && binding.Pending(3500));
    assert(!binding.Start(server,id,1200));
    assert((*req)[0]==0 && (*req)[1]==1);
    assert((*req)[2]==0 && (*req)[3]==0);
    assert(std::equal(Binding::Cookie.begin(),Binding::Cookie.end(),
                      req->begin()+4));
    auto r=Response(*req,{198,51,100,18},{182,47});
    assert(!binding.Take(rogue,r,1001));
    assert(!binding.Take(server,r,3501));
    assert(binding.Pending(3400));
    auto altered=r;altered[9]^=1;
    assert(!binding.Take(server,altered,2000));
    altered=r;altered[4]^=1;
    assert(!binding.Take(server,altered,2000));
    altered=r;altered[2]=1;
    assert(!binding.Take(server,altered,2000));
    altered=r;
    for(int i=0;i<4;++i)altered[28+i]=Binding::Cookie[i];
    assert(!binding.Take(server,altered,2000)); // zero mapped IPv4
    altered=r;altered[25]=2;
    assert(!binding.Take(server,altered,2000));
    altered=r;altered.resize(31);
    assert(!binding.Take(server,altered,2000));
    altered=r;altered.insert(altered.end(),r.begin()+20,r.end());
    altered[3]=24;
    assert(!binding.Take(server,altered,2000)); // duplicate mapped
    auto good=binding.Take(server,r,2000);
    assert(good && *good==expected);
    assert(!binding.Pending(2000));
    assert(!binding.Take(server,r,2001)); // replay
    const auto req2=binding.Start(server,id,9000);
    assert(req2);
    binding.Revoke();
    assert(!binding.Pending(9000));
    assert(!binding.Take(server,Response(*req2,{198,51,100,18},{182,47}),9001));
    std::puts("SHYT_V321_STUN_ADVISORY_CANDIDATE_NO_PEER_AUTH_PASS");
}
