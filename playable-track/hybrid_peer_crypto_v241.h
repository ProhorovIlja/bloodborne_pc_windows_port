// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
// V241: actual authenticated encryption of YT GameFrame movement datagrams.
// Uses original pinned YT LinkAuth::Session / Monocypher implementation.
// The caller MUST obtain independent directional keys through a verified
// peer handshake + server-issued pair lease. Never reuse shadNet link keys.
// This has NO socket, STUN, certificate authority or launcher integration.
#include "hybrid_direct_egress_v240.h"
#include "coop/link_auth.h"
#include <algorithm>
#include <array>
#include <cstddef>
#include <cstdint>
#include <optional>
#include <span>
#include <string>
#include <string_view>
#include <vector>

namespace BloodborneCoop::SHYTHybrid {

struct PeerCryptoScopeV241 {
    std::string party_session;
    std::string hunter_a;
    std::string hunter_b;
    u32 a_instance = 0;
    u32 b_instance = 0;
    u64 world_epoch = 0;
    u32 map = 0;
};

inline bool ValidPeerCryptoScopeV241(const PeerCryptoScopeV241& s) {
    return !s.party_session.empty() && s.party_session.size() <= 128 &&
        !s.hunter_a.empty() && s.hunter_a.size() <= 128 &&
        !s.hunter_b.empty() && s.hunter_b.size() <= 128 &&
        s.hunter_a != s.hunter_b && s.a_instance && s.b_instance &&
        s.world_epoch && s.map;
}

inline std::array<u8, 32> PeerBindingV241(const PeerCryptoScopeV241& s) {
    std::vector<u8> bytes = {'S','H','Y','T','-','P','E','E','R','-','2','4','1'};
    auto add_string = [&](const std::string& name) {
        bytes.push_back(static_cast<u8>(name.size())); // scope size <=128
        bytes.insert(bytes.end(), name.begin(), name.end());
    };
    auto add_number = [&](u64 value, size_t width) {
        for (size_t i=0;i<width;i++) bytes.push_back(static_cast<u8>(value >> (i*8)));
    };
    add_string(s.party_session);
    add_string(s.hunter_a);
    add_string(s.hunter_b);
    add_number(s.a_instance, 4);
    add_number(s.b_instance, 4);
    add_number(s.world_epoch, 8);
    add_number(s.map, 4);
    return LinkAuth::Sha256::Of(bytes);
}

class PeerCryptoDatagramsV241 {
public:
    // The two keys must come from a VERIFIED peer-to-peer Noise/session
    // exchange, not from the existing client<->server LinkAuth::Session.
    PeerCryptoDatagramsV241(PeerCryptoScopeV241 scope, bool local_is_a,
                            const LinkAuth::Key& send_key,
                            const LinkAuth::Key& receive_key)
        : scope_(std::move(scope)), local_is_a_(local_is_a),
          binding_(PeerBindingV241(scope_)), cipher_(send_key, receive_key),
          valid_(ValidPeerCryptoScopeV241(scope_) && send_key != receive_key &&
              std::any_of(send_key.begin(),send_key.end(),[](u8 b){return b!=0;}) &&
              std::any_of(receive_key.begin(),receive_key.end(),[](u8 b){return b!=0;})) {}

    // V258: a correctly encrypted datagram is NOT enough if it belongs
    // to a prior world epoch/session. Revalidate the live server-issued
    // ordered pair grant against the key exchange's pinned crypto scope.
    bool MatchesOutgoingGrantV258(const PeerRouteLease& lease,
                                  const DirectEgressIdentity& identity,
                                  const PacketEnds& ends) const {
        const auto& me=local_is_a_ ? scope_.hunter_a : scope_.hunter_b;
        const auto& other=local_is_a_ ? scope_.hunter_b : scope_.hunter_a;
        const u32 mine=local_is_a_ ? scope_.a_instance : scope_.b_instance;
        const u32 theirs=local_is_a_ ? scope_.b_instance : scope_.a_instance;
        return valid_ && identity.server_authorized_local_id==me &&
            identity.server_authorized_remote_id==other &&
            identity.server_authorized_party_session_id==scope_.party_session &&
            identity.local_instance==mine && identity.remote_instance==theirs &&
            lease.granted_sender_id==me && lease.granted_receiver_id==other &&
            lease.granted_sender_instance==mine &&
            lease.granted_receiver_instance==theirs &&
            lease.granted_party_session_id==scope_.party_session &&
            lease.authority_epoch==scope_.world_epoch &&
            lease.local_world_epoch==scope_.world_epoch &&
            lease.approved_sender_map==scope_.map &&
            lease.approved_target_map==scope_.map &&
            ends.sender_map==scope_.map && ends.target_map==scope_.map;
    }

    // V262: verify that the actual receiver's authenticated, live
    // server-issued lease still authorizes precisely the pair for which
    // these Noise-derived keys were created. The local role is INVERTED
    // against outgoing: the remote peer is the GameFrame sender.
    bool MatchesIncomingGrantV262(const PeerRouteLease& lease,
                                  const DirectIngressIdentity& identity,
                                  const PacketEnds& ends) const {
        const auto& remote=local_is_a_ ? scope_.hunter_b : scope_.hunter_a;
        const auto& local=local_is_a_ ? scope_.hunter_a : scope_.hunter_b;
        const u32 remote_instance=local_is_a_ ? scope_.b_instance : scope_.a_instance;
        const u32 local_instance=local_is_a_ ? scope_.a_instance : scope_.b_instance;
        return valid_ &&
            identity.server_authorized_remote_id==remote &&
            identity.server_authorized_local_id==local &&
            identity.server_authorized_party_session_id==scope_.party_session &&
            identity.server_authorized_remote_instance==remote_instance &&
            identity.local_instance==local_instance &&
            lease.granted_sender_id==remote &&
            lease.granted_receiver_id==local &&
            lease.granted_sender_instance==remote_instance &&
            lease.granted_receiver_instance==local_instance &&
            lease.granted_party_session_id==scope_.party_session &&
            lease.authority_epoch==scope_.world_epoch &&
            lease.local_world_epoch==scope_.world_epoch &&
            lease.approved_sender_map==scope_.map &&
            lease.approved_target_map==scope_.map &&
            ends.sender_map==scope_.map && ends.target_map==scope_.map;
    }

    static constexpr size_t MaxDatagram = 1200;
    static constexpr size_t HeaderSize = LinkAuth::HeaderBytes;
    static constexpr size_t BindingSize = 32;
    static constexpr std::array<u8, HeaderSize> Header{
        0xff, 0xff, 0xff, 0xff, 'S', 'H', 'D', 'P', 1
    };

    std::optional<std::vector<u8>> SealMovement(const GameFrame& frame) {
        if (!valid_ || !CheckFrame(frame, true)) return std::nullopt;
        const auto body = EncodeGameFrame(frame);
        if (body.size() + HeaderSize + BindingSize +
            LinkAuth::TrailerBytes > MaxDatagram) return std::nullopt;
        std::vector<u8> wire(Header.begin(), Header.end());
        wire.insert(wire.end(), binding_.begin(), binding_.end());
        wire.insert(wire.end(), body.begin(), body.end());
        const auto trailer = cipher_.Seal(wire);
        wire.insert(wire.end(), trailer.begin(), trailer.end());
        return wire;
    }

    std::optional<GameFrame> OpenMovement(std::span<const u8> received) {
        if (!valid_ || received.size() > MaxDatagram ||
            received.size() < HeaderSize + BindingSize +
                LinkAuth::TrailerBytes + 1 ||
            !std::equal(Header.begin(), Header.end(), received.begin()))
            return std::nullopt;
        std::vector<u8> packet(received.begin(), received.end());
        // Original YT Open checks the AEAD tag + counter replay window BEFORE
        // the untrusted plaintext may reach the GameFrame decoder.
        if (cipher_.Open(packet) != LinkAuth::Session::Verdict::Ok)
            return std::nullopt;
        const auto frame_end = packet.size() - LinkAuth::TrailerBytes;
        if (!std::equal(binding_.begin(), binding_.end(),
                        packet.begin() + HeaderSize))
            return std::nullopt;
        auto decoded = DecodeGameFrame(
            std::span<const u8>(packet.data() + HeaderSize + BindingSize,
                frame_end - HeaderSize - BindingSize));
        if (!decoded || !CheckFrame(*decoded, false)) return std::nullopt;
        return decoded;
    }

private:
    bool CheckFrame(const GameFrame& frame, bool outbound) const {
        const bool sender_is_a = outbound ? local_is_a_ : !local_is_a_;
        const auto& sender = sender_is_a ? scope_.hunter_a : scope_.hunter_b;
        const u32 source_instance = sender_is_a ? scope_.a_instance : scope_.b_instance;
        const u32 peer_instance = sender_is_a ? scope_.b_instance : scope_.a_instance;
        return frame.sender == sender && frame.instance == source_instance &&
            frame.peer_instance == peer_instance && frame.ack == 0 &&
            IsExactUnreliableMovement(frame, 1100);
    }

    PeerCryptoScopeV241 scope_;
    bool local_is_a_;
    std::array<u8, 32> binding_{};
    LinkAuth::Session cipher_;
    bool valid_;
};
} // namespace BloodborneCoop::SHYTHybrid
