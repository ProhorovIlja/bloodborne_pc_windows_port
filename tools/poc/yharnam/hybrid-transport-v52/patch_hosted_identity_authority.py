#!/usr/bin/env python3
"""Backport narrow upstream YT PR #423 authenticated-world identity guard.

One original game link's trusted online_id, not a user-supplied LobbyHello or
Hello member string, must own lobby requests and team worlds on the real Qt
shadNet server. Isolated original World/TeamLobby tests keep historical fake
names unless the test explicitly invokes RequireAuthenticatedIdentity().
No wire/protobuf changes, no new public socket, no Direct game enable.
"""
from __future__ import annotations
H="server/src/bloodborne_world.h"
CPP="server/src/bloodborne_world.cpp"
LINK="server/src/link_server.cpp"
TEST="server/tests/test_bloodborne_world.cpp"
FILES=(H,CPP,LINK,TEST)

def one(content,old,new,what):
    n=content.count(old)
    if n!=1:
        raise ValueError(f"authenticated YT identity {what}: {n} pinned anchors")
    return content.replace(old,new,1)

def patch(src):
    if set(src)!=set(FILES):
        raise ValueError("need original YT world, LinkServer and real world tests")
    h,cpp,link,test=(src[k] for k in FILES)
    h=one(h,
"""    explicit Service(QString folder, qint64 heartbeat_ms = 1000, int compact_records = 200,
                     qint64 compact_ms = 30'000);
""",
"""    explicit Service(QString folder, qint64 heartbeat_ms = 1000, int compact_records = 200,
                     qint64 compact_ms = 30'000);
    // Upstream YT #423: the Internet-facing game link must not accept
    // client-chosen member identity in LobbyHello or game Hello.
    void RequireAuthenticatedIdentity() { require_authenticated_identity = true; }
""","public opt-in for authentic server")
    h=one(h,
"""    bool lobby_changed = false; // a player's game went: states to send at the next tick
""",
"""    bool lobby_changed = false; // a player's game went: states to send at the next tick
    bool require_authenticated_identity = false; // tests opt in, live LinkServer ALWAYS opts in
""","default compatible with synthetic test identities")
    link=one(link,
"""      m_rpcInstance(QRandomGenerator::global()->generate() | 1u) {
    if (!m_db.Open(db_path))
""",
"""      m_rpcInstance(QRandomGenerator::global()->generate() | 1u) {
    // Upstream #423: NEVER allow a signed-in link to control another
    // user's lobby/team/world by forging a second protobuf member name.
    m_world.RequireAuthenticatedIdentity();
    if (!m_db.Open(db_path))
""","real shadNet LinkServer enables account binding")
    cpp=one(cpp,
"""    } else if (party.indexOf(':') <= 0 || hello.member().empty()) {
        welcome.set_text("no party key or member name");
    }
    if (!welcome.text().empty()) {
""",
"""    } else if (party.indexOf(':') <= 0 || hello.member().empty()) {
        welcome.set_text("no party key or member name");
    } else if (require_authenticated_identity &&
               hello.member() != member.online_id.toHex().toStdString()) {
        welcome.set_text("member identity does not match the signed-in account");
    } else if (require_authenticated_identity && party.startsWith("world:")) {
        // A world key alone is NOT permission to follow an existing team.
        // Ordinary PvP invaders will need a separately authenticated role.
        const auto* team=lobby.TeamOf(hello.member());
        if(!team || !team->started() || team->party()!=party.toStdString())
            welcome.set_text("not in the team that plays this world");
    }
    if (!welcome.text().empty()) {
""","deny forged world hello and uninvited team world")
    cpp=one(cpp,
"""    if (hello.protocol() != CoopProtocol || hello.member().empty()) {
        bbcoop::Envelope answer;
        answer.mutable_lobby_state()->set_notice(
            hello.member().empty() ? "no member name"
                                   : "co-op protocol " + std::to_string(hello.protocol()) +
                                         ", this server speaks " + std::to_string(CoopProtocol));
""",
"""    const bool wrong_identity=require_authenticated_identity &&
        hello.member()!=member.online_id.toHex().toStdString();
    if (hello.protocol() != CoopProtocol || hello.member().empty() || wrong_identity) {
        bbcoop::Envelope answer;
        answer.mutable_lobby_state()->set_notice(
            hello.member().empty() ? "no member name"
            : wrong_identity ? "member identity does not match the signed-in account"
                             : "co-op protocol " + std::to_string(hello.protocol()) +
                                   ", this server speaks " + std::to_string(CoopProtocol));
""","reject spoofed lobby account before TeamLobby mutation")
    # The real original game test's default names remain unchanged. Explicit
    # strict test fixture uses exactly authenticated online_id.toHex().
    test=one(test,
"""  void Hello(qint64 now_ms, const QByteArray &party = Party,
             bool direct_p2p_opt_in=false) {
""",
"""  void Hello(qint64 now_ms, const QByteArray &party = Party,
             bool direct_p2p_opt_in=false, bool authenticated_account=false) {
""","fixture strict game Hello signature")
    test=one(test,
"""    envelope.mutable_hello()->set_member(name);
""",
"""    envelope.mutable_hello()->set_member(
        authenticated_account ?
        QByteArray::fromStdString(name).toHex().toStdString() : name);
""","fixture strict game Hello wire name")
    test=one(test,
"""int AuthenticatedFiveHunterPolicyDoesNotDiscoverOtherTeams() {
  Service service{{}};
""",
"""int AuthenticatedFiveHunterPolicyDoesNotDiscoverOtherTeams() {
  Service service{{}};
  service.RequireAuthenticatedIdentity();
""","enable strict original game world regression")
    test=one(test,
"""      game->Hello(Now+20,party,true);
""",
"""      game->Hello(Now+20,party,true,true);
""","send actual signed-in identity through the original world")
    # Exercise both unauthenticated mutations separately, AND ensure the
    # forged same-world outsider never receives a valid game Welcome.
    test=one(test,
"""  const auto valid=service.DiscoverLiveDirectPairs();
  CHECK(valid.size()==10);""",
"""  CHECK(c.welcome && !c.welcome->accepted());
  const auto valid=service.DiscoverLiveDirectPairs();
  CHECK(valid.size()==10);""","sixth member's game Hello rejected despite knowing the world key")
    return dict(zip(FILES,(h,cpp,link,test)))
