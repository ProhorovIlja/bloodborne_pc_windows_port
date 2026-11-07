// SPDX-License-Identifier: GPL-3.0-or-later
// COMPILE THIS WITHOUT SHYT_V430_SYNTHETIC_TEST_ONLY: no authorizer is
// exposed to a compiled production BBHost plugin until server binding.
#include "shyt_yt_game_packet_stage_v430.h"
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>
using Stage=SeamlessHunt::YtGamePacketStageV430;
template<typename T>
concept HasSyntheticArm=requires(T& t) {
    t.ArmSynthetic(77u,std::string("peer"));
};
static_assert(!HasSyntheticArm<Stage>,
    "An unverified party must never arm outgoing gameplay staging");
int main() {
    Stage stage;
    const std::vector<std::uint8_t> frame={6u,0u,0u,0u,0u,0u,0u,0u};
    assert(stage.Stage(frame,"peer",false)==Stage::Result::Closed);
    assert(stage.Pending()==0u && stage.BytesHeld()==0u &&
           !stage.Peek() && !stage.Armed());
    stage.Revoke();
    assert(stage.Pending()==0u && !stage.Peek());
    std::puts("SHYT_V430_PRODUCTION_GAME_STAGING_NEVER_ARMABLE_PASS");
}
