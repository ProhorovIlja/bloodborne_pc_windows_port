// SPDX-License-Identifier: GPL-2.0-or-later
// V288: compiled *real pinned upstream protobuf* game/server Coop
// Envelope uses additive message fields 51/52 without disturbing 1-50.
// Neither sending a request nor decoding a response enables P2P.
#include "coop.pb.h"
#include <cassert>
#include <cstdint>
#include <cstdio>
#include <string>
int main() {
    bbcoop::Envelope request{};
    auto* want=request.mutable_direct_peer_request();
    want->set_recipient("hunter-B");
    want->set_noise_static_public_key(std::string(32,'K'));
    want->set_request_nonce(std::string(16,'R'));
    assert(request.body_case()==bbcoop::Envelope::kDirectPeerRequest);
    std::string wire{};
    assert(request.SerializeToString(&wire) && wire.size()<512);
    bbcoop::Envelope received{};
    assert(received.ParseFromString(wire));
    assert(received.has_direct_peer_request());
    assert(received.direct_peer_request().recipient()=="hunter-B");
    assert(received.direct_peer_request().noise_static_public_key().size()==32);
    assert(received.direct_peer_request().request_nonce().size()==16);

    bbcoop::Envelope issued{};
    auto* signed_msg=issued.mutable_direct_peer_grant();
    signed_msg->set_signed_grant(std::string(256,'G'));
    signed_msg->set_authority_public_key(std::string(32,'A'));
    assert(issued.body_case()==bbcoop::Envelope::kDirectPeerGrant);
    assert(issued.SerializeToString(&wire));
    received.Clear();
    assert(received.ParseFromString(wire));
    assert(received.has_direct_peer_grant());
    assert(received.direct_peer_grant().signed_grant().size()==256);
    assert(received.direct_peer_grant().authority_public_key().size()==32);

    // A legacy stream still handles original message numbering.
    bbcoop::Envelope old{};
    old.mutable_team_request()->set_world("old-yharnam");
    assert(old.body_case()==bbcoop::Envelope::kTeamRequest);
    old.mutable_duel_state();
    assert(old.body_case()==bbcoop::Envelope::kDuelState);
    puts("SHYT_V288_REAL_PROTOC_PINNED_COOP_SIGNED_GRANT_SCHEMA_PASS");
}
