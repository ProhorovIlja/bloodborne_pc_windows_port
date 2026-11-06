// SPDX-License-Identifier: GPL-2.0-or-later
// Synthetic-only, no game bytes or real server. Validates original YT v1.4
// Team / TeamMember / LobbyState / TeamStart / party Welcome field semantics.
#include "shyt_yt_team_authority_v414.h"
#include <cassert>
#include <cstdio>
#include <utility>

using Gate = SeamlessHunt::YtTeamAuthorityV414;
static Gate::Lobby Five() {
    return {"t-17", "hunter1", "level-44", "world:level-44", true, {
        {"hunter1", 0, 1, true},
        {"hunter2", 7, 2, true},
        {"hunter3", 6, 3, true},
        {"hunter4", 5, 4, true},
        {"hunter5", 4, 5, true}
    }};
}
int main() {
    Gate gate("hunter5");
    const auto five = Five();
    const Gate::Start start{"t-17","world:level-44","hunter1","level-44",5};
    assert(!gate.Authorized());
    assert(!gate.IsTeamMember("hunter2"));
    // A server link or team start alone cannot authorize a world.
    assert(!gate.OnAuthenticatedTeamStart(start));
    assert(!gate.Authorized());
    assert(gate.OnAuthenticatedLobby(five));
    assert(!gate.Authorized());
    assert(gate.OnAuthenticatedTeamStart(start));
    assert(!gate.Authorized());
    assert(!gate.OnAuthenticatedPartyWelcome("unrelated-world",true,21,0));
    assert(!gate.Authorized()); // wrong stream destroyed previous grant context
    assert(gate.OnAuthenticatedLobby(five));
    assert(gate.OnAuthenticatedTeamStart(start));
    assert(!gate.OnAuthenticatedPartyWelcome("world:level-44",false,21,0));
    assert(gate.OnAuthenticatedLobby(five));
    assert(gate.OnAuthenticatedTeamStart(start));
    assert(gate.OnAuthenticatedPartyWelcome("world:level-44",true,21,0));
    assert(gate.Authorized());
    assert(gate.IsTeamMember("hunter1") && gate.IsTeamMember("hunter5"));
    assert(!gate.IsTeamMember("intruder"));
    auto view = gate.Snapshot();
    assert(view.team=="t-17" && view.host=="hunter1");
    assert(view.members.size()==5 && view.epoch==21 && view.last==0);
    assert(gate.OnAuthenticatedPartyWelcome("world:level-44",true,21,7));
    assert(gate.Authorized() && gate.Snapshot().last==7);
    // Incoming LobbyState member order is not security-relevant.
    auto reordered=five;
    std::swap(reordered.members[0],reordered.members[4]);
    assert(gate.OnAuthenticatedLobby(reordered));
    assert(gate.Authorized());
    // A host may become another already-authorized teammate on migration,
    // but only after a fresh TeamStart and the party's own Welcome.
    const Gate::Start moved{"t-17","world:level-44","hunter2","level-44",5};
    assert(gate.OnAuthenticatedTeamStart(moved));
    assert(!gate.Authorized());
    assert(gate.OnAuthenticatedPartyWelcome("world:level-44",true,21,8));
    assert(gate.Authorized() && gate.Snapshot().host=="hunter2");
    // Replay or older world log position revokes authorization.
    assert(!gate.OnAuthenticatedPartyWelcome("world:level-44",true,21,7));
    assert(!gate.Authorized());
    // Member departure / sign reassignment / save slot changes revoke.
    assert(gate.OnAuthenticatedLobby(five));
    assert(gate.OnAuthenticatedTeamStart(start));
    assert(gate.OnAuthenticatedPartyWelcome("world:level-44",true,50,9));
    auto changed=five;
    changed.members.pop_back();
    assert(!gate.OnAuthenticatedLobby(changed)); // local player no longer in team
    assert(!gate.Authorized());
    assert(gate.OnAuthenticatedLobby(five));
    assert(gate.OnAuthenticatedTeamStart(start));
    assert(gate.OnAuthenticatedPartyWelcome("world:level-44",true,50,9));
    changed=five;
    changed.members[1].sign=5; // duplicates hunter4
    assert(!gate.OnAuthenticatedLobby(changed));
    assert(!gate.Authorized());
    changed=five;
    changed.members[4].slot=6;
    assert(gate.OnAuthenticatedLobby(changed));
    assert(!gate.Authorized());
    assert(!gate.OnAuthenticatedTeamStart(start)); // wrong saved slot
    // No sixth player (even if every sign otherwise looks plausible).
    changed=five;
    changed.members.push_back({"hunter6",7,6,true});
    assert(!gate.OnAuthenticatedLobby(changed));
    // A malformed party key can never be used as authority.
    changed=five;
    changed.party="world:../../other";
    assert(!gate.OnAuthenticatedLobby(changed));
    // An unstarted team never gets gameplay permission.
    changed=five;
    changed.started=false;
    changed.party.clear();
    changed.world.clear();
    assert(gate.OnAuthenticatedLobby(changed));
    assert(!gate.OnAuthenticatedTeamStart(start));
    // The same team id in another world cannot inherit an old grant.
    assert(gate.OnAuthenticatedLobby(five));
    assert(gate.OnAuthenticatedTeamStart(start));
    assert(gate.OnAuthenticatedPartyWelcome("world:level-44",true,60,0));
    changed=five;
    changed.world="level-45";
    changed.party="world:level-45";
    assert(gate.OnAuthenticatedLobby(changed));
    assert(!gate.Authorized());
    gate.Revoke();
    gate.Revoke();
    assert(!gate.Authorized());
    assert(gate.Snapshot().members.empty());
    Gate invalid("bad\nidentity");
    assert(!invalid.OnAuthenticatedLobby(five));
    std::puts("SHYT_V414_SOURCE_PINNED_FIVE_PLAYER_TEAM_WORLD_AUTHORITY_PASS");
}
