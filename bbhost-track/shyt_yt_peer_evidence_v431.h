// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V431: bounded, READ-ONLY evidence for a remote online ID in the
// original YT v1.4.0 server-authenticated five-member TeamStart.
// This is NOT an identity certificate, authenticated endpoint, map/owner
// permission, P2P consent or a NetSync/GameLink send authorization.
//
// The V408 caller owns the *same* Noise-NK authenticated CoopStream for
// all evidence; never call this on untrusted external lobby JSON or on
// raw SHLK Member presence notices. The original party Welcome echoes
// no party ID. Correlation with one Hello + matched Snapshot is evidence
// of observed party progress, not cryptographic per-peer route consent.
#include "shyt_yt_team_authority_v414.h"
#include "shyt_yt_party_reply_v419.h"
#include "shyt_yt_world_staging_v425.h"
#include <cstdint>
#include <string>

namespace SeamlessHunt {
class YtPeerEvidenceV431 final {
public:
    struct Observation {
        bool roster_candidate=false;
        bool correlated_hello=false;
        bool matched_world_snapshot=false;
        bool ready_for_route=false; // must remain false until separate proof
        bool can_arm_game_queue=false; // no V430 production arm
        std::uint64_t observed_world_epoch=0;
        std::uint64_t observed_world_cursor=0;
    };
    // The caller MUST pass only a canonical authenticated TeamMember.member
    // (lowercase hex online-id) decoded from the original protobuf. Never
    // convert a display name to OnlineID or trust an unsigned peer endpoint.
    static Observation Inspect(const YtTeamAuthorityV414& gate,
                               const YtPartyReplyV419& reply,
                               const YtWorldStagingV425& world,
                               const std::string& canonical_member) {
        Observation o;
        o.roster_candidate=gate.PreparedPeerCandidate(canonical_member);
        if(!o.roster_candidate)return o;
        o.correlated_hello=reply.CandidateAwaitingSnapshot();
        o.matched_world_snapshot=o.correlated_hello && world.Active() &&
            world.Epoch()!=0u && world.PendingPackets()>0u;
        if(o.matched_world_snapshot) {
            o.observed_world_epoch=world.Epoch();
            o.observed_world_cursor=world.StagedCursor();
        }
        // A single server Noise-NK link and successful lobby snapshot do
        // NOT prove peer endpoint ownership, map/owner permissions or the
        // separate Party CoopStream identity. Therefore no route grant.
        return o;
    }
};
} // namespace SeamlessHunt
