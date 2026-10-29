"""Original Qt five-hunter invasion admission regression, source fail-closed."""
from pathlib import Path
import tempfile
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
import stage_five_hunter_invasion_guard as guard

H="""// The game's player slots (the host and three): an invader needs a free one, so a session of
// this many is never invaded.
constexpr size_t InvasionMaxPlayers = 4;
"""
WORLD="""    if (outcome.changed) {
        StoreWorldList(result);
    }
    // Invasions: the leader turned them off: a running one ends.
    for (const auto& [key, member] : members) {
        if (member.party == world.name && !member.hostile) {
            ++target.players;
            target.members.push_back({member.map, member.level, member.boss});
        }
    }
    return target;
}

void Service::JoinInvasion(PartyWorld& world, Invasion& invasion, qint64 now_ms, Result& result) {
    Member& invader = found->second;
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
    bbcoop::Envelope start;
"""
TEST="""// NonHostedTeamEditsAreCoalescedAndStartStillWorks
int AnInvasionNeedsTheServerAndTheTeamToAllowIt() {
}
      {"AnInvaderJoinsATeamWorldAfterANotice",
       AnInvaderJoinsATeamWorldAfterANotice},
"""
SOURCES={guard.H:H,guard.WORLD:WORLD,guard.TEST:TEST}


class InvasionGate(unittest.TestCase):
    def test_five_hunter_capacity_and_just_in_time_world_guard(self):
        result=guard.patch(SOURCES)
        self.assertEqual(result[guard.H].count(guard.TAG),1)
        self.assertIn("constexpr size_t InvasionMaxPlayers = 5;",result[guard.H])
        cpp=result[guard.WORLD]
        self.assertEqual(cpp.count(guard.TAG),3)
        self.assertLess(cpp.index("live.players >= InvasionMaxPlayers"),
                        cpp.index("invader.visiting = world.name;"))
        self.assertLess(cpp.index("if (!sign) {"),
                        cpp.index("invader.visiting = world.name;"))
        self.assertIn("team->members_size()",cpp)
        self.assertIn("!live.allows_invaders",cpp)
        self.assertIn("m.boss",cpp)
        self.assertIn("AJoiningFifthHunterRevokesAlreadyJoinedInvader",
                      result[guard.TEST])
        self.assertIn("EndInvasion(party, bbcoop::InvasionEnd::REFUSED",
                      cpp)
        self.assertIn("candidate <= 7",cpp)
        tests=result[guard.TEST]
        self.assertIn("AJoinedFiveHunterTeamRejectsAnAlreadyNotifiedInvader",tests)
        self.assertIn("AFourHunterTeamCanStillBeInvadedInItsOnlyVacantSlot",tests)
        self.assertIn("EndedFor(rig.red, bbcoop::InvasionEnd::REFUSED)",tests)
        self.assertIn("rig.red.invasion->session().sign() == 4",tests)
        with self.assertRaisesRegex(ValueError,"twice"):
            guard.patch(result)

    def test_world_invasion_source_drift_is_not_silently_patched(self):
        cases=[
            {**SOURCES,guard.H:H.replace("= 4;","= 5;")},
            {**SOURCES,guard.WORLD:WORLD.replace("taken.contains(sign)","false")},
            {**SOURCES,guard.WORLD:WORLD.replace(
                "    invader.visiting = world.name;","")},
            {**SOURCES,guard.WORLD:WORLD.replace(
                "target.members.push_back({member.map, member.level, member.boss});","")},
            {**SOURCES,guard.TEST:TEST.replace(
                "NonHostedTeamEditsAreCoalescedAndStartStillWorks","")},
        ]
        for case in cases:
            with self.subTest(index=cases.index(case)):
                with self.assertRaises(ValueError):
                    guard.patch(case)

    def test_only_exact_required_original_files(self):
        with self.assertRaises(ValueError):
            guard.patch({guard.H:H})
        self.assertEqual(len(guard.ORIGINAL_H_SHA),40)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            for path,s in SOURCES.items():
                source=root/path
                source.parent.mkdir(parents=True,exist_ok=True)
                source.write_text(s,encoding="utf-8")
            (root/"server/coop/team_lobby.h").write_text(
                "constexpr size_t TeamSize = 5;",encoding="utf-8")
            before={path:(root/path).read_bytes() for path in SOURCES}
            with self.assertRaisesRegex(ValueError,"source pin drift"):
                guard.stage(root)
            self.assertEqual(before,
                             {path:(root/path).read_bytes() for path in SOURCES})


if __name__=="__main__":
    unittest.main()
