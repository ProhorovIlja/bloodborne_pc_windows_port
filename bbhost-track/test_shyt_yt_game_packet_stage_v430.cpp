// SPDX-License-Identifier: GPL-3.0-or-later
#define SHYT_V430_SYNTHETIC_TEST_ONLY
#include "shyt_yt_game_packet_stage_v430.h"
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>
using Stage=SeamlessHunt::YtGamePacketStageV430;
using Bytes=std::vector<std::uint8_t>;
using Result=Stage::Result;
static void Put32(Bytes& b,std::uint32_t x) {
    for(unsigned i=0u;i<4u;++i) {
        b.push_back(static_cast<std::uint8_t>(x&255u));
        x>>=8u;
    }
}
static Bytes Game(std::uint32_t channel,std::size_t data_bytes) {
    Bytes bytes;
    bytes.reserve(8u+data_bytes);
    Put32(bytes,channel);
    Put32(bytes,static_cast<std::uint32_t>(data_bytes));
    for(std::size_t i=0u;i<data_bytes;++i)
        bytes.push_back(static_cast<std::uint8_t>(i&255u));
    return bytes;
}
int main() {
    Stage stage;
    const auto first=Game(0x06u,16u); // original YT player movement
    assert(stage.Stage(first,"peer-A",false)==Result::Closed);
    assert(!stage.ArmSynthetic(0u,"peer-A"));
    assert(!stage.ArmSynthetic(21u,""));
    assert(!stage.ArmSynthetic(21u,std::string(256u,'X')));
    assert(!stage.ArmSynthetic(21u,std::string("peer\0A",6)));
    assert(stage.ArmSynthetic(21u,"peer-A"));
    assert(!stage.ArmSynthetic(21u,"peer-A"));
    assert(stage.Pending()==0u && stage.Armed());
    assert(stage.Stage(first,"peer-B",false)==Result::UnboundMember);
    assert(stage.Stage(first,"peer-A",false)==Result::Accepted);
    const auto* first_packet=stage.Peek();
    assert(first_packet && first_packet->epoch==21u &&
           first_packet->generation!=0u &&
           first_packet->sequence==1u && first_packet->channel==6u &&
           first_packet->policy==SHYT_YT_CHANNEL_SAME_MAP_V21 &&
           !first_packet->reliable && first_packet->frame==first &&
           stage.BoundMember()=="peer-A");
    assert(stage.Pending()==1u && stage.BytesHeld()==first.size());
    // Original game frames are [LE32 channel][LE32 payload_len][payload].
    auto bad=first;bad[4u]^=1u;
    assert(stage.Stage(bad,"peer-A",true)==Result::BadFrame);
    assert(stage.Stage(Game(68u,3u),"peer-A",false)==Result::BadFrame);
    assert(stage.Stage(Bytes{1u,2u,3u},"peer-A",false)==Result::BadFrame);
    const auto max=Game(0x27u,0x6400u);
    assert(max.size()==Stage::MaxWire);
    assert(stage.Stage(max,"peer-A",true)==Result::Accepted);
    // The server's channel 0x27 drop policy is NOT authorization:
    // staged for quarantine only, not routed or emitted anywhere.
    assert(stage.Stats().accepted==2u &&
           stage.Stats().rejected_frame==3u);
    assert(stage.Pending()==2u && stage.BytesHeld()==first.size()+max.size());
    assert(!stage.Consume(20u,first_packet->generation,1u));
    assert(!stage.Consume(21u,first_packet->generation+1u,1u));
    assert(!stage.Consume(21u,first_packet->generation,2u));
    const auto generation=first_packet->generation;
    assert(stage.Consume(21u,generation,1u));
    assert(stage.Pending()==1u && stage.Peek()->sequence==2u);
    assert(stage.Peek()->reliable &&
           stage.Peek()->policy==SHYT_YT_CHANNEL_DROP_V21);
    assert(stage.Consume(21u,generation,2u));
    assert(stage.Pending()==0u && stage.BytesHeld()==0u &&
           stage.Stats().bytes_consumed==first.size()+max.size());

    // No loss of FIFO or original bytes under the 32-message budget.
    const auto small=Game(0x2cu,0u); // ours-policy not local P2P grant
    for(unsigned i=0;i<Stage::MaxHeld;++i)
        assert(stage.Stage(small,"peer-A",i%2u==0u)==Result::Accepted);
    assert(stage.Pending()==Stage::MaxHeld);
    assert(stage.Stage(small,"peer-A",false)==Result::Full);
    for(unsigned i=0;i<Stage::MaxHeld;++i) {
        const auto* packet=stage.Peek();
        assert(packet && packet->frame==small && packet->sequence==i+3u);
        assert(packet->policy==SHYT_YT_CHANNEL_OURS_V21);
        assert(packet->reliable==(i%2u==0u));
        assert(stage.Consume(21u,generation,packet->sequence));
    }
    assert(stage.Pending()==0u);

    // Huge frames may fit one-at-a-time but cannot exceed total 128 KiB.
    for(int i=0;i<5;++i)
        assert(stage.Stage(max,"peer-A",true)==Result::Accepted);
    assert(stage.Pending()==5u && stage.BytesHeld()==5u*max.size());
    assert(stage.Stage(max,"peer-A",true)==Result::Full);
    assert(stage.Pending()==5u && stage.BytesHeld()<=Stage::MaxTotalBytes);
    const auto previous_generation=stage.Generation();
    stage.Revoke();
    assert(!stage.Armed() && stage.Pending()==0u &&
           stage.BytesHeld()==0u &&
           stage.Generation()!=previous_generation);
    assert(stage.Stage(first,"peer-A",false)==Result::Closed);
    assert(stage.BoundMember().empty()); // zeroed when link revoked
    assert(!stage.ArmSynthetic(21u,"peer-A")); // no stale same-link rearm
    assert(stage.Stats().revoked==1u &&
           stage.Stats().rejected_full==2u &&
           stage.Stats().rejected_member==1u &&
           stage.Stats().rejected_closed==2u);
    std::puts("SHYT_V430_YT_NATIVE_GAME_PACKET_STAGE_FAIL_CLOSED_PASS");
}
