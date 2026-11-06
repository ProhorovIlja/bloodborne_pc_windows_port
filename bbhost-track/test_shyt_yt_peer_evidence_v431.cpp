// SPDX-License-Identifier: GPL-2.0-or-later
#include "shyt_yt_peer_evidence_v431.h"
#include <cassert>
#include <cstdio>
#include <cstdint>
#include <vector>

using Gate=SeamlessHunt::YtTeamAuthorityV414;
using Reply=SeamlessHunt::YtPartyReplyV419;
using Stage=SeamlessHunt::YtWorldStagingV425;
using Fence=SeamlessHunt::YtPeerEvidenceV431;
int main() {
    const std::string local="616c696365"; // hex("alice")
    const std::string peer="626f62"; // hex("bob")
    Gate gate(local);
    Reply reply;
    Stage stage;
    Gate::Lobby lobby;
    lobby.team="team";
    lobby.leader=local;
    lobby.world="realm";
    lobby.party="world:realm";
    lobby.started=true;
    lobby.members={{local,0u,1u,true},{peer,4u,2u,true}};
    const Gate::Start start={"team","world:realm",local,"realm",1u};
    auto obs=Fence::Inspect(gate,reply,stage,peer);
    assert(!obs.roster_candidate && !obs.ready_for_route);
    assert(gate.OnAuthenticatedLobby(lobby));
    assert(!gate.PreparedPeerCandidate(peer)); // no trusted TeamStart
    assert(gate.OnAuthenticatedTeamStart(start));
    assert(gate.PreparedPeerCandidate(peer));
    assert(!gate.PreparedPeerCandidate(local)); // no self P2P
    assert(!gate.PreparedPeerCandidate("6e6f7065")); // unknown
    assert(!gate.PreparedPeerCandidate("bob")); // display name != server ID
    obs=Fence::Inspect(gate,reply,stage,peer);
    assert(obs.roster_candidate && !obs.correlated_hello &&
           !obs.matched_world_snapshot && !obs.ready_for_route &&
           !obs.can_arm_game_queue);
    assert(reply.Arm("world:realm",1u,123u,1000u));
    obs=Fence::Inspect(gate,reply,stage,peer);
    assert(obs.roster_candidate && !obs.correlated_hello);
    assert(reply.OnAuthenticatedWelcome(true,1001u,true)==
           Reply::Reply::CorrelatedCandidate);
    obs=Fence::Inspect(gate,reply,stage,peer);
    assert(obs.roster_candidate && obs.correlated_hello &&
           !obs.matched_world_snapshot && !obs.can_arm_game_queue);
    // Original generated protobuf: Envelope.snapshot=7,
    // Snapshot.epoch=1 and Snapshot.last=2, both varints.
    const std::vector<std::uint8_t> snapshot{
        0x3au,0x04u,0x08u,0x4du,0x10u,0x09u
    };
    assert(stage.StageSnapshot(snapshot,77u,9u));
    obs=Fence::Inspect(gate,reply,stage,peer);
    assert(obs.roster_candidate && obs.correlated_hello &&
           obs.matched_world_snapshot && obs.observed_world_epoch==77u &&
           obs.observed_world_cursor==9u &&
           !obs.ready_for_route && !obs.can_arm_game_queue);
    assert(!Fence::Inspect(gate,reply,stage,local).roster_candidate);
    assert(!Fence::Inspect(gate,reply,stage,"626f63").roster_candidate);
    // A changed MAC-authenticated roster removes the previously known
    // peer; even with stale reply and Snapshot evidence, it cannot match.
    auto changed=lobby;
    changed.members[1].id="6361726f6c"; // hex("carol")
    assert(gate.OnAuthenticatedLobby(changed));
    assert(!Fence::Inspect(gate,reply,stage,peer).roster_candidate);
    assert(gate.OnAuthenticatedTeamStart(start));
    assert(!Fence::Inspect(gate,reply,stage,peer).roster_candidate);
    // Change of party reply or world snapshot revokes the other
    // evidence. Neither can ever independently grant traffic.
    reply.Revoke();
    obs=Fence::Inspect(gate,reply,stage,"6361726f6c");
    assert(obs.roster_candidate && !obs.correlated_hello &&
           !obs.matched_world_snapshot);
    stage.Revoke();
    obs=Fence::Inspect(gate,reply,stage,"6361726f6c");
    assert(obs.observed_world_epoch==0u && !obs.ready_for_route);
    gate.Revoke();
    assert(!Fence::Inspect(gate,reply,stage,"6361726f6c").roster_candidate);
    std::puts("SHYT_V431_AUTHENTICATED_ROSTER_EVIDENCE_READ_ONLY_PASS");
}
