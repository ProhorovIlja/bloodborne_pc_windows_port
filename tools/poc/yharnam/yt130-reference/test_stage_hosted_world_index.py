"""Fail-closed source tests for original Hosted world privacy and cache invalidation."""
import importlib.util
from pathlib import Path
import unittest

PATH = Path(__file__).with_name("stage_hosted_world_index.py")
spec = importlib.util.spec_from_file_location("yt_hosted_world_index", PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class HostedWorldIndexTests(unittest.TestCase):
    def original(self):
        # Tiny independently pinned original-stage fixture, not a fake C++ build.
        cpp = "\n".join((
            m.OLD_CLEAR,
            m.OLD_INDEX,
            m.OLD_STATE,
            m.OLD_ADD_WORLD,
            m.OLD_SET_WORLDS,
            m.OLD_TAKE_IDLE,
            m.OLD_NOTE_WORLD,
        ))
        return cpp, m.OLD_FIELDS, m.OLD_MAIN

    def test_hosted_private_member_only_world_list_and_order(self):
        cpp, header, tests = m.rewrite(*self.original())
        self.assertIn("hosted_world_index.clear();", cpp)
        self.assertIn("hosted_world_index[owner].push_back(at);", cpp)
        self.assertIn("std::set<std::string> members_seen", cpp)
        self.assertIn("const auto owned = hosted_world_index.find(member)", cpp)
        self.assertIn("if (shown >= worlds_per_player)", cpp)
        self.assertIn("out.clear_members();", cpp)
        self.assertIn("for (const bbcoop::TeamWorldInfo& world : worlds) {\n            publish_world(world);", cpp)
        self.assertNotIn("!Lists(world.members(), member)", cpp)
        self.assertIn("mutable std::map<std::string, std::vector<size_t>> hosted_world_index;", header)
        self.assertIn("HostedWorldIndexKeepsFortyPartiesPrivateAfterRestoreAndUpdate", tests)

    def test_mutations_invalidate_all_cached_world_offsets(self):
        cpp, _, _ = m.rewrite(*self.original())
        for reason in ("AddWorld", "SetWorlds", "TakeIdleWorlds", "NoteWorld"):
            self.assertIn("Changed(); //", cpp, reason)
        self.assertEqual(cpp.count("Changed(); //"), 4)
        self.assertIn("if (!taken.empty())", cpp)
        self.assertIn("if (changed) {\n        Changed();", cpp)

    def test_exact_pinned_original_cpp_source_required(self):
        self.assertEqual(m.PIN, "0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(m.BLOBS[m.CPP], "7978d8d8062d8c18f1db79b02551c65fba2eb261")
        self.assertEqual(m.BLOBS[m.HEADER], "b97f3b650fbbd0b737accac9992a0bc1da7bd2b8")
        self.assertEqual(m.BLOBS[m.TEST], "c045e637ada5e548b003d34033c912fde54f1d34")

    def test_duplicate_stage_or_drift_fails_closed(self):
        source = self.original()
        rewritten = m.rewrite(*source)
        with self.assertRaises(ValueError):
            m.rewrite(*rewritten)
        for n in range(3):
            changed = list(source)
            changed[n] = changed[n].replace(
                (m.OLD_STATE, m.OLD_FIELDS, m.OLD_MAIN)[n], "BAD SOURCE")
            with self.subTest(file=n), self.assertRaises(ValueError):
                m.rewrite(*changed)
        # This stage must never be used without the prior native roster index.
        cpp, head, test = source
        with self.assertRaises(ValueError):
            m.rewrite(cpp.replace("hosted_solo_index", "unindexed"), head, test)

if __name__ == "__main__":
    unittest.main()
