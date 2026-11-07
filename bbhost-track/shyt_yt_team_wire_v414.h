// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// Original YT Envelope -> V414 authorization state. This adapter MUST run
// only after SHLK4/Noise-NK server MAC+replay validation, original CoopStream
// ordering/reassembly and explicit binding to either the lobby stream or the
// party stream established by a prior verified TeamStart. No P2P addresses,
// NetSync hooks, save data or game-memory writes are authorized here.
//
// The .proto is generated from pinned original YT by protoc at build time.
// Never hand-roll field numbers or accept caller-built "trusted" envelopes.
#include "shyt_yt_team_authority_v414.h"
#include "coop.pb.h"
#include <cstddef>
#include <cstdint>
#include <span>
#include <string>
#include <vector>

namespace SeamlessHunt {
class YtTeamWireV414 final {
public:
    enum class Scope { Lobby, Party };
    enum class Result { Ignored, Accepted, Revoked };
    static constexpr std::size_t MaxEnvelopeBytes = 64u * 1024u;

    static Result FeedAfterVerifiedServerAuth(
        YtTeamAuthorityV414& gate, Scope scope,
        const std::string& authenticated_party_stream_identity,
        std::span<const std::uint8_t> wire) {
        static_assert(bbcoop::PROTOCOL_CURRENT == YtTeamAuthorityV414::Protocol,
                      "YT Coop protocol changed; update BBHost admission rules");
        if (wire.empty() || wire.size() > MaxEnvelopeBytes) {
            gate.Revoke();
            return Result::Revoked;
        }
        bbcoop::Envelope envelope;
        if (!envelope.ParseFromArray(wire.data(), static_cast<int>(wire.size()))) {
            gate.Revoke();
            return Result::Revoked;
        }
        if (scope == Scope::Lobby && envelope.has_lobby_state()) {
            const auto& message = envelope.lobby_state();
            if (!message.has_team()) {
                gate.Revoke();
                return Result::Revoked;
            }
            const auto& team = message.team();
            if (team.members_size() < 1 ||
                team.members_size() > static_cast<int>(YtTeamAuthorityV414::MaxTeam)) {
                gate.Revoke();
                return Result::Revoked;
            }
            YtTeamAuthorityV414::Lobby lobby;
            lobby.team=team.id();
            lobby.leader=team.leader();
            lobby.world=team.world();
            lobby.party=team.party();
            lobby.started=team.started();
            for (const auto& member : team.members()) {
                lobby.members.push_back({member.member(),member.sign(),
                                         member.slot(),member.ready()});
            }
            return gate.OnAuthenticatedLobby(std::move(lobby)) ?
                   Result::Accepted : Result::Revoked;
        }
        if (scope == Scope::Lobby && envelope.has_team_start()) {
            const auto& start = envelope.team_start();
            YtTeamAuthorityV414::Start view{
                start.team(), start.party(), start.host(), start.world(), start.slot()};
            return gate.OnAuthenticatedTeamStart(view) ?
                   Result::Accepted : Result::Revoked;
        }
        if (scope == Scope::Party && envelope.has_welcome()) {
            const auto& welcome = envelope.welcome();
            return gate.OnAuthenticatedPartyWelcome(
                       authenticated_party_stream_identity, welcome.accepted(),
                       welcome.epoch(), welcome.last()) ?
                   Result::Accepted : Result::Revoked;
        }
        // An unrelated world board is not a team-authority message. It stays
        // quarantined for a future separately authorized gameplay decoder.
        return Result::Ignored;
    }
};
} // namespace SeamlessHunt
