#!/usr/bin/env python3
"""Native YT shadNet: discover direct candidates from original live world.

Eliminates manually enumerated A-B/A-C/B-C server-side pairs. The signed-in
game LinkServer has the actual observed UDP endpoint and virtual ID already,
so legacy Wozzard STUN's untrusted NP-ID claim is NOT needed. This is a
server-INTERNAL read-only lookup, never public account/IP disclosure and
NEVER a Direct gameplay or production TLS enable switch.
"""
from __future__ import annotations

H="server/src/bloodborne_world.h"
CPP="server/src/bloodborne_world.cpp"
L_H="server/src/link_server.h"
L_CPP="server/src/link_server.cpp"
S_H="server/src/server.h"
S_CPP="server/src/server.cpp"
TEST="server/tests/test_bloodborne_world.cpp"
MAIN="server/src/main.cpp"
FILES=(H,CPP,L_H,L_CPP,S_H,S_CPP,TEST,MAIN)
TYPE="std::vector<std::pair<QByteArray,QByteArray>>"
API="DiscoverLiveDirectPairs"
TAG="SHYT-LIVE-YT-WORLD-PAIR-DISCOVERY"

def one(s,a,b,name):
    n=s.count(a)
    if n!=1:
        raise ValueError(f"live discovery {name}: expected 1 original anchor, got {n}")
    return s.replace(a,b,1)

def patch(srcs):
    if set(srcs)!=set(FILES):
        raise ValueError("must patch exact current original Qt server + world tests")
    h,cpp,lh,lc,sh,sc,test,main=(srcs[p] for p in FILES)
    if TAG in main or API in h or API in sh or API in lh:
        raise ValueError("live pair discovery already installed")
    h=one(h,'#include <string>\n',
          '#include <string>\n#include <vector>\n#include <utility>\n',
          'explicit C++ vector/utility deps')
    # Keep it available only to the server's own Qt event-loop timer.
    # Nothing in ordinary shadNet RPC/HTTP/UDP exposes the candidate list.
    h=one(h,
'''    quint64 CurrentDirectAccountEpoch(const QByteArray& online_id) const;
''',
f'''    quint64 CurrentDirectAccountEpoch(const QByteArray& online_id) const;
    // Server-owned current team pairs, limited to 512 edges / 16 per account.
    // Each pair is rechecked via CaptureDirectPairScope before staging.
    {TYPE} {API}() const;
''', "world declaration")
    cpp=one(cpp,
'''quint64 Service::CurrentDirectAccountEpoch(const QByteArray& id) const {
''',
f'''{TYPE} Service::{API}() const {{
    constexpr std::size_t kMaxPairs=512,kMaxPeersPerAccount=16;
    {TYPE} result;
    std::map<QByteArray,std::size_t> occurrences;
    std::map<std::string,std::vector<QByteArray>> teams; // TEAM ID, never world name
    // Duplicate account links are ambiguous: they NEVER enter a pair.
    for(const auto& [key,member]:members)
        if(!member.online_id.isEmpty())++occurrences[member.online_id];
    for(const auto& [key,member]:members) {{
        if(occurrences[member.online_id]!=1 ||
           !member.direct_p2p_opt_in || !member.direct_state_serial ||
           member.map==0 || member.party.isEmpty() ||
           (!member.cut_from.isEmpty() && member.cut_from==member.party) ||
           endpoints.find(key)==endpoints.end() ||
           worlds.find(member.party)==worlds.end())
            continue;
        // Critical: world membership alone is NOT a team, particularly
        // for public matchmaking or PvP. A user-supplied LobbyHello member
        // may be forged on older servers. Only the hex of the authenticated
        // SHLK online ID is allowed to name this signed-in lobby account.
        const auto authenticated_lobby=member.online_id.toHex().toStdString();
        if(member.lobby.empty() || member.lobby!=authenticated_lobby)
            continue;
        const auto* team=lobby.TeamOf(authenticated_lobby);
        if(!team || !team->started() ||
           team->members_size()<2 || team->members_size()>5 ||
           team->party().empty() ||
           member.party!=FolderOf(QByteArray::fromStdString(team->party())))
            continue;
        teams[team->id()].push_back(member.online_id);
    }}
    std::map<QByteArray,std::size_t> degrees;
    for(auto& [party,players]:teams) {{
        // Full team means host + four hunters, not arbitrarily large
        // user-claimed parties. Refuse a malformed 6+ member world.
        if(players.size()>5)continue;
        std::sort(players.begin(),players.end());
        for(std::size_t i=0;i<players.size() && result.size()<kMaxPairs;++i) {{
            if(degrees[players[i]]>=kMaxPeersPerAccount)continue;
            for(std::size_t j=i+1;j<players.size() && result.size()<kMaxPairs;++j) {{
                if(degrees[players[i]]>=kMaxPeersPerAccount)break;
                if(degrees[players[j]]>=kMaxPeersPerAccount)continue;
                // World service checks BOTH current consents, party, map,
                // owner, epoch and observed physical/virtual addresses.
                // No client-provided peer or NAT hints can authorize this.
                if(!CaptureDirectPairScope(players[i],players[j]))
                    continue;
                result.emplace_back(players[i],players[j]);
                ++degrees[players[i]];++degrees[players[j]];
            }}
        }}
        if(result.size()==kMaxPairs)break;
    }}
    return result;
}}

quint64 Service::CurrentDirectAccountEpoch(const QByteArray& id) const {{
''', "original world candidates")
    for index,old in (
        ("Qt link header",'''    quint64 CurrentDirectAccountEpoch(const QByteArray& id) const;
'''),
        ("Qt server header",'''    quint64 CurrentDirectAccountEpoch(const QByteArray& online_id) const;
''')):
        if index=="Qt link header":
            lh=one(lh,old,old+f'    {TYPE} {API}() const;\n',index)
        else:
            sh=one(sh,old,old+f'    {TYPE} {API}() const;\n',index)
    lc=one(lc,
'''quint64 LinkServer::CurrentDirectAccountEpoch(const QByteArray& id) const {
''',
f'''{TYPE} LinkServer::{API}() const {{
    const auto world=m_world.{API}();
    {TYPE} allowed;
    for(const auto& pair:world)
        if(m_signedIn.contains(pair.first) && m_signedIn.contains(pair.second) &&
           m_world.CurrentDirectAccountEpoch(pair.first) &&
           m_world.CurrentDirectAccountEpoch(pair.second))
            allowed.push_back(pair);
    return allowed;
}}

quint64 LinkServer::CurrentDirectAccountEpoch(const QByteArray& id) const {{
''', "real signed-in LinkServer")
    sc=one(sc,
'''quint64 ShadNetServer::CurrentDirectAccountEpoch(const QByteArray& id) const {
''',
f'''{TYPE} ShadNetServer::{API}() const {{
    return m_linkServer ? m_linkServer->{API}() : {TYPE}{{}};
}}

quint64 ShadNetServer::CurrentDirectAccountEpoch(const QByteArray& id) const {{
''', "one original Qt daemon delegation")
    test=one(test,
'''  CHECK(service.CurrentDirectAccountEpoch("host")!=0);
  CHECK(service.CurrentDirectAccountEpoch("guest")!=0);
''',
f'''  CHECK(service.CurrentDirectAccountEpoch("host")!=0);
  CHECK(service.CurrentDirectAccountEpoch("guest")!=0);
  // A shared world is NOT sufficient: until authenticated YT lobby
  // membership and a started team exist, no direct keys are discoverable.
  CHECK(service.{API}().empty());
''', "actual world one-pair enumeration")
    test=one(test,
'''  CHECK(service.CurrentDirectAccountEpoch("host")==0);
  CHECK(!service.PairDirectConsent("host","guest"));
''',
f'''  CHECK(service.CurrentDirectAccountEpoch("host")==0);
  CHECK(service.{API}().empty());
  CHECK(!service.PairDirectConsent("host","guest"));
''', "map-load revokes discovered edge")
    test=one(test,
'''  b.Hello(now+40,Party,false);
  Pump(service,games,now+40);
  CHECK(service.CurrentDirectAccountEpoch("guest")==0);
  CHECK(!service.PairDirectConsent("host","guest"));
''',
f'''  b.Hello(now+40,Party,false);
  Pump(service,games,now+40);
  CHECK(service.CurrentDirectAccountEpoch("guest")==0);
  CHECK(service.{API}().empty());
  CHECK(!service.PairDirectConsent("host","guest"));
''', "actual opt-out event uniquely revokes discovered edge")
    # The original test game's network link receives a raw account ID;
    # in hosted YT the lobby member is exactly this ID encoded as hex.
    # Preserve the original default used by all existing older tests, but
    # permit one strict authenticated-lobby fixture for candidate discovery.
    test=one(test,
'''  void LobbyHello(bool playing, qint64 now_ms) {
    bbcoop::Envelope envelope;
    envelope.mutable_lobby_hello()->set_protocol(CoopProtocol);
    envelope.mutable_lobby_hello()->set_member(name);
''',
'''  void LobbyHello(bool playing, qint64 now_ms,
                  bool authenticated_account=false) {
    bbcoop::Envelope envelope;
    envelope.mutable_lobby_hello()->set_protocol(CoopProtocol);
    envelope.mutable_lobby_hello()->set_member(
        authenticated_account ?
        QByteArray::fromStdString(name).toHex().toStdString() : name);
''',"real game fixture optionally binds current authenticated online ID")
    test=one(test,
'''int ATeamFormsAndStartsThroughTheService() {
''',
f'''int AuthenticatedFiveHunterPolicyDoesNotDiscoverOtherTeams() {{
  Service service{{{{}}}};
  Game a{{1000,"host",11}}, b{{1001,"guest",12}}, c{{1002,"stranger",13}};
  Game d{{1003,"guest2",14}}, e{{1004,"guest3",15}}, f{{1005,"guest4",16}};
  constexpr qint64 Now=1'000'000;
  const std::vector<Game*> games{{&a,&b,&c,&d,&e,&f}};
  for(Game* game:games)game->LobbyHello(false,Now,true);
  Pump(service,games,Now);
  const auto identity=[](const Game& game) {{
      return QByteArray::fromStdString(game.name).toHex().toStdString();
  }};
  a.Team(bbcoop::TeamRequest::CREATE,Now);
  Pump(service,games,Now);
  CHECK(a.lobby.has_team());
  const auto team=a.lobby.team().id();
  for(Game* guest:std::vector<Game*>{{&b,&d,&e,&f}}) {{
      a.Team(bbcoop::TeamRequest::INVITE,Now,identity(*guest));
      Pump(service,games,Now);
      guest->Team(bbcoop::TeamRequest::ACCEPT,Now,{{}},team);
      Pump(service,games,Now);
  }}
  CHECK(a.lobby.team().members_size()==5);
  // A sixth player, even in the same world, MUST NOT inherit team grants.
  a.Team(bbcoop::TeamRequest::INVITE,Now,identity(c));
  Pump(service,games,Now);
  CHECK(c.lobby.invites_size()==0);
  for(Game* member:std::vector<Game*>{{&a,&b,&d,&e,&f}})
      member->Team(bbcoop::TeamRequest::READY,Now,{{}},{{}},1);
  Pump(service,games,Now);
  a.Team(bbcoop::TeamRequest::START,Now);
  Pump(service,games,Now);
  CHECK(!a.starts.empty() && !b.starts.empty());
  const auto party=QByteArray::fromStdString(a.starts.back().party());
  for(Game* game:games) {{
      game->Hello(Now+20,party,true);
      game->Map(0x18010000,Now+20);
  }}
  Pump(service,games,Now+20);
  const auto valid=service.{API}();
  CHECK(valid.size()==10); // five approved hunters => 5*4/2
  for(const auto& edge:valid)
      CHECK(edge.first!="stranger" && edge.second!="stranger");
  // Host leaves first: TeamLobby must elect the next leader,
  // and old-host direct grants disappear without tearing down the
  // four surviving hunters' world. An outsider stays denied.
  a.Team(bbcoop::TeamRequest::LEAVE,Now+40);
  Pump(service,games,Now+40);
  CHECK(b.lobby.has_team());
  CHECK(b.lobby.team().leader()==identity(b));
  CHECK(service.{API}().size()==6); // four hunters still share six edges
  b.Team(bbcoop::TeamRequest::LEAVE,Now+50);
  Pump(service,games,Now+50);
  CHECK(d.lobby.has_team());
  CHECK(d.lobby.team().leader()==identity(d));
  CHECK(service.{API}().size()==3); // three hunters, three edges
  d.Team(bbcoop::TeamRequest::LEAVE,Now+60);
  Pump(service,games,Now+60);
  CHECK(service.{API}().size()==1); // e and f survive
  e.Team(bbcoop::TeamRequest::LEAVE,Now+70);
  Pump(service,games,Now+70);
  CHECK(service.{API}().empty());
  return 0;
}}

int ATeamFormsAndStartsThroughTheService() {{
''',"original Qt world real team and intruder isolation")
    test=one(test,
'''      {"ATeamFormsAndStartsThroughTheService",
       ATeamFormsAndStartsThroughTheService},
''',
'''      {"AuthenticatedFiveHunterPolicyDoesNotDiscoverOtherTeams",
       AuthenticatedFiveHunterPolicyDoesNotDiscoverOtherTeams},
      {"ATeamFormsAndStartsThroughTheService",
       ATeamFormsAndStartsThroughTheService},
''',"include actual authenticated team isolation regression")
    # Replace LOCAL 3-way hardcoded enumeration with real current signed-in
    # shadNet world. For this dev test, only exactly operator-pinned A/B/C
    # may consume the candidate offers. This does NOT make public TLS.
    old='''                    (void)p2p_tls.ConfigureLocalTeamPairV102(
                        a,b,world_pair,pair_id);
                    (void)p2p_tls.ConfigureLocalTeamPairV102(
                        a,c,world_pair,pair_id);
                    (void)p2p_tls.ConfigureLocalTeamPairV102(
                        b,c,world_pair,pair_id);
'''
    new='''                    // Peer list comes from real signed-in shadNet
                    // team membership; no hardcoded edge or user claim.
                    // Local test pins alone choose whose grants may be
                    // consumed by this isolated 127.0.0.1 listener.
                    const auto authorized=[&](const QByteArray& id) {
                        return id==a || id==b || id==c ||
                               (!d.isEmpty() && id==d) ||
                               (!e.isEmpty() && id==e);
                    };
                    std::vector<std::pair<QByteArray,QByteArray>> current;
                    for(const auto& edge:server.DiscoverLiveDirectPairs()) {
                        if(authorized(edge.first) &&
                           authorized(edge.second))
                            current.push_back(edge);
                    }
                    // Revoke pending grants before staging new ones;
                    // otherwise old team edges can outlive departure.
                    // Game-client revocation is separate and still needed.
                    (void)p2p_tls.ReconcileLocalTeamPairsV102(current);
                    for(const auto& edge:current)
                        (void)p2p_tls.ConfigureLocalTeamPairV102(
                            edge.first,edge.second,world_pair,pair_id);
'''
    main=one(main,old,new,"remove operator hardcoded three-pair staging")
    main=one(main,
'''        const QByteArray team_enabled=qgetenv("SHYT_P2P_TLS_AUTOTEAM_TEST");
''',
f'''        // {TAG}: no new STUN service; original game link owns peer addresses.
        const QByteArray team_enabled=qgetenv("SHYT_P2P_TLS_AUTOTEAM_TEST");
''', "main source tag")
    return dict(zip(FILES,(h,cpp,lh,lc,sh,sc,test,main)))
