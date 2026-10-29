#!/usr/bin/env python3
"""YT pinned native game candidate: host + FOUR real remote hunters.

The original TeamLobby cap and fourth guest sign are server-side only.
The game's own RoomForMore() still artificially stops the hosting player's
re-summon search at three total players. The reverse-engineering docs report
four remote GameDataMan slots, but a real five-hunter in-game rig test remains
MANDATORY. This patch does not enable Direct gameplay or change relay routing.
"""
from __future__ import annotations

PARTY="emulator/src/core/bloodborne_party.cpp"
HEADER="emulator/src/core/bloodborne_party.h"
JOIN="emulator/src/core/bloodborne_join.cpp"
TEST_ROOM="emulator/tests/bloodborne/test_bloodborne_three_players.cpp"
TEST_SIGN="emulator/tests/bloodborne/test_bloodborne_team.cpp"
FILES=(PARTY,HEADER,JOIN,TEST_ROOM,TEST_SIGN)

def one(src,old,new,description):
    count=src.count(old)
    if count!=1:
        raise ValueError(f"five-hunter native game {description}: {count} pinned anchors")
    return src.replace(old,new,1)

def patch(files):
    if set(files)!=set(FILES):
        raise ValueError("five-hunter game patch requires real runtime and BOTH original tests")
    party,header,join,test_room,test_sign=(files[p] for p in FILES)
    party=one(party,
        """bool RoomForMore(bool hosting, size_t in_session, size_t party_online) {
    constexpr size_t MaxPlayers = 3; // the host and two cooperators
    return hosting && in_session < MaxPlayers && party_online > in_session;
}""",
        """bool RoomForMore(bool hosting, size_t in_session, size_t party_online) {
    // YT 5-hunter candidate: the game has four remote GameDataMan slots.
    // This is a host-only summon/search gate, NOT a native session-size
    // bypass; the game's join task and fourth phantom still need a rig.
    constexpr size_t MaxPlayers = 5; // the host and FOUR cooperators
    return hosting && in_session < MaxPlayers && party_online > in_session;
}""",
        "original host re-summon room gate")
    header=one(header,
        "// The host rings again: hosting, fewer than three in the session, a party member online outside.",
        "// The host rings again: hosting, fewer than five in the session, a team member online outside.",
        "game API contract")
    join=one(join,
        "// Hosting, fewer than three in the session, and a party member online that is not in it.",
        "// Hosting, fewer than five in the session, and an authorized team member outside it.",
        "original native join path")
    test_room=one(test_room,
        '''TEST(BloodborneThreePlayers, TheHostRingsOnlyWhileTheSessionHasRoom) {
    EXPECT_TRUE(RoomForMore(true, 2, 3)) << "one guest in, one outside";
    EXPECT_TRUE(RoomForMore(true, 1, 2)) << "a guest dropped out";
    EXPECT_FALSE(RoomForMore(true, 2, 2)) << "everyone is in";
    EXPECT_FALSE(RoomForMore(true, 3, 4)) << "three is the game's limit";
    EXPECT_FALSE(RoomForMore(false, 1, 3)) << "not hosting: the idle search does it";
}''',
        '''TEST(BloodborneThreePlayers, TheHostRingsOnlyWhileTheSessionHasRoom) {
    EXPECT_TRUE(RoomForMore(true, 2, 3)) << "one guest in, one outside";
    EXPECT_TRUE(RoomForMore(true, 1, 2)) << "a guest dropped out";
    EXPECT_FALSE(RoomForMore(true, 2, 2)) << "everyone is in";
    EXPECT_TRUE(RoomForMore(true, 3, 5)) << "two more invited after third";
    EXPECT_TRUE(RoomForMore(true, 4, 5)) << "fifth hunter can enter";
    EXPECT_FALSE(RoomForMore(true, 5, 6)) << "five-player co-op limit";
    EXPECT_FALSE(RoomForMore(false, 1, 5)) << "only the host re-rings";
}''',
        "game room capacity regression")
    test_sign=one(test_sign,
        '''TEST(TeamGate, EachGuestJoinsWithItsOwnPlayerSlot) {
    bbcoop::LobbyState lobby = InTeam("a");
    for (const char* member : {"a", "b", "c", "d"}) {
        lobby.mutable_team()->add_members()->set_member(member);
    }
    EXPECT_EQ(TeamGuestSign(lobby, "b"), 7u);
    EXPECT_EQ(TeamGuestSign(lobby, "c"), 6u);
    EXPECT_EQ(TeamGuestSign(lobby, "d"), 5u);
    EXPECT_EQ(TeamGuestSign(lobby, "x"), 7u) << "not in the team: the game's own";
    EXPECT_EQ(TeamGuestSign(bbcoop::LobbyState{}, "b"), 7u);
}''',
        '''TEST(TeamGate, EachGuestJoinsWithItsOwnPlayerSlot) {
    bbcoop::LobbyState lobby = InTeam("a");
    for (const char* member : {"a", "b", "c", "d", "e"}) {
        lobby.mutable_team()->add_members()->set_member(member);
    }
    EXPECT_EQ(TeamGuestSign(lobby, "b"), 7u);
    EXPECT_EQ(TeamGuestSign(lobby, "c"), 6u);
    EXPECT_EQ(TeamGuestSign(lobby, "d"), 5u);
    EXPECT_EQ(TeamGuestSign(lobby, "e"), 4u) << "fourth guest needs a unique game slot";
    EXPECT_EQ(TeamGuestSign(lobby, "x"), 7u) << "not in the team: the game's own";
    EXPECT_EQ(TeamGuestSign(bbcoop::LobbyState{}, "b"), 7u);
}''',
        "four separate native guest signs")
    return dict(zip(FILES,(party,header,join,test_room,test_sign)))
