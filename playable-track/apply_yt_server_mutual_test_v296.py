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
           '#include "shyt_hybrid/yt_signed_peer_grant_v279.h"')
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
  service.SetDirectPeerIssuer(
      [&](const Service::DirectPairSource& src,
          const bbcoop::DirectPeerRequest&) ->std::optional<bbcoop::Envelope>{
        ++signed_calls;
        Grant::Scope scope{};
        scope.team=src.team;scope.party=src.party;
        scope.sender=src.sender;scope.receiver=src.receiver;
        scope.sender_instance=src.sender_run;
        scope.receiver_instance=src.receiver_run;
        scope.map=src.map;scope.world_epoch=src.world_epoch;
        scope.issued_unix_ms=QDateTime::currentMSecsSinceEpoch();
        scope.expires_unix_ms=scope.issued_unix_ms+20000;
        scope.sender_ip_nbo=0x0100007f;
        scope.receiver_ip_nbo=0x0200007f;
        scope.sender_port_nbo=30001;
        scope.receiver_port_nbo=30002;
        const char wanted=src.receiver==a.name?'A':'B';
        scope.responder_noise_pub.fill(static_cast<u8>(wanted));
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
  const auto request=[&](Game& from,const Game& to,char key) {
      bbcoop::Envelope msg{};
      auto* intent=msg.mutable_direct_peer_request();
      intent->set_recipient(to.name);
      intent->set_noise_static_public_key(std::string(32,key));
      intent->set_request_nonce(std::string(16,key));
      from.Send(msg,now);
      step();
  };
  request(a,b,'A');
  CHECK(signed_calls==0);
  CHECK(a.direct_grants.empty() && b.direct_grants.empty());
  request(b,a,'B');
  std::cerr<<"V296_DIAG count="<<signed_calls
    <<" a_grants="<<a.direct_grants.size()
    <<" b_grants="<<b.direct_grants.size()
    <<" a_team="<<a.lobby.team().id()
    <<" b_team="<<b.lobby.team().id()
    <<" a_map="<<(service.PlaceOf(a.endpoint) ? service.PlaceOf(a.endpoint)->map : 0)
    <<" b_map="<<(service.PlaceOf(b.endpoint) ? service.PlaceOf(b.endpoint)->map : 0)
    <<" player_status="<<a.lobby.team().members(0).state()
    <<"/"<<b.lobby.team().members(1).state()<<'\n';
  CHECK(signed_calls==2);
  CHECK(a.direct_grants.size()==1);
  CHECK(b.direct_grants.size()==1);
  // Old consent is consumed: no third grant after one replay.
  now+=1300;
  request(a,b,'A');
  CHECK(signed_calls==2);
  CHECK(a.direct_grants.size()==1);
  now+=13000;
  request(b,a,'B');
  CHECK(signed_calls==2);
  CHECK(b.direct_grants.size()==1);
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
        # V296 diagnostics ONLY in disposable functional test build.
        # Production server patch remains silent and private.
        server=root/"server/src/bloodborne_world.cpp"
        body=server.read_text(encoding="utf-8")
        body=once(body,'#include "bloodborne_world.h"',
             '#include "bloodborne_world.h"\n#include <cstdio>')
        stages=[
          ('    if (envelope.has_direct_peer_request()) {',
           '    if (envelope.has_direct_peer_request()) {\n'
           '        std::fprintf(stderr,"V296_GATE_RECEIVED\\n");'),
          ('        // Charge requester BEFORE any costly signing work',
           '        std::fprintf(stderr,"V296_GATE_BASIC_PASS\\n");\n'
           '        // Charge requester BEFORE any costly signing work'),
          ('        // Original YT TeamMember::PLAYING=2.',
           '        std::fprintf(stderr,"V296_GATE_TEAM_PASS\\n");\n'
           '        // Original YT TeamMember::PLAYING=2.'),
          ('        const auto world=worlds.find(member.party);',
           '        std::fprintf(stderr,"V296_GATE_PLAYING_PASS\\n");\n'
           '        const auto world=worlds.find(member.party);'),
          ('        Member* recipient=nullptr;',
           '        std::fprintf(stderr,"V296_GATE_WORLD_PASS\\n");\n'
           '        Member* recipient=nullptr;'),
          ('        if (!recipient) return;',
           '        if (!recipient) return;\n'
           '        std::fprintf(stderr,"V296_GATE_RECIPIENT_PASS\\n");'),
          ('        if (!reciprocal) {',
           '        std::fprintf(stderr,"V296_GATE_RECIPROCAL=%d\\n",reciprocal);\n'
           '        if (!reciprocal) {'),
        ]
        for a,b in stages:body=once(body,a,b)
        server.write_text(body,encoding="utf-8")
        print("SHYT_V296_YT_ORIGINAL_SERVER_MUTUAL_CONSENT_TEST_APPLIED")
    else:
        print("SHYT_V296_YT_ORIGINAL_SERVER_TEST_ANCHORS_PASS")
if __name__=="__main__":
    try:main()
    except (ValueError,OSError,subprocess.TimeoutExpired) as e:
        raise SystemExit("V296 unsafe source fixture refused: "+type(e).__name__) from None
