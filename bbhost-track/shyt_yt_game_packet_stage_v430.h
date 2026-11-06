// SPDX-License-Identifier: GPL-3.0-or-later
#pragma once
// V430: bounded candidate queue for ORIGINAL YT v1.4.0 game packets.
// This does not install hooks, capture guest memory, forward datagrams,
// grant NetSync permissions, or serialize authoritatively. Production
// cannot arm this queue yet: actual authenticated party->member identity
// binding is missing and MUST be supplied by ShadNet/CoopStream first.
//
// Original TakeGamePacket receives {rcx=packet, rdx=member, (u32)rsi=
// reliable, (u32)r8=size}, and frame bytes are {u32 LE channel,
// u32 LE payload_size, payload[payload_size]}. Source: released YT 1.4.0.
// The server's route/membership/owner rules are separate: the channel
// policy here is OBSERVATION ONLY, never proof of direct-P2P authority.
#include "shyt_yt_native_channel_policy_v21.h"
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <span>
#include <string>
#include <utility>
#include <vector>

namespace SeamlessHunt {
class YtGamePacketStageV430 final {
public:
    static constexpr std::size_t MaxWire=0x6408u;
    static constexpr std::size_t MaxHeld=32u;
    static constexpr std::size_t MaxTotalBytes=128u*1024u;
    static constexpr std::size_t MaxOnlineId=255u;
    enum class Result : std::uint8_t {
        Accepted, Closed, UnboundMember, BadFrame, Full
    };
    struct Packet {
        std::vector<std::uint8_t> frame; // exact immutable YT native bytes
        std::uint64_t epoch=0, generation=0, sequence=0;
        std::uint32_t channel=0;
        bool reliable=false;
        ShytYtNativeChannelPolicyV21 policy=SHYT_YT_CHANNEL_DROP_V21;
    };
    struct Counters {
        std::uint64_t accepted=0, rejected_closed=0, rejected_member=0;
        std::uint64_t rejected_frame=0, rejected_full=0;
        std::uint64_t bytes_staged=0, bytes_consumed=0;
        std::uint64_t revoked=0;
    };
    Result Stage(std::span<const std::uint8_t> frame,
                 const std::string& original_online_id,
                 bool reliable) {
        if(!armed_) {
            ++stats_.rejected_closed;
            return Result::Closed;
        }
        if(!IsOnlineId(original_online_id) ||
           original_online_id!=member_) {
            ++stats_.rejected_member;
            return Result::UnboundMember;
        }
        // Read only the frame's own header after bounding length. No
        // dereferencing of game pointers, no high-bit channel truncation.
        if(frame.size()<8u || frame.size()>MaxWire) {
            ++stats_.rejected_frame;
            return Result::BadFrame;
        }
        const auto channel=Le32(frame.data());
        const auto payload_size=Le32(frame.data()+4u);
        if(channel>=SHYT_YT_NATIVE_CHANNEL_COUNT_V21 ||
           payload_size!=frame.size()-8u) {
            ++stats_.rejected_frame;
            return Result::BadFrame;
        }
        // Even channel 0x27 (Drop) remains quarantined rather than
        // being interpreted as local authority. The later server/peer
        // routing layer must make a separate explicit routing decision.
        if(packets_.size()>=MaxHeld ||
           frame.size()>MaxTotalBytes-held_bytes_) {
            ++stats_.rejected_full;
            return Result::Full; // no silent reliable packet eviction
        }
        // Advance only after successfully storing the complete bytes.
        Packet candidate;
        candidate.frame.assign(frame.begin(),frame.end());
        candidate.epoch=epoch_;
        candidate.generation=generation_;
        candidate.sequence=next_sequence_;
        candidate.channel=channel;
        candidate.reliable=reliable;
        candidate.policy=shyt_yt_channel_policy_v21(channel);
        packets_.push_back(std::move(candidate));
        held_bytes_+=frame.size();
        ++next_sequence_;
        ++stats_.accepted;
        stats_.bytes_staged+=frame.size();
        return Result::Accepted;
    }

    // Read-only peek. No socket send, guest fill, or extraction as proof
    // of room authority. A future authenticated consumer must verify
    // context again immediately before transmission.
    const Packet* Peek() const noexcept {
        if(!armed_ || packets_.empty())return nullptr;
        return &packets_.front();
    }
    bool Consume(std::uint64_t epoch,std::uint64_t generation,
                 std::uint64_t sequence) noexcept {
        const Packet* front=Peek();
        if(!front || epoch!=epoch_ || generation!=generation_ ||
           front->sequence!=sequence)return false;
        const auto size=front->frame.size();
        Wipe(packets_.front().frame);
        packets_.pop_front();
        held_bytes_-=size;
        stats_.bytes_consumed+=size;
        return true;
    }
    void Revoke() noexcept {
        if(armed_)++stats_.revoked;
        armed_=false;epoch_=0;
        member_.assign(member_.size(),'\0');
        member_.clear();
        for(auto& packet:packets_) {
            Wipe(packet.frame);
        }
        packets_.clear();held_bytes_=0;
        if(generation_!=UINT64_MAX)++generation_;
    }
    bool Armed() const noexcept {return armed_;}
    std::size_t Pending() const noexcept{return packets_.size();}
    std::size_t BytesHeld() const noexcept{return held_bytes_;}
    // Store one authenticated member binding per queue, not one repeated
    // heap-allocated OnlineID for every game packet (up to 32 copies).
    const std::string& BoundMember() const noexcept{return member_;}
    Counters Stats() const noexcept{return stats_;}
    std::uint64_t Generation() const noexcept{return generation_;}
private:
    static bool IsOnlineId(const std::string& value) noexcept {
        if(value.empty() || value.size()>MaxOnlineId)return false;
        for(const char ch:value)if(ch=='\0')return false;
        return true;
    }
    static std::uint32_t Le32(const std::uint8_t* p) noexcept {
        return static_cast<std::uint32_t>(p[0])|
               (static_cast<std::uint32_t>(p[1])<<8u)|
               (static_cast<std::uint32_t>(p[2])<<16u)|
               (static_cast<std::uint32_t>(p[3])<<24u);
    }
    static void Wipe(std::vector<std::uint8_t>& b) noexcept {
        std::fill(b.begin(),b.end(),std::uint8_t{0});
        b.clear();
    }
    // NEVER expose a free-form production Arm(bool), since the original
    // server's authenticated team-member/peer binding is not yet
    // connected. Fixture-only admission makes this stage testable but
    // unarmable by any distributed production plugin.
#ifdef SHYT_V430_SYNTHETIC_TEST_ONLY
public:
    bool ArmSynthetic(std::uint64_t epoch,std::string member) {
        if(armed_ || was_armed_ || epoch==0u || !IsOnlineId(member))
            return false;
        member_=std::move(member);
        epoch_=epoch;
        armed_=was_armed_=true;
        if(generation_==0u)generation_=1u;
        return true;
    }
private:
#endif
    std::deque<Packet> packets_{};
    Counters stats_{};
    std::string member_{};
    std::size_t held_bytes_=0;
    std::uint64_t epoch_=0,generation_=0,next_sequence_=1u;
    bool armed_=false,was_armed_=false;
};
} // namespace SeamlessHunt
