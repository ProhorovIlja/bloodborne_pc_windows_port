// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V433: pure policy parity for original YT v1.4.0 server packet routing.
// The authoritative server uses packet_routes.h; this deterministic model
// shows the same COOP/HOSTILE channel, map and enemy-owner decisions.
// It is NOT network route authorization: no currently verified per-peer
// authenticated path, map assignment, instance or invader identity exists
// in BBHost's linked YT session. No send, recv, guest write or NetSync.
//
// Original server/coop/packet_routes.h (YT v1.4.0, blob
// f732c87cd0a030751f5ed23dfa225e98bb8ffc5c) is used as an oracle
// on every channel, all owner roles and both known/unknown/different maps.
#include "shyt_yt_native_channel_policy_v21.h"
#include <array>
#include <cstddef>
#include <cstdint>

namespace SeamlessHunt {
class YtGameRouteAssessmentV433 final {
public:
    enum class EnemyPart : std::uint8_t { None, Owner, Follower };
    enum class Relation : std::uint8_t { Teammate, HostileVisitor };
    struct Ends {
        std::uint32_t sender_map=0, target_map=0;
        EnemyPart sender=EnemyPart::None,target=EnemyPart::None;
    };
    struct Assessment {
        bool original_server_policy_would_pass=false;
        bool needs_reliable_drop_placeholder=false;
        bool can_forward_game=false;
        bool can_arm_game_queue=false;
    };
    static constexpr std::uint32_t DroppedNativeChannel=68u;
    static constexpr std::array<std::uint8_t,8> DroppedReliablePacket={
        static_cast<std::uint8_t>(DroppedNativeChannel),0,0,0,0,0,0,0};
    static constexpr bool CoOpPolicy(std::uint32_t channel,
                                     const Ends& e) noexcept {
        if(channel>=SHYT_YT_NATIVE_CHANNEL_COUNT_V21)return false;
        switch(shyt_yt_channel_policy_v21(channel)) {
        case SHYT_YT_CHANNEL_PASS_V21:return true;
        case SHYT_YT_CHANNEL_OURS_V21:
        case SHYT_YT_CHANNEL_DROP_V21:return false;
        case SHYT_YT_CHANNEL_SAME_MAP_V21:break;
        }
        // YT allows original game's traffic while a map is unknown.
        // This is source parity only, NOT evidence of an authorized path.
        if(e.sender_map && e.target_map && e.sender_map!=e.target_map)
            return false;
        if(channel==0x16u)
            return e.sender==EnemyPart::Follower &&
                   e.target==EnemyPart::Owner;
        if(channel==0x17u)
            return e.sender==EnemyPart::Owner &&
                   e.target==EnemyPart::Follower;
        if(channel==0x15u)
            return e.sender!=EnemyPart::Owner &&
                   e.target!=EnemyPart::Follower;
        if(channel==0x05u || channel==0x29u || channel==0x36u) {
            switch(e.target) {
            case EnemyPart::None:
                return e.sender!=EnemyPart::Follower;
            case EnemyPart::Follower:
                return e.sender==EnemyPart::Owner;
            case EnemyPart::Owner:
                return false;
            }
        }
        return true;
    }
    static constexpr bool HostilePolicy(std::uint32_t channel,
                                        const Ends& e,
                                        bool from_visitor) noexcept {
        if(channel>=SHYT_YT_NATIVE_CHANNEL_COUNT_V21)return false;
        bool same_map=e.sender_map!=0 && e.target_map!=0 &&
                      e.sender_map==e.target_map;
        switch(channel) {
        case 0x07u:case 0x19u:case 0x10u:case 0x11u:
        case 0x3fu:case 0x42u:
        case 0x08u:case 0x0au:case 0x0bu:case 0x0cu:
        case 0x0du:case 0x13u:case 0x3bu:case 0x3cu:
        case 0x43u:return true;
        case 0x06u:case 0x14u:case 0x12u:case 0x37u:
        case 0x30u:case 0x24u:case 0x25u:case 0x3eu:
        case 0x40u:return same_map;
        case 0x04u:case 0x05u:case 0x29u:case 0x36u:
        case 0x3du:case 0x41u:case 0x17u:
            return !from_visitor && same_map &&
                   e.sender==EnemyPart::Owner;
        case 0x15u:case 0x16u:case 0x34u:
        case 0x0eu:case 0x0fu:case 0x31u:
        case 0x2au:case 0x2bu:case 0x2du:case 0x2eu:
        case 0x2fu:case 0x2cu:case 0x27u:case 0x39u:
            return false;
        default:return shyt_yt_channel_policy_v21(channel)==
                       SHYT_YT_CHANNEL_PASS_V21;
        }
    }
    static constexpr Assessment Inspect(
        std::uint32_t channel,Relation relation,const Ends& e,
        bool from_visitor,bool reliable) noexcept {
        const bool policy=relation==Relation::Teammate?
            CoOpPolicy(channel,e):HostilePolicy(channel,e,from_visitor);
        return Assessment{policy,!policy && reliable,false,false};
    }
};
static_assert(YtGameRouteAssessmentV433::DroppedReliablePacket[0]==68u);
static_assert(!YtGameRouteAssessmentV433::Inspect(
    0x27u,YtGameRouteAssessmentV433::Relation::Teammate,{},false,
    true).can_forward_game);
} // namespace SeamlessHunt
