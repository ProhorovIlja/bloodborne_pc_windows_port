// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V283: SERVER-SIDE ONLY membership eligibility check before the V279
// EdDSA grant issuer is allowed to sign ANY peer pair. The interface
// uses exact generated bbcoop::Team / TeamMember accessor names from
// original YT 1.3.1 server/coop/coop.proto (id(), party(), started(),
// members_size(), members(i).member(), members(i).state()).
//
// Team size MUST be passed from the running authoritative shadNet
// TeamSize setting (4 in official YT v1.3.1; 5 only after complete
// official team-5 server/client/invasion changes). No client flags or
// UDP peer messages may be used as this server-side source of truth.
//
// This does not mint a server signing key, grant original game
// instance/map attestations or add the grant to an authenticated
// shadNet Coop response: those production integrations are separate.
#include "yt_signed_peer_grant_v279.h"
#include <cstddef>
#include <optional>
#include <string>
#include <string_view>

namespace BloodborneCoop::SHYTHybrid::ServerTeamIssuerV283 {

// Original bbcoop::LobbyPlayer.State PLAYING enum value is 2.
// The generated protoc C++ accessor returns the same integer value.
// Only currently PLAYING team members are eligible, not TITLE/OFFLINE.
inline constexpr int PlayingState=2;

template <typename Team>
bool Eligible(const Team& authoritative_team,
              const SignedPeerGrantV279::Scope& requested,
              std::string_view authenticated_link_member,
              std::size_t actual_server_team_limit)
{
    if (!SignedPeerGrantV279::Valid(requested) ||
        actual_server_team_limit<2 || actual_server_team_limit>5 ||
        !authoritative_team.started() ||
        authoritative_team.id()!=requested.team ||
        authoritative_team.party()!=requested.party ||
        authenticated_link_member!=requested.sender ||
        authoritative_team.members_size()<2 ||
        static_cast<std::size_t>(authoritative_team.members_size())>
            actual_server_team_limit)
        return false;
    bool sender=false, receiver=false;
    for (int i=0;i<authoritative_team.members_size();++i) {
        const auto& member=authoritative_team.members(i);
        if (member.member()==requested.sender) {
            // Duplicate member IDs are invalid even if both are playing.
            if (sender || static_cast<int>(member.state())!=PlayingState)
                return false;
            sender=true;
        }
        if (member.member()==requested.receiver) {
            if (receiver || static_cast<int>(member.state())!=PlayingState)
                return false;
            receiver=true;
        }
    }
    return sender && receiver;
}

template <typename Team>
std::optional<SignedPeerGrantV279::Signed> Issue(
    const Team& authoritative_team,
    const SignedPeerGrantV279::Scope& server_scoped_grant,
    std::string_view authenticated_link_member,
    std::size_t actual_server_team_limit,
    const SignedPeerGrantV279::SecretKey& server_only_eddsa_secret)
{
    if (!Eligible(authoritative_team,server_scoped_grant,
                  authenticated_link_member,actual_server_team_limit))
        return std::nullopt;
    return SignedPeerGrantV279::Sign(server_scoped_grant,
                                    server_only_eddsa_secret);
}
// V296: original TeamLobby::TeamOf() returns the *canonical* team,
// whose TeamMember.state is intentionally stale/default. The original
// TeamLobby::StateFor() creates a server-authored VIEW with current
// PLAYING/TITLE/OFFLINE status. Issuers must use that fresh view, not
// canonical TeamOf or a client-supplied LobbyState.
template <typename TeamLobby>
std::optional<SignedPeerGrantV279::Signed> IssueFromLiveLobby(
    const TeamLobby& authoritative_lobby,
    const SignedPeerGrantV279::Scope& server_derived_grant,
    std::string_view authenticated_link_member,
    std::size_t actual_team_limit,
    const SignedPeerGrantV279::SecretKey& server_only_eddsa_secret)
{
    const std::string link_member{authenticated_link_member};
    const auto* canonical=authoritative_lobby.TeamOf(link_member);
    if(!canonical) return std::nullopt;
    const auto view=authoritative_lobby.StateFor(link_member);
    if(!view.has_team() || view.team().id()!=canonical->id() ||
       view.team().party()!=canonical->party() ||
       view.team().members_size()!=canonical->members_size())
        return std::nullopt;
    return Issue(view.team(),server_derived_grant,authenticated_link_member,
                 actual_team_limit,server_only_eddsa_secret);
}

} // namespace BloodborneCoop::SHYTHybrid::ServerTeamIssuerV283
