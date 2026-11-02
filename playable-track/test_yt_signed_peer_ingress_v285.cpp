// SPDX-License-Identifier: GPL-2.0-or-later
// V285: real original YT LinkAuth/Monocypher signature + peer crypto
// cannot be replaced with a caller's 'verified=true' socket flag.
#include "yt_signed_peer_ingress_v285.h"
#include <cassert>
#include <cstdio>
using namespace BloodborneCoop;
using namespace BloodborneCoop::SHYTHybrid;
namespace Grant=BloodborneCoop::SHYTHybrid::SignedPeerGrantV279;
static PeerRouteLease Lease() {
    PeerRouteLease p{};
    p.local_opt_in=true;p.remote_opt_in=true;p.same_party_session=true;
    p.session_authenticated=true;p.peer_authenticated=true;
    p.direct_datagram_verified=true;p.server_route_granted=true;
    p.has_common_protocol=true;p.granted_sender_id="A";p.granted_receiver_id="B";
    p.granted_party_session_id="world:42";
    p.granted_sender_instance=17;p.granted_receiver_instance=29;
    p.authority_epoch=42;p.local_world_epoch=42;
    p.approved_sender_map=0x101;p.approved_target_map=0x101;
    p.now_ms=10000;p.lease_expiry_ms=12000;
    p.last_authenticated_direct_probe_ms=9999;
    return p;
}
int main() {
    Grant::PubKey pub{};
    Grant::SecretKey key{};
    std::array<u8,32> seed{};
    for(size_t i=0;i<32;++i) seed[i]=static_cast<u8>(20+i);
    LinkMonocypher::crypto_eddsa_key_pair(key.data(),pub.data(),seed.data());
    PeerCryptoScopeV241 noise_scope{"world:42","A","B",17,29,42,0x101};
    LinkAuth::Key ab{},ba{};
    for(size_t i=0;i<ab.size();++i) {
        ab[i]=static_cast<u8>(i+1);ba[i]=static_cast<u8>(i+91);
    }
    PeerCryptoDatagramsV241 bob(noise_scope,false,ba,ab);
    Grant::Scope s{};
    s.team="team-42";s.party="world:42";
    s.sender="A";s.receiver="B";
    s.sender_instance=17;s.receiver_instance=29;
    s.map=0x101;s.world_epoch=42;
    s.issued_unix_ms=1810000000000LL;
    s.expires_unix_ms=1810000015000LL;
    s.sender_ip_nbo=0x0100007f;s.receiver_ip_nbo=0x0200007f;
    s.sender_port_nbo=30123;s.receiver_port_nbo=30124;
    for(size_t i=0;i<32;++i)s.responder_noise_pub[i]=static_cast<u8>(i+7);
    for(size_t i=0;i<16;++i)s.grant_nonce[i]=static_cast<u8>(i+2);
    const auto signed_result=Grant::Sign(s,key);
    assert(signed_result);
    SignedPeerIngressV285 authorization{};
    authorization.receiver.session=&bob;
    authorization.receiver.lease=Lease();
    authorization.receiver.identity={"A",17,29,1100,"B","world:42"};
    authorization.receiver.endpoints={0x101,0x101,EnemyPart::None,EnemyPart::None};
    authorization.receiver.approved_endpoint={s.sender_ip_nbo,s.sender_port_nbo};
    authorization.receiver.endpoint_proved_by_authenticated_handshake=true;
    authorization.issued_by_server=*signed_result;
    authorization.pinned_authority_pub=pub;
    authorization.live_server_view={"team-42","world:42","A","B",17,29,0x101,42};
    authorization.noise_scope=noise_scope;
    authorization.responder_noise_pub=s.responder_noise_pub;
    authorization.now_unix_ms=s.issued_unix_ms;
    assert(ValidateSignedPeerIngressV285(authorization));

    auto x=authorization;
    x.receiver.approved_endpoint.second++;
    assert(!ValidateSignedPeerIngressV285(x));
    x=authorization;
    x.receiver.approved_endpoint.first++;
    assert(!ValidateSignedPeerIngressV285(x));
    x=authorization;
    x.receiver.endpoint_proved_by_authenticated_handshake=false;
    assert(!ValidateSignedPeerIngressV285(x));
    x=authorization;
    x.receiver.session=nullptr;
    assert(!ValidateSignedPeerIngressV285(x));
    x=authorization;
    x.issued_by_server.signature[0]^=1;
    assert(!ValidateSignedPeerIngressV285(x));
    x=authorization;
    x.pinned_authority_pub[0]^=1;
    assert(!ValidateSignedPeerIngressV285(x));
    x=authorization;
    x.noise_scope.world_epoch++;
    assert(!ValidateSignedPeerIngressV285(x));
    x=authorization;
    x.responder_noise_pub[9]^=1;
    assert(!ValidateSignedPeerIngressV285(x));
    x=authorization;
    x.receiver.identity.server_authorized_remote_instance++;
    assert(!ValidateSignedPeerIngressV285(x));
    x=authorization;
    x.receiver.lease.authority_epoch++;
    assert(!ValidateSignedPeerIngressV285(x));
    x=authorization;
    x.now_unix_ms=s.expires_unix_ms;
    assert(!ValidateSignedPeerIngressV285(x));
    x=authorization;
    x.live_server_view.party="world:changed";
    assert(!ValidateSignedPeerIngressV285(x));
    x=authorization;
    x.receiver.lease.lease_expiry_ms=x.receiver.lease.now_ms;
    assert(!ValidateSignedPeerIngressV285(x));
    std::puts("SHYT_V285_SIGNED_SERVER_GRANTED_PEER_SOCKET_ADMISSION_PASS");
}
