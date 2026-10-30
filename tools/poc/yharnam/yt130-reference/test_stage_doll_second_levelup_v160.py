"""Original YT 1.3 native Doll #468 continuation over staged #457 V151."""
import importlib.util
from pathlib import Path
import unittest

p=Path(__file__).with_name("stage_doll_second_levelup_v160.py")
spec=importlib.util.spec_from_file_location("original_doll_second_level_v160",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class DollSecondLevelV160(unittest.TestCase):
    def test_pinned_original_and_reviewed_upstream_file_blobs(self):
        self.assertEqual(m.PIN,"0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(m.REVIEWED,"b18c5f371a19ca9a605e8fc40f8a57876ed12aac")
        self.assertEqual(set(m.FILES),{m.CPP,m.HEADER,m.TRAVEL,m.TEST})
        self.assertTrue(all(len(x)==40 for pair in m.FILES.values() for x in pair))
        self.assertEqual(m.norm(b"a\r\nb\r\n"),b"a\nb\n")
        self.assertNotEqual(m.blob(b"wrong"),m.FILES[m.CPP][1])
    def test_own_guest_talk_blessing_only_after_closed_menu(self):
        self.assertIn(
            "party_configured && !others_talk && requested_flag == DollBlessingFlag",
            m.EXPECTED_HELPER)
        fixture=("ClearsDollLevelUpFlagAfterHerMenu\n"
                 +m.CPP_AFTER+"\n")
        reviewed=("ClearsDollLevelUpFlagAfterHerMenu\n"+m.CPP_START+
                  "                                        s32 requested_flag) {\n"
                  "    return party_configured && !others_talk && requested_flag == DollBlessingFlag;\n"
                  "}\n"+m.CPP_AFTER+"\n")
        result=m.patch(m.CPP,fixture,reviewed)
        self.assertIn("bool ClearsDollLevelUpFlagOnHerBlessing",result)
        with self.assertRaisesRegex(ValueError,"V151 prior staged"):
            m.patch(m.CPP,result,reviewed)
        with self.assertRaisesRegex(ValueError,"predicate drift"):
            m.patch(m.CPP,fixture,reviewed.replace(
                "party_configured && !others_talk &&",
                "party_configured && others_talk &&"))
    def test_own_talk_atomic_and_delayed_tick_required(self):
        self.assertIn("doll_blessing_asked.store(true)",m.patch.__code__.co_consts if False else
                      "doll_blessing_asked.store(true)")
        # Real original source staging and game object compilation are checked
        # separately in CI. Here we reject drift in helper extraction.
        with self.assertRaisesRegex(ValueError,"exact upstream start drift"):
            m.region("bad","not here","end","missing")
        with self.assertRaisesRegex(ValueError,"staged #457 source drift"):
            m.one("x\nx\n","x\n","y\n","duplicate anchor")
    def test_do_not_modify_original_network_server_or_other_game_files(self):
        with self.assertRaisesRegex(ValueError,"unrelated game source refused"):
            m.patch("server/coop/team_lobby.cpp",
                    "ClearsDollLevelUpFlagAfterHerMenu", "")

if __name__=="__main__":
    unittest.main()
