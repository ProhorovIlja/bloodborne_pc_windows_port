// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V414: conservative team/world authority state gate for the BBHost bridge.
// Inputs MUST be decoded from the exact original bbcoop::Envelope schemas,
// on the correct server-authenticated lobby or party CoopStream. This gate
// does NOT decode protobufs, establish a Noise session, authorize a bare
// UDP endpoint, or permit game-memory writes. In particular a SHLK Member
// notice is NOT a lobby membership grant.
#include <algorithm>
#include <cstdint>
#include <set>
#include <string>
#include <utility>
#include <vector>

namespace SeamlessHunt {
class YtTeamAuthorityV414 final {
public:
    static constexpr std::uint32_t Protocol = 8; // pinned YT v1.3.1 and v1.4.0
    static constexpr std::size_t MaxTeam = 5;
    struct Member {
        std::string id;  // original TeamMember.member, NOT display name
        std::uint32_t sign = 0;
        std::uint32_t slot = 0;
        bool ready = false;
        bool operator==(const Member&) const = default;
    };
    struct Lobby {
        std::string team, leader, world, party;
        bool started = false;
        std::vector<Member> members;
        bool operator==(const Lobby&) const = default;
    };
    struct Start {
        std::string team, party, host, world;
        std::uint32_t slot = 0;
        bool operator==(const Start&) const = default;
    };
    struct World {
        std::string team, party, world, host;
        std::uint64_t epoch = 0, last = 0;
        std::vector<Member> members;
    };
    explicit YtTeamAuthorityV414(std::string local_id)
        : local_id_(std::move(local_id)), identity_valid_(Identifier(local_id_)) {}
    // Idempotent; call upon link loss, reconnect, stream overflow, game
    // reload, changed save or party-stream restart. No silent auto-rejoin.
    void Revoke() noexcept {
        lobby_ = {};
        start_ = {};
        have_lobby_ = false;
        have_start_ = false;
        authorized_ = false;
        epoch_ = last_ = 0;
    }
    bool OnAuthenticatedLobby(Lobby lobby) {
        if (!identity_valid_ || !CheckLobby(lobby)) {
            Revoke();
            return false;
        }
        std::sort(lobby.members.begin(), lobby.members.end(),
                  [](const Member& a, const Member& b) {return a.id < b.id;});
        if (!have_lobby_ || lobby_ != lobby) {
            Revoke(); // membership / world / save-slot changes revoke grants
            lobby_ = std::move(lobby);
            have_lobby_ = true;
        }
        return true;
    }
    bool OnAuthenticatedTeamStart(const Start& start) {
        if (!have_lobby_ || !lobby_.started ||
            !Identifier(start.team) || !Identifier(start.host) ||
            !Identifier(start.world) || start.team != lobby_.team ||
            start.world != lobby_.world || start.party != lobby_.party ||
            start.party != "world:" + start.world ||
            !HasMember(start.host)) {
            Revoke();
            return false;
        }
        const auto me = std::find_if(lobby_.members.begin(), lobby_.members.end(),
            [&](const Member& m) {return m.id == local_id_;});
        if (me == lobby_.members.end() || !me->ready ||
            me->slot != start.slot) {
            Revoke();
            return false;
        }
        if (!have_start_ || start_ != start) {
            authorized_ = false;
            epoch_ = last_ = 0;
            start_ = start;
            have_start_ = true;
        }
        return true;
    }
    // The Welcome message itself contains NO party identifier. The caller
    // supplies party_stream_identity ONLY from a separately authenticated,
    // context-bound party CoopStream (not from the protobuf's own fields).
    // The link-level Welcome and the lobby stream's Welcome MUST NOT call this.
    bool OnAuthenticatedPartyWelcome(const std::string& party_stream_identity,
                                     bool accepted, std::uint64_t epoch,
                                     std::uint64_t last) {
        if (!accepted || !have_lobby_ || !have_start_ ||
            !lobby_.started || party_stream_identity != start_.party ||
            party_stream_identity != lobby_.party ||
            !HasMember(start_.host)) {
            Revoke();
            return false;
        }
        if (authorized_ && (epoch != epoch_ || last < last_)) {
            Revoke(); // an epoch change requires a new trusted world snapshot
            return false;
        }
        epoch_ = epoch;
        last_ = last;
        authorized_ = true;
        return true;
    }
    // A TeamStart validated against the exact authenticated member is
    // sufficient to PREPARE an opt-in party Hello, not to run game NetSync.
    // The loaded save slot comes from the owner game and must match the
    // server's TeamStart before any such Hello may leave this client.
    bool MaySendPartyHello(const std::string& party,
                           std::uint32_t loaded_slot,bool& local_host) const {
        local_host=false;
        if(!identity_valid_ || !have_lobby_ || !have_start_ ||
           authorized_ || !lobby_.started || party!=start_.party ||
           loaded_slot!=start_.slot || !HasMember(local_id_))return false;
        local_host=start_.host==local_id_;
        return true;
    }
    bool Authorized() const noexcept { return authorized_; }
    // A membership check only. Does NOT validate map/owner/channel,
    // invasion policy, the peer's cryptographic key or its endpoint.
    bool IsTeamMember(const std::string& id) const {
        return authorized_ && HasMember(id);
    }
    World Snapshot() const {
        if (!authorized_) return {};
        return {start_.team, start_.party, start_.world, start_.host,
                epoch_, last_, lobby_.members};
    }
private:
    static bool Identifier(const std::string& value) {
        if (value.empty() || value.size() > 255u) return false;
        for (unsigned char c : value) {
            if (c < 0x21u || c > 0x7eu) return false;
        }
        return true;
    }
    static bool ValidWorld(const std::string& value) {
        if (value.empty() || value.size() > 128u) return false;
        for (unsigned char c : value) {
            if (!((c >= 'a' && c <= 'z') ||
                  (c >= 'A' && c <= 'Z') ||
                  (c >= '0' && c <= '9') || c == '-' || c == '_'))
                return false;
        }
        return true;
    }
    bool CheckLobby(const Lobby& lobby) const {
        if (!Identifier(lobby.team) || !Identifier(lobby.leader) ||
            lobby.members.empty() || lobby.members.size() > MaxTeam ||
            (lobby.started &&
             (!ValidWorld(lobby.world) || lobby.party != "world:" + lobby.world)))
            return false;
        std::set<std::string> identities;
        std::set<std::uint32_t> guest_signs;
        bool contains_local = false, contains_leader = false;
        for (const auto& m : lobby.members) {
            if (!Identifier(m.id) || !identities.insert(m.id).second)
                return false;
            if (m.id == local_id_) contains_local = true;
            if (m.id == lobby.leader) {
                contains_leader = true;
                if (m.sign != 0) return false;
            } else if (m.sign < 4u || m.sign > 7u ||
                       !guest_signs.insert(m.sign).second) {
                return false;
            }
        }
        return contains_local && contains_leader;
    }
    bool HasMember(const std::string& id) const {
        return std::any_of(lobby_.members.begin(), lobby_.members.end(),
            [&](const Member& member) {return member.id == id;});
    }
    std::string local_id_;
    bool identity_valid_ = false;
    Lobby lobby_{};
    Start start_{};
    bool have_lobby_ = false, have_start_ = false, authorized_ = false;
    std::uint64_t epoch_ = 0, last_ = 0;
};
} // namespace SeamlessHunt
