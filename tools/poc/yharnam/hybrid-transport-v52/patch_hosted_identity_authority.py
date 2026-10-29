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
    # V25 already inserted its opt-in StrictMode identity gate immediately
    # before "const bool arrived". Do NOT match/replace the original
    # OnLobbyHello protocol block: that code was transformed upstream.
    # The live Internet server additionally enforces account binding always.
    cpp=one(cpp,
"""    const bool arrived = member.lobby.empty();
    member.lobby = hello.member();
""",
"""    if (require_authenticated_identity &&
        hello.member()!=member.online_id.toHex().toStdString()) {
        bbcoop::Envelope refuse;
        refuse.mutable_lobby_state()->set_notice(
            "member identity does not match the signed-in account");
        SendTo(member,refuse,now_ms);
        return;
    }
    const bool arrived = member.lobby.empty();
    member.lobby = hello.member();
""","V25-compatible live Qt lobby identity gate before mutation")
    # Discovery V102 already patched LobbyHello to use the signed-in
    # account's hex identity; don't patch that fixture a second time.
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
    # Exercise both unauthorized mutations separately, including
    # attempting to impersonate the leader using another valid signed-in link.
    test=one(test,
"""  const auto valid=service.DiscoverLiveDirectPairs();
  CHECK(valid.size()==10);""",
"""  CHECK(c.welcome && !c.welcome->accepted());
  bbcoop::Envelope forged;
  forged.mutable_lobby_hello()->set_protocol(CoopProtocol);
  forged.mutable_lobby_hello()->set_member(identity(a));
  forged.mutable_lobby_hello()->set_name("forged host");
  c.Send(forged,Now+21);
  Pump(service,games,Now+21);
  CHECK(c.lobby.notice()=="member identity does not match the signed-in account");
  bbcoop::Envelope forged_world;
  auto* forged_hello=forged_world.mutable_hello();
  forged_hello->set_protocol(CoopProtocol);
  forged_hello->set_party(party.toStdString());
  forged_hello->set_member(identity(a));
  forged_hello->set_run(c.run);
  forged_hello->set_direct_p2p_opt_in(true);
  c.Send(forged_world,Now+22);
  Pump(service,games,Now+22);
  CHECK(c.welcome && !c.welcome->accepted());
  CHECK(a.lobby.team().members_size()==5);
  const auto valid=service.DiscoverLiveDirectPairs();
  CHECK(valid.size()==10);""","outsider world rejection and attempted leader impersonation")
    return dict(zip(FILES,(h,cpp,link,test)))
