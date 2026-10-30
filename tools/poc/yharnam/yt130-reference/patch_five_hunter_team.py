#!/usr/bin/env python3
"""5 coop hunters on original pinned Qt YT team lobby, candidate only.

Server admits host + 4 cooperators. Fourth guest uses sign 4, previously
unused by co-op in this pinned source. Upstream unmerged invasion prototype
also guesses sign 4: merging it MUST reserve the slot for co-op and deny PvP
when the party is full. Native game support for 4 simultaneous remote
characters still needs live confirmation. No production merge/Direct unlock.
"""
from __future__ import annotations
H="server/coop/team_lobby.h"
CPP="server/coop/team_lobby.cpp"
TEST="server/tests/test_team_lobby.cpp"
FILES=(H,CPP,TEST)

def one(src,old,new,label):
    n=src.count(old)
    if n!=1:
        raise ValueError(f"5 hunter {label}: pinned upstream changed, {n} anchors")
    return src.replace(old,new,1)

def patch(files):
    if set(files)!=set(FILES):
        raise ValueError("five player patch must update source and server test")
    h,cpp,test=(files[x] for x in FILES)
    h=one(h,
        "// The game's remote player slots: the host and three more.\nconstexpr size_t TeamSize = 4;",
        "// Candidate 5-hunter coop: host and FOUR remote hunter slots.\n"
        "// GameDataMan has four remote player slots; validate actual in-game\n"
        "// fourth guest before production. Invader can't reuse guest sign 4.\n"
        "constexpr size_t TeamSize = 5;",
        "host + four capacity")
    cpp=one(cpp,
        "constexpr std::array<u32, 3> GuestSigns{7, 6, 5};",
        "// Guest sign 4 was unused by co-op in this pinned server; it\n"
        "// conflicts with the upstream EXPERIMENTAL InvasionSign=4.\n"
        "// Reserve for the fourth cooperator; no invader in full team.\n"
        "constexpr std::array<u32, 4> GuestSigns{7, 6, 5, 4};",
        "four distinct guest signs, no collision")
    test=one(test,
        "int TeamHoldsFour() {",
        "int TeamHoldsFive() {",
        "renamed capacity test")
    test=one(test,
        '''int TeamHoldsFive() {
  TeamLobby lobby = NewLobby();
  for (const char *m : {"a", "b", "c", "d", "e"}) {''',
        '''int TeamHoldsFive() {
  TeamLobby lobby = NewLobby();
  for (const char *m : {"a", "b", "c", "d", "e", "f"}) {''',
        "capacity test six players only inside five-hunter fixture")
    test=one(test,
        '''  for (const char *m : {"b", "c", "d"}) {
    lobby.Request("a", Request(Action::INVITE, m));
    CHECK(lobby.Request(m, Request(Action::ACCEPT, {}, team)).changed);
  }
  CHECK(lobby.TeamOf("a")->members_size() == 4);
  // A full team takes no more: the invite itself is refused.
  CHECK(!lobby.Request("a", Request(Action::INVITE, "e")).notice.empty());''',
        '''  for (const char *m : {"b", "c", "d", "e"}) {
    lobby.Request("a", Request(Action::INVITE, m));
    CHECK(lobby.Request(m, Request(Action::ACCEPT, {}, team)).changed);
  }
  CHECK(lobby.TeamOf("a")->members_size() == 5);
  CHECK(SignOf(lobby, "a") == 0);
  // A full team takes no sixth player, even while it can see the lobby.
  CHECK(!lobby.Request("a", Request(Action::INVITE, "f")).notice.empty());'''.replace(
           '  CHECK(SignOf(lobby, "a") == 0);\n',''),
        "5 member join and 6th refuses")
    test=one(test,
        "failed |= TeamHoldsFour();",
        "failed |= TeamHoldsFive();",
        "invoke renamed test")
    # In the existing original host handover test, test all FOUR guest
    # signs with a 5-player team, recycling the freed slot after a leave.
    part='''int GuestsKeepTheirPlayerSlots() {
  TeamLobby lobby = NewLobby();
  for (const char *m : {"a", "b", "c", "d", "e"}) {
    lobby.Arrive(m, m, false);
  }
  lobby.Request("a", Request(Action::CREATE));
  const std::string team = lobby.TeamOf("a")->id();
  for (const char *m : {"b", "c", "d"}) {
    lobby.Request("a", Request(Action::INVITE, m));
    lobby.Request(m, Request(Action::ACCEPT, {}, team));
  }
  CHECK(SignOf(lobby, "a") == 0); // the leader hosts: no sign'''
    repl='''int GuestsKeepTheirPlayerSlots() {
  TeamLobby lobby = NewLobby();
  for (const char *m : {"a", "b", "c", "d", "e", "f"}) {
    lobby.Arrive(m, m, false);
  }
  lobby.Request("a", Request(Action::CREATE));
  const std::string team = lobby.TeamOf("a")->id();
  for (const char *m : {"b", "c", "d", "e"}) {
    lobby.Request("a", Request(Action::INVITE, m));
    lobby.Request(m, Request(Action::ACCEPT, {}, team));
  }
  CHECK(SignOf(lobby, "e") == 4);
  CHECK(lobby.TeamOf("a")->members_size() == 5);
  CHECK(SignOf(lobby, "a") == 0); // the leader hosts: no sign'''
    test=one(test,part,repl,"real fourth guest retains sign 4")
    test=one(test,
        '''  // c leaves: b and d keep theirs, and e takes the free one.
  lobby.Request("c", Request(Action::LEAVE));
  CHECK(SignOf(lobby, "b") == 7 && SignOf(lobby, "d") == 5);
  lobby.Request("a", Request(Action::INVITE, "e"));
  lobby.Request("e", Request(Action::ACCEPT, {}, team));
  CHECK(SignOf(lobby, "e") == 6);
  // The leader leaves: the new one hosts, the others keep theirs.
  lobby.Request("a", Request(Action::LEAVE));
  CHECK(lobby.TeamOf("b")->leader() == "b" && SignOf(lobby, "b") == 0);
  CHECK(SignOf(lobby, "d") == 5 && SignOf(lobby, "e") == 6);''',
        '''  // c leaves: the other THREE guests keep their signs, while
  // f takes precisely the vacated sign 6.
  lobby.Request("c", Request(Action::LEAVE));
  CHECK(SignOf(lobby, "b") == 7 && SignOf(lobby, "d") == 5 &&
        SignOf(lobby, "e") == 4);
  lobby.Request("a", Request(Action::INVITE, "f"));
  CHECK(lobby.Request("f", Request(Action::ACCEPT, {}, team)).changed);
  CHECK(SignOf(lobby, "f") == 6);
  CHECK(lobby.TeamOf("a")->members_size() == 5);
  // The leader leaves: no sign collision; everyone keeps a valid sign.
  lobby.Request("a", Request(Action::LEAVE));
  CHECK(lobby.TeamOf("b")->leader() == "b" && SignOf(lobby, "b") == 0);
  CHECK(SignOf(lobby, "d") == 5 && SignOf(lobby, "e") == 4 &&
        SignOf(lobby, "f") == 6);''',
        "fifth hunter and slot reuse across host handover")
    # With host + FOUR guests, the ORIGINAL "join by team code" regression
    # must also admit its fifth member. Otherwise it incorrectly asserts
    # the v1.3.0 4-person cap and fails genuine Qt CTests despite correct
    # five-hunter server admission. The sixth player remains refused.
    test=one(test,
        '''  CHECK(lobby.Request("b", join).notice.empty());
  CHECK(lobby.Request("c", join).notice.empty());
  CHECK(!lobby.Request("d", join).notice.empty());
  CHECK(!lobby.TeamOf("d"));''',
        '''  CHECK(lobby.Request("b", join).notice.empty());
  CHECK(lobby.Request("c", join).notice.empty());
  CHECK(lobby.Request("d", join).notice.empty());
  CHECK(lobby.TeamOf("d") == lobby.TeamOf("a"));
  CHECK(!lobby.Request("f", join).notice.empty()); // sixth is refused
  CHECK(!lobby.TeamOf("f"));''',
        "code-join fifth accepted and sixth refused")
    test=one(test,
        '''  CHECK(!lobby.Request("d", join).notice.empty());
  join.set_code(fresh);
  CHECK(lobby.Request("d", join).notice.empty());
  CHECK(lobby.TeamOf("d") == lobby.TeamOf("a"));''',
        '''  CHECK(!lobby.Request("f", join).notice.empty());
  join.set_code(fresh);
  CHECK(lobby.Request("f", join).notice.empty());
  CHECK(lobby.TeamOf("f") == lobby.TeamOf("a"));''',
        "renewed team code permits sixth only after vacated seat")
    return dict(zip(FILES,(h,cpp,test)))
