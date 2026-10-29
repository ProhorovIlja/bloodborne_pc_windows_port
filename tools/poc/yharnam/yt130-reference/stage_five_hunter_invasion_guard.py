#!/usr/bin/env python3
"""Stage original Qt YT1.3 five-hunter invasion vacancy fix, CI ONLY.

Requires original pinned InvasionMaxPlayers=4 and the already-staged
five-member TeamLobby + non-hosted real C++ tests. The guard uses full
TEAM RESERVATIONS, not merely currently connected in-world players, and
rechecks after the 10s invasion notice before changing world/routing state.
A live 4-hunter team may still take one invader (free sign 4); a 5-hunter
team cannot accept a sixth occupant even during race / reconnection.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import sys

H = "server/coop/invasions.h"
WORLD = "server/src/bloodborne_world.cpp"
TEST = "server/tests/test_bloodborne_world.cpp"
FILES = (H, WORLD, TEST)
ORIGINAL_H_SHA = "4c3441dfefd1913966b7d715622389b48960364a"
TAG = "SHYT-YT130-FIVE-HUNTER-INVASION-CAPACITY-V1"


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def exactly(s: str, old: str, new: str, label: str) -> str:
    count = s.count(old)
    if count != 1:
        raise ValueError(f"five-hunter invasion {label}: expected 1 anchor, got {count}")
    return s.replace(old, new, 1)


def patch(raw: dict[str, str]) -> dict[str, str]:
    if set(raw) != set(FILES):
        raise ValueError("invasion guard requires all three source files")
    h,world,test=(raw[p] for p in FILES)
    if TAG in h or TAG in world or TAG in test:
        raise ValueError("five-hunter invasion patch applied twice")
    if "constexpr size_t TeamSize = 5" not in raw.get(
        "server/coop/team_lobby.h", "constexpr size_t TeamSize = 5"
    ):
        raise ValueError("five hunter TeamLobby not present")
    if "NonHostedTeamEditsAreCoalescedAndStartStillWorks" not in test:
        raise ValueError("Expected preceding source-pinned original C++ test staging")
    h=exactly(h,
        "// The game's player slots (the host and three): an invader needs a free one, so a session of\n"
        "// this many is never invaded.\n"
        "constexpr size_t InvasionMaxPlayers = 4;",
        "// "+TAG+": one host + FOUR guest sign slots 7/6/5/4.\n"
        "// A fifth team occupant reserves the final guest sign, even when offline.\n"
        "constexpr size_t InvasionMaxPlayers = 5;",
        "capacity")
    world=exactly(world,
'''    for (const auto& [key, member] : members) {
        if (member.party == world.name && !member.hostile) {
            ++target.players;
            target.members.push_back({member.map, member.level, member.boss});
        }
    }
    return target;
}''',
'''    for (const auto& [key, member] : members) {
        if (member.party == world.name && !member.hostile) {
            ++target.players;
            target.members.push_back({member.map, member.level, member.boss});
        }
    }
    // '''+TAG+''': a signed-in team member reserves their game slot even
    // if their native UDP link is temporarily absent. A stale PLAYING count
    // must never authorize a sixth participant during matchmaking.
    if (world.session) {
        if (const bbcoop::Team* team = lobby.TeamOf(world.session->host())) {
            target.players = std::max(
                target.players, static_cast<size_t>(team->members_size()));
        }
    }
    return target;
}''',
        "reserved slots in TargetOf")
    world=exactly(world,
'''    Member& invader = found->second;
    invader.visiting = world.name;
    invader.hostile = true;
    invasion.joined = true;
    invasion.joined_ms = now_ms;
    // Its slot byte: the configured one, or the first free below the guests' 7/6/5.
    std::set<std::uint32_t> taken;
    if (const bbcoop::Team* team = lobby.TeamOf(world.session->host())) {
        for (const bbcoop::TeamMember& m : team->members()) {
            taken.insert(m.sign());
        }
    }
    std::uint32_t sign = invasion_rules.sign;
    for (std::uint32_t free = 4; taken.contains(sign) && free > 0; --free) {
        sign = free;
    }
    bbcoop::Envelope start;''',
'''    // '''+TAG+''': match occurred BEFORE the 10s notice. Players can join,
    // reconnect, enter a boss arena or turn invaders OFF meanwhile. Recheck
    // CURRENT original-world state before mutating hostile flags or routing.
    const bbcoop::Team* team = lobby.TeamOf(world.session->host());
    const InvasionTarget live = TargetOf(world);
    if (!team || !live.session_open || !live.allows_invaders ||
        live.players >= InvasionMaxPlayers ||
        std::ranges::any_of(live.members, [](const auto& m) { return m.boss; })) {
        EndInvasion(world.name, bbcoop::InvasionEnd::REFUSED, now_ms, result);
        return;
    }
    // Only guest signs 4/5/6/7 are supported by the five-hunter team.
    // Never choose 0, an occupied sign, or a sixth unrecognized sign.
    std::set<std::uint32_t> taken;
    for (const bbcoop::TeamMember& m : team->members()) {
        taken.insert(m.sign());
    }
    const auto available = [&](std::uint32_t candidate) {
        return candidate >= 4 && candidate <= 7 && !taken.contains(candidate);
    };
    std::uint32_t sign = available(invasion_rules.sign) ? invasion_rules.sign : 0;
    for (const std::uint32_t candidate : {4u, 5u, 6u, 7u}) {
        if (!sign && available(candidate)) {
            sign = candidate;
        }
    }
    if (!sign) {
        EndInvasion(world.name, bbcoop::InvasionEnd::REFUSED, now_ms, result);
        return;
    }
    Member& invader = found->second;
    invader.visiting = world.name;
    invader.hostile = true;
    invasion.joined = true;
    invasion.joined_ms = now_ms;
    bbcoop::Envelope start;''',
        "recheck after 10s notice before world mutation")
    anchor='''int AnInvasionNeedsTheServerAndTheTeamToAllowIt() {
'''
    added='''int AJoinedFiveHunterTeamRejectsAnAlreadyNotifiedInvader() {
  InvasionRig rig;
  Game c{1003, "cc", 14}, d{1004, "dd", 15}, e{1005, "ee", 16};
  rig.red.Invade(60, rig.now);
  rig.red.Map(InvadedMap, rig.now);
  rig.Step();
  CHECK(rig.red.notices.size() == 1);
  CHECK(!rig.red.invasion);
  // While the 10-second invasion notice runs, three more guests
  // reserve signs 6/5/4 in the ORIGINAL five-hunter Qt TeamLobby.
  for (Game* guest : std::vector<Game*>{&c, &d, &e}) {
    rig.games.push_back(guest);
    guest->LobbyHello(false, rig.now);
    rig.Step();
    rig.a.Team(bbcoop::TeamRequest::INVITE, rig.now, guest->name);
    rig.Step();
    CHECK(guest->lobby.invites_size() == 1);
    guest->Team(bbcoop::TeamRequest::ACCEPT, rig.now, {},
                guest->lobby.invites(0).team());
    rig.Step();
  }
  CHECK(rig.a.lobby.team().members_size() == 5);
  bool fourth_guest_sign = false;
  for (const auto& m : rig.a.lobby.team().members()) {
    if (m.member() == "ee") fourth_guest_sign = m.sign() == 4;
  }
  CHECK(fourth_guest_sign);
  rig.Step(InvasionNoticeMs);
  CHECK(!rig.red.invasion);
  CHECK(EndedFor(rig.red, bbcoop::InvasionEnd::REFUSED));
  CHECK(rig.service.VisitingOf(rig.red.endpoint).isEmpty());
  CHECK(!rig.Routes(rig.red, rig.a, 0x06));
  return 0;
}

int AFourHunterTeamCanStillBeInvadedInItsOnlyVacantSlot() {
  InvasionRig rig;
  Game c{1003, "cc", 14}, d{1004, "dd", 15};
  for (Game* guest : std::vector<Game*>{&c, &d}) {
    rig.games.push_back(guest);
    guest->LobbyHello(false, rig.now);
    rig.Step();
    rig.a.Team(bbcoop::TeamRequest::INVITE, rig.now, guest->name);
    rig.Step();
    CHECK(guest->lobby.invites_size() == 1);
    guest->Team(bbcoop::TeamRequest::ACCEPT, rig.now, {},
                guest->lobby.invites(0).team());
    rig.Step();
  }
  CHECK(rig.a.lobby.team().members_size() == 4);
  CHECK(rig.Invade());
  CHECK(rig.red.invasion->session().sign() == 4);
  CHECK(rig.service.VisitingOf(rig.red.endpoint) ==
        rig.service.PartyOf(rig.a.endpoint));
  return 0;
}

'''+anchor
    test=exactly(test,anchor,added,"real live-world join/reject regressions")
    test=exactly(test,
'''      {"AnInvaderJoinsATeamWorldAfterANotice",
       AnInvaderJoinsATeamWorldAfterANotice},
''',
'''      {"AnInvaderJoinsATeamWorldAfterANotice",
       AnInvaderJoinsATeamWorldAfterANotice},
      {"AJoinedFiveHunterTeamRejectsAnAlreadyNotifiedInvader",
       AJoinedFiveHunterTeamRejectsAnAlreadyNotifiedInvader},
      {"AFourHunterTeamCanStillBeInvadedInItsOnlyVacantSlot",
       AFourHunterTeamCanStillBeInvadedInItsOnlyVacantSlot},
''',
        "C++ native test registration")
    return dict(zip(FILES,(h,world,test)))


def stage(root: Path) -> None:
    root=root.resolve(strict=True)
    paths={p:root/p for p in FILES}
    originals={}
    for name,path in paths.items():
        if path.is_symlink() or not path.is_file():
            raise ValueError("missing or linked invasion source: " + name)
        raw=path.read_bytes()
        if name==H and blob(raw)!=ORIGINAL_H_SHA:
            raise ValueError("original invasion header source pin drift")
        originals[name]=raw.decode("utf-8")
    # No partial patching on failed anchors. The source must already contain
    # the original 5-hunter lobby and all earlier staging (the workflow orders).
    if "constexpr size_t TeamSize = 5;" not in (
        root/"server/coop/team_lobby.h").read_text("utf-8"):
        raise ValueError("five-hunter lobby was not staged")
    changes=patch(originals)
    for name,path in paths.items():
        path.write_text(changes[name],encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv)!=2:
        raise SystemExit("usage: stage_five_hunter_invasion_guard.py DISPOSABLE_YT_SOURCE")
    stage(Path(sys.argv[1]))
    print("SHYT_QT_FIVE_HUNTER_INVASION_VACANCY_RECHECK_SOURCE_STAGE_ONLY")
