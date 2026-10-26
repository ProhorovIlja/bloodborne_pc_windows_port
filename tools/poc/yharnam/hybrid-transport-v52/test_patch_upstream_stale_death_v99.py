#!/usr/bin/env python3
"""Original pinned V99 5-file transactional source and memory-write guard."""
import importlib.util
from pathlib import Path
import unittest

p=Path(__file__).with_name("patch_upstream_stale_death_v99.py")
spec=importlib.util.spec_from_file_location("shyt_v99",p)
v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
FIX={
v.PARTY_H:'''std::string TargetCandidateBlock(const TargetCandidate& candidate);
// Where the board has the other members down on''',
v.PARTY_CPP:'''    if (candidate.has_info && (candidate.info_d & 0x10) != 0) {
        return "info 0xd bit 0x10";
    }
    return "";
}

std::vector<LampPosition> OthersDownOnMap''',
v.DEATH_CPP:'''void LogEnemyTargets() {
    // Original game target logging remains alive.
}
} // namespace Coop

} // namespace Core::Bloodborne
''',
v.RE_CPP:'''        LogUnsharedNearbyCharacters();
    }
    LogOtherPlayersChanges();''',
v.INTERNAL_H:'''void LogEnemyTargets();
void LogJoinTasksOnChange();'''
}
class TestStaleDeathV99(unittest.TestCase):
    def test_transactional_original_game_rewrite_and_guards(self):
        old={k:x.encode() for k,x in FIX.items()}
        out=v.patch(old)
        self.assertEqual(len(out),5)
        self.assertEqual(old[v.PARTY_CPP],FIX[v.PARTY_CPP].encode())
        h=out[v.PARTY_H].decode()
        policy=out[v.PARTY_CPP].decode()
        game=out[v.DEATH_CPP].decode()
        tick=out[v.RE_CPP].decode()
        self.assertIn("StaleDeathMarks::Tick",policy)
        self.assertIn("p.handle==body.handle && p.info==body.info",policy)
        self.assertIn("body.dead || body.downed || body.invader",policy)
        self.assertIn("last_visit!=visit",policy)
        self.assertIn("now_ms-since>=HoldMs",policy)
        self.assertIn("static constexpr s64 HoldMs=3000;",h)
        self.assertIn("ClearStaleDeathMarks();",tick)
        self.assertIn("if(!InPartyHere())",game)
        self.assertIn("CurrentPlace().visit!=visit",game)
        self.assertIn("HasMemoryAccess(found->info+0x18,1,MemoryProt::CpuWrite)",game)
        self.assertIn("ReadValue<u32>(p.character,0x08)!=handle",game)
        self.assertIn("ReadValue<u64>(control,0x30)!=found->info",game)
        self.assertIn("std::ranges::find(invaders,handle)!=invaders.end()",game)
        self.assertIn("WriteValue(found->info,0x18,static_cast<u8>(bits&~u8{1}))",game)
        self.assertNotIn("direct_egress.Arm(",game)
        self.assertNotIn("HostP2P",game)
        with self.assertRaisesRegex(ValueError,"already applied"):
            v.patch(out)
    def test_any_upstream_drift_is_a_total_failure(self):
        original={k:x.encode() for k,x in FIX.items()}
        for name in v.FILES:
            broken=dict(original)
            broken[name]=b"changed original file!"
            with self.subTest(name=name),self.assertRaisesRegex(ValueError,"drift"):
                v.patch(broken)
            self.assertEqual(original[name],FIX[name].encode())
        broken=dict(original);del broken[v.RE_CPP]
        with self.assertRaisesRegex(ValueError,"missing native source"):
            v.patch(broken)

if __name__=="__main__":
    unittest.main()
