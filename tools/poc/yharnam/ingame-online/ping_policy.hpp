// SPDX-License-Identifier: GPL-2.0-or-later
// Native in-game ping policy: measure peers, NEVER substitute RTT to Fornex.
#pragma once
#include <algorithm>
#include <chrono>
#include <cmath>
#include <optional>
#include <vector>
namespace SeamlessHunt::InGame {
enum class PingPath { Any, DirectOnly, RelayOnly };
enum class PingQuality { Unmeasured, Excellent, Low, Moderate, High, VeryHigh };
struct PingSamples {
    std::vector<float> direct_ms,relay_ms;
    bool direct_verified=false,authenticated=false;
    std::chrono::steady_clock::time_point observed{};
};
struct PingFilter {
    std::optional<unsigned> maximum_ms;
    PingPath path=PingPath::Any;
    bool allow_relay_fallback=true,require_measured=false;
    std::chrono::seconds freshness{15};
};
struct PingDecision {
    bool matches=false;
    std::optional<float> measured_ms;
    PingPath path=PingPath::Any;
    PingQuality quality=PingQuality::Unmeasured;
};
inline std::optional<float> MedianRtt(const std::vector<float>& samples){
    std::vector<float> good;
    for(float s:samples)if(std::isfinite(s)&&s>0&&s<5000)good.push_back(s);
    if(good.size()<3)return std::nullopt;
    std::sort(good.begin(),good.end());
    const auto mid=good.size()/2;
    return good.size()%2?good[mid]:(good[mid-1]+good[mid])/2;
}
inline PingQuality QualityFor(float rtt){
    if(rtt<=35)return PingQuality::Excellent;
    if(rtt<=60)return PingQuality::Low;
    if(rtt<=100)return PingQuality::Moderate;
    if(rtt<=150)return PingQuality::High;
    return PingQuality::VeryHigh;
}
inline PingDecision MatchPing(const PingSamples& s,const PingFilter& filter,
                            std::chrono::steady_clock::time_point now){
    const bool fresh=s.authenticated && now>=s.observed && now-s.observed<=filter.freshness;
    const auto direct=fresh&&s.direct_verified?MedianRtt(s.direct_ms):std::nullopt;
    const auto relay=fresh?MedianRtt(s.relay_ms):std::nullopt;
    PingDecision result;
    if(filter.path==PingPath::RelayOnly){
        result.measured_ms=relay;result.path=PingPath::RelayOnly;
    }else if(direct){
        result.measured_ms=direct;result.path=PingPath::DirectOnly;
    }else if(filter.allow_relay_fallback&&relay){
        result.measured_ms=relay;result.path=PingPath::RelayOnly;
    }
    if(!result.measured_ms){
        result.matches=!filter.maximum_ms && !filter.require_measured;
        return result;
    }
    result.quality=QualityFor(*result.measured_ms);
    result.matches=!filter.maximum_ms || *result.measured_ms<=*filter.maximum_ms;
    return result;
}
} // namespace SeamlessHunt::InGame
