"""V162 original native guest Doll own-talk and command-71 end fix guards."""
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location("doll_v162",Path(__file__).with_name("stage_doll_talk_v162.py"))
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class DollTalkV162(unittest.TestCase):
    def fixture(self, name):
        old,new=m.PATCHES[name]
        prefix="BeginsDollBlessing ClearsDollLevelUpFlagOnHerBlessing\n"
        if name=="src/core/bloodborne_travel.cpp":
            return prefix+old+m.TALK_OLD, prefix+new+m.TALK_NEW
        return prefix+old, prefix+new

    def test_pinned_source_and_all_four_paths(self):
        self.assertEqual(m.REVIEWED,"4a55f02c48207770273e0cf0ed5d06e85a9143e5")
        self.assertEqual(m.ORIGINAL,"0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(len(m.FILES),4)
        self.assertEqual(set(m.PATCHES),set(m.FILES))
        self.assertTrue(all(len(h)==40 for pair in m.FILES.values() for h in pair))
        self.assertNotEqual(m.blob(b"wrong"),next(iter(m.FILES.values()))[1])

    def test_exact_upstream_471_hunks_and_repeated_patch_refused(self):
        for name in m.FILES:
            with self.subTest(name=name):
                before,upstream=self.fixture(name)
                after=m.patch(name,before,upstream)
                self.assertIn(m.PATCHES[name][1],after)
                self.assertNotIn(m.PATCHES[name][0],after)
                if name=="src/core/bloodborne_travel.cpp":
                    self.assertIn("std::ranges::any_of(OtherPlayers()",after)
                    self.assertIn("doll_blessing_end_asked.store(true)",after)
                with self.assertRaises(ValueError):
                    m.patch(name,after,upstream)
                with self.assertRaises(ValueError):
                    m.patch(name,before,upstream.replace(m.PATCHES[name][1],"modified"))

    def test_fail_closed_on_unrelated_files_and_v160_absent(self):
        with self.assertRaises(ValueError):
            m.patch("server/game_server.cpp","BeginsDollBlessing ClearsDollLevelUpFlagOnHerBlessing","")
        old,head=self.fixture("src/core/bloodborne_party.cpp")
        with self.assertRaises(ValueError):
            m.patch("src/core/bloodborne_party.cpp",old.replace("ClearsDollLevelUpFlagOnHerBlessing","no_prior_v160"),head)
        self.assertIn("return talk_command == 71",m.PATCHES["src/core/bloodborne_party.cpp"][1])

if __name__=="__main__":
    unittest.main()
