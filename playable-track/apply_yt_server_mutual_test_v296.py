#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""V296: test actual source-locked YT server Service/CoopStream, not mocks.

Run after V288 proto patch AND V292 server patch in an expendable YT
checkout; only patches the ORIGINAL test_bloodborne_world.cpp fixture.
"""
import argparse
import subprocess
from pathlib import Path
PIN="5d2305ee611ef1e03be39ff925f0da75c9a70393"
BLOB="fa5c8c758dd6eda3c176320752922bdc03b32375"
REL="server/tests/test_bloodborne_world.cpp"
def once(s,a,b):
    if s.count(a)!=1:raise ValueError("upstream server test ABI changed")
    return s.replace(a,b,1)
def patched(s):
    s=once(s, '#include "bloodborne_world.h"',
           '#include "bloodborne_world.h"\n'
           '#include "shyt_hybrid/yt_signed_peer_grant_v279.h"\n'
           '#include <QtEndian>')
    s=once(s, '''    } else if (envelope.has_team_start()) {
      starts.push_back(envelope.team_start());
''','''    } else if (envelope.has_team_start()) {
      starts.push_back(envelope.team_start());
    } else if (envelope.has_direct_peer_grant()) {
      direct_grants.push_back(envelope.direct_peer_grant());
''')
    s=once(s, '  std::vector<bbcoop::TeamStart> starts;',
           '  std::vector<bbcoop::TeamStart> starts;\n'
           '  std::vector<bbcoop::DirectPeerGrant> direct_grants;')
    runtime=r'''
// V296: real Service::Receive->CoopStream->Service::Take path with
// original bbcoop::Envelope. No Fornex credentials or original game.
int ServerRequiresMutualDirectPeerConsentV296() {
  namespace Grant=BloodborneCoop::SHYTHybrid::SignedPeerGrantV279;
  Service service{{}};
  BloodborneWorld::HostedRules hosted;
  hosted.enabled=true;
  service.SetHosted(hosted);
  service.RequireAuthenticatedIdentity();
  const auto hex=[](const char* name) {
      return QByteArray(name).toHex().toStdString();
  };
  Game a{1000,hex("alice"),11};
  Game b{1001,hex("bob"),12};
  a.online_id="alice";
  b.online_id="bob";
  std::vector<Game*> games{&a,&b};
  qint64 now=QDateTime::currentMSecsSinceEpoch();
  const auto step=[&] {
      now+=300;
      Pump(service,games,now);
  };
  a.LobbyHello(false,now);
  b.LobbyHello(false,now);
  step();
  a.Team(bbcoop::TeamRequest::CREATE,now);
  step();
  a.Team(bbcoop::TeamRequest::INVITE,now,b.name);
  step();
  CHECK(b.lobby.invites_size()==1);
  b.Team(bbcoop::TeamRequest::ACCEPT,now,{},
         b.lobby.invites(0).team());
  step();
  a.Team(bbcoop::TeamRequest::READY,now,{},{},0,"Hunter");
  b.Team(bbcoop::TeamRequest::READY,now,{},{},1,"Doll");
  step();
  a.Team(bbcoop::TeamRequest::START,now);
  step();
  CHECK(!a.starts.empty());
  const QByteArray party=QByteArray::fromStdString(a.starts.back().party());
  a.LobbyHello(true,now);
  b.LobbyHello(true,now);
  a.Hello(now,party);
  b.Hello(now,party);
  step();
  CHECK(a.welcome && a.welcome->accepted());
  CHECK(b.welcome && b.welcome->accepted());
  a.Map(0x18010000,now);
  b.Map(0x18010000,now);
  step();
  CHECK(service.Lobby().TeamOf(a.name));
  CHECK(service.Lobby().TeamOf(b.name));
  CHECK(service.Lobby().TeamOf(a.name)->started());
  CHECK(service.Lobby().TeamOf(a.name)->members_size()==2);
  Grant::PubKey pub{};
  Grant::SecretKey secret{};
  std::array<u8,32> seed{};
  for (size_t i=0;i<seed.size();++i)seed[i]=static_cast<u8>(i+1);
  // TEST-ONLY deterministic signer. Production MUST use OS CSPRNG.
  LinkMonocypher::crypto_eddsa_key_pair(
      secret.data(),pub.data(),seed.data());
  int signed_calls=0;
  bool corrupt_signed_endpoint=false;
  service.SetDirectPeerIssuer(
      [&](const Service::DirectPairSource& src,
          const bbcoop::DirectPeerRequest&) ->std::optional<bbcoop::Envelope>{
        ++signed_calls;
        Grant::Scope scope{};
        scope.team=src.team;scope.party=src.party;
        scope.sender=src.sender;scope.receiver=src.receiver;
        scope.sender_instance=src.sender_game_link_instance;
        scope.receiver_instance=src.receiver_game_link_instance;
        scope.map=src.map;scope.world_epoch=src.world_epoch;
        scope.issued_unix_ms=QDateTime::currentMSecsSinceEpoch();
        scope.expires_unix_ms=scope.issued_unix_ms+20000;
        // V308: the server issuer MUST use authenticated LinkAuth
        // endpoint records, not synthetic guesswork or peer claims.
        scope.sender_ip_nbo=qToBigEndian(src.sender_link.ipv4);
        scope.receiver_ip_nbo=qToBigEndian(src.receiver_link.ipv4);
        scope.sender_port_nbo=qToBigEndian(src.sender_link.port);
        scope.receiver_port_nbo=qToBigEndian(src.receiver_link.port);
        if (src.sender_link!=(
                src.sender==a.name?a.endpoint:b.endpoint) ||
            src.receiver_link!=(
                src.receiver==a.name?a.endpoint:b.endpoint) ||
            src.responder_noise_static_key.size()!=32)
          return std::nullopt;
        std::copy(src.responder_noise_static_key.begin(),
                  src.responder_noise_static_key.end(),
                  scope.responder_noise_pub.begin());
        // V308 negative case: even a VALID EdDSA signature cannot
        // redirect a peer toward a server-unobserved port.
        if(corrupt_signed_endpoint) scope.sender_port_nbo^=1;
        scope.grant_nonce.fill(static_cast<u8>(signed_calls));
        const auto grant=Grant::Sign(scope,secret);
        if(!grant) return std::nullopt;
        const auto raw=Grant::EncodeWire(*grant);
        bbcoop::Envelope message{};
        auto* body=message.mutable_direct_peer_grant();
        body->set_signed_grant(
            std::string(reinterpret_cast<const char*>(raw.data()),raw.size()));
        body->set_authority_public_key(
            std::string(reinterpret_cast<const char*>(pub.data()),pub.size()));
        return message;
      },pub);
  const auto request=[&](Game& from,const Game& to,char key,
                        char nonce=0) {
      bbcoop::Envelope msg{};
      auto* intent=msg.mutable_direct_peer_request();
      intent->set_recipient(to.name);
      intent->set_noise_static_public_key(std::string(32,key));
      intent->set_request_nonce(std::string(16,nonce?nonce:key));
      intent->set_game_link_instance(from.name==a.name?17:29);
      from.Send(msg,now);
      step();
  };
  request(a,b,'A');
  CHECK(signed_calls==0);
  CHECK(a.direct_grants.empty() && b.direct_grants.empty());
  request(b,a,'B');
  CHECK(signed_calls==2);
  CHECK(a.direct_grants.size()==1);
  CHECK(b.direct_grants.size()==1);
  // V301: runtime must prove that EACH real CoopStream recipient got
  // its own correctly signed and directed peer ticket, not merely that
  // two protobuf envelopes were sent.
  const auto decode=[](const bbcoop::DirectPeerGrant& message) {
      const auto* data=reinterpret_cast<const u8*>(
          message.signed_grant().data());
      return Grant::DecodeWire(std::span<const u8>(
          data,message.signed_grant().size()));
  };
  const auto signed_a=decode(a.direct_grants.front());
  const auto signed_b=decode(b.direct_grants.front());
  CHECK(signed_a && signed_b);
  const std::string authority(
      reinterpret_cast<const char*>(pub.data()),pub.size());
  CHECK(a.direct_grants.front().authority_public_key()==authority);
  CHECK(b.direct_grants.front().authority_public_key()==authority);
  const auto& current_team=service.Lobby().TeamOf(a.name);
  CHECK(current_team && current_team==service.Lobby().TeamOf(b.name));
  // Expect stores string_view: never bind it to a temporary
  // QByteArray::toStdString() result (dangling view after statement).
  const std::string expected_party=party.toStdString();
  const Grant::Expect expect_a{
      current_team->id(),expected_party,a.name,b.name,
      17,29,0x18010000,signed_a->scope.world_epoch};
  const Grant::Expect expect_b{
      current_team->id(),expected_party,b.name,a.name,
      29,17,0x18010000,signed_b->scope.world_epoch};
  CHECK(signed_a->scope.sender_ip_nbo==qToBigEndian(a.endpoint.ipv4));
  CHECK(signed_a->scope.receiver_ip_nbo==qToBigEndian(b.endpoint.ipv4));
  CHECK(signed_a->scope.sender_port_nbo==qToBigEndian(a.endpoint.port));
  CHECK(signed_a->scope.receiver_port_nbo==qToBigEndian(b.endpoint.port));
  CHECK(signed_b->scope.sender_ip_nbo==qToBigEndian(b.endpoint.ipv4));
  CHECK(signed_b->scope.receiver_ip_nbo==qToBigEndian(a.endpoint.ipv4));
  CHECK(signed_b->scope.sender_port_nbo==qToBigEndian(b.endpoint.port));
  CHECK(signed_b->scope.receiver_port_nbo==qToBigEndian(a.endpoint.port));
  CHECK(signed_a->scope.team==current_team->id());
  CHECK(signed_a->scope.party==party.toStdString());
  CHECK(signed_a->scope.sender==a.name);
  CHECK(signed_a->scope.receiver==b.name);
  CHECK(signed_a->scope.sender_instance==17);
  CHECK(signed_a->scope.receiver_instance==29);
  CHECK(signed_a->scope.map==0x18010000);
  CHECK(signed_b->scope.sender==b.name);
  CHECK(signed_b->scope.receiver==a.name);
  CHECK(signed_b->scope.sender_instance==29);
  CHECK(signed_b->scope.receiver_instance==17);
  CHECK(signed_a->scope.world_epoch!=0);
  CHECK(signed_a->scope.world_epoch==signed_b->scope.world_epoch);
  CHECK(Grant::Verify(*signed_a,pub,expect_a,
                      QDateTime::currentMSecsSinceEpoch()));
  CHECK(Grant::Verify(*signed_b,pub,expect_b,
                      QDateTime::currentMSecsSinceEpoch()));
  CHECK(!Grant::Verify(*signed_a,pub,expect_b,
                       QDateTime::currentMSecsSinceEpoch()));
  CHECK(!Grant::Verify(*signed_b,pub,expect_a,
                       QDateTime::currentMSecsSinceEpoch()));
  CHECK(std::all_of(signed_a->scope.responder_noise_pub.begin(),
                    signed_a->scope.responder_noise_pub.end(),
                    [](u8 v){return v==static_cast<u8>('B');}));
  CHECK(std::all_of(signed_b->scope.responder_noise_pub.begin(),
                    signed_b->scope.responder_noise_pub.end(),
                    [](u8 v){return v==static_cast<u8>('A');}));
  // Old consent is consumed: no third grant after one replay.
  // V302: both old, mutually consented requests replayed after the
  // rate-limit window must NOT mint two more valid signed grants.
  now+=1300;
  request(a,b,'A');
  request(b,a,'B');
  CHECK(signed_calls==2);
  CHECK(a.direct_grants.size()==1);
  CHECK(b.direct_grants.size()==1);
  // Legitimate new reciprocal consent with NEW nonces and the same
  // registered Noise identities must still work in the same world.
  now+=1300;
  request(a,b,'A','C');
  request(b,a,'B','D');
  CHECK(signed_calls==4);
  CHECK(a.direct_grants.size()==2);
  CHECK(b.direct_grants.size()==2);
  CHECK(decode(a.direct_grants.back()).has_value());
  CHECK(decode(b.direct_grants.back()).has_value());
  // Even older prior nonces stay blocked after a second valid grant.
  now+=1300;
  request(a,b,'A');
  request(b,a,'B');
  CHECK(signed_calls==4);
  CHECK(a.direct_grants.size()==2);
  CHECK(b.direct_grants.size()==2);
  // V308: callback may sign a forged endpoint with correct private
  // EdDSA key; Service itself must reject BOTH sides of the pair.
  corrupt_signed_endpoint=true;
  now+=1300;
  request(a,b,'A','E');
  request(b,a,'B','F');
  CHECK(signed_calls==6);
  CHECK(a.direct_grants.size()==2);
  CHECK(b.direct_grants.size()==2);
  return 0;
}
'''
    s=once(s,"int main() {",runtime+"\nint main() {")
    entry='''      {"FriendsAreFoundAskedAndAnsweredInTheLobby",
       FriendsAreFoundAskedAndAnsweredInTheLobby},'''
    s=once(s,entry,'''      {"ServerRequiresMutualDirectPeerConsentV296",
       ServerRequiresMutualDirectPeerConsentV296},
'''+entry)
    return s
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--upstream-checkout",required=True,type=Path)
    p.add_argument("--mode",choices=["check","apply"],default="check")
    x=p.parse_args()
    root=x.upstream_checkout.resolve(strict=True)
    def git(*args):
        result=subprocess.run(["git","-C",str(root),*args],
                              capture_output=True,text=True,timeout=12)
        if result.returncode:raise ValueError("unpinned upstream test checkout")
        return result.stdout.strip()
    path=root/REL
    if (git("rev-parse","HEAD")!=PIN or
        git("hash-object",REL)!=BLOB or path.is_symlink()):
        raise ValueError("original upstream test source changed")
    content=patched(path.read_text(encoding="utf-8"))
    if x.mode=="apply":
        path.write_text(content,encoding="utf-8")
        print("SHYT_V296_YT_ORIGINAL_SERVER_MUTUAL_CONSENT_TEST_APPLIED")
    else:
        print("SHYT_V296_YT_ORIGINAL_SERVER_TEST_ANCHORS_PASS")
if __name__=="__main__":
    try:main()
    except (ValueError,OSError,subprocess.TimeoutExpired) as e:
        raise SystemExit("V296 unsafe source fixture refused: "+type(e).__name__) from None
