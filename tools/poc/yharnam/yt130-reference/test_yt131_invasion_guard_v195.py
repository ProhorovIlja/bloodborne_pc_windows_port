"""V195 invented-source, offline fail-closed tests. No Bloodborne assets."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("yt195", HERE / "stage_yt131_invasion_guard_v195.py")
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)

class GuardTests(unittest.TestCase):
    def test_pinned_original_three_files(self):
        self.assertEqual(len(v.BLOBS), 3)
        self.assertEqual(set(v.BLOBS), set(v.FILES))
        self.assertTrue(all(len(x) == 40 for x in v.BLOBS.values()))
        self.assertEqual(len(v.PIN), 40)

    def test_rejects_unsafe_and_incomplete_sources_before_writes(self):
        with self.assertRaisesRegex(ValueError, "incomplete"):
            v.patch({v.INV:"invented"})
        rows={p:"invented synthetic C++" for p in v.FILES}
        with self.assertRaisesRegex(ValueError, "source drift"):
            v.patch(rows)
        rows[v.TEST] += "\n"+v.MARK
        with self.assertRaisesRegex(ValueError,"already applied"):
            v.patch(rows)

    def test_policy_rechecks_are_in_original_cpp_patch_not_synthetic(self):
        # This only proves the mandatory code-review gates are source-locked.
        source=Path(v.__file__).read_text(encoding="utf-8")
        for token in (
                "SupportsCurrentServerInvasion(live.players, 1)",
                "const InvasionTarget live = TargetOf(world)",
                "EndInvasion(world.name, bbcoop::InvasionEnd::REFUSED",
                "team->members_size()",
                "candidate >= 4 && candidate <= 7",
                "static_assert(!SupportsCurrentServerInvasion(3, 2))",
                "FifthSeatInvaderCapacityAndOptIn",
                "FiveSeatPublicOpenTeamHonorsServerCapacity"):
            self.assertIn(token,source)
        self.assertNotIn("ImplementedInvadersPerWorld = 3",source)

    def test_anchor_can_only_change_once(self):
        self.assertEqual(v.one("ab","ab","new","once"),"new")
        for bad in ("","xy","ab-ab"):
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError,"drift"):
                v.one(bad,"ab","new","once")
        with self.assertRaisesRegex(ValueError,"drift"):
            v.one("ab new","ab","new","reapply")

if __name__=="__main__":
    unittest.main()
