"""V162: unit guards for source-exact YT 471 Doll guest begin/end blocks."""
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location("yt162",Path(__file__).with_name("stage_doll_talk_v162.py"))
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class DollTalkV162(unittest.TestCase):
    def test_pinned_native_source_and_only_four_original_files(self):
        self.assertEqual(m.REVIEWED,"4a55f02c48207770273e0cf0ed5d06e85a9143e5")
        self.assertEqual(m.PREVIOUS,"b18c5f371a19ca9a605e8fc40f8a57876ed12aac")
        self.assertEqual(m.MIDDLE,"a64214d4875ff7cbe735b155e8b075261891e1cc")
        self.assertEqual(len(m.FILES),4)
        self.assertEqual(set(m.FILES),{m.CPP,m.HEADER,m.TRAVEL,m.TEST})
        self.assertTrue(all(len(sha)==40 for pair in m.FILES.values() for sha in pair))
        self.assertNotEqual(m.blob(b"wrong"),next(iter(m.FILES.values()))[1])

    def test_exact_source_marker_guards(self):
        self.assertEqual(m.region("before\nA\nexact\nB\nend","A\n","B\n","test"),
                         "A\nexact\n")
        with self.assertRaisesRegex(ValueError,"start marker drift"):
            m.region("bad","missing","end","missing")
        with self.assertRaisesRegex(ValueError,"end marker drift"):
            m.region("A","A","B","missing end")
        with self.assertRaisesRegex(ValueError,"staged hunk drift"):
            m.one("old\nold\n","old\n","new\n","duplicated")
        with self.assertRaisesRegex(ValueError,"staged hunk drift"):
            m.one("new\n","old\n","new\n","already applied")

    def test_pinned_cpp_full_helper_trio_is_required(self):
        base="ClearsDollLevelUpFlagOnHerBlessing\n"+m.CPP_END
        helper=(m.CPP_START+"    return level_up_on;\n}\n\n"
                "bool EndsDollBlessing(s32 talk_command) {\n"
                "    return talk_command == 71;\n}\n\n"
                "std::optional<bool> DollBlessingStepFor(bool g,bool b,bool e,bool s) {\n"
                "    return std::nullopt;\n}\n")
        middle=helper.replace("bool EndsDollBlessing(s32 talk_command) {\n    return talk_command == 71;\n}\n\n","")
        result=m.patch(m.CPP,base,"",helper+m.CPP_END,middle)
        self.assertIn("bool EndsDollBlessing",result)
        self.assertIn("DollBlessingStepFor",result)
        with self.assertRaisesRegex(ValueError,"not #468 whole source"):
            m.patch(m.CPP,result,"",helper+m.CPP_END,middle)
        with self.assertRaisesRegex(ValueError,"dependency/source review drift"):
            m.patch(m.CPP,base,"",helper.replace("return talk_command == 71;",
                                                  "return talk_command == 72;")+m.CPP_END,middle)

    def test_header_and_original_native_flag_regression_transplanted(self):
        header=(m.HEADER_START+"\n"
                "constexpr auto DollBlessingSteps=1;\n"
                "bool EndsDollBlessing(s32 talk_command);\n")
        base="ClearsDollLevelUpFlagOnHerBlessing\n"+m.HEADER_END
        new=m.patch(m.HEADER,base,"",header+m.HEADER_END,"")
        self.assertIn("DollBlessingSteps",new)
        self.assertIn("EndsDollBlessing",new)
        upstream_test=(m.TEST_START+"\n"
                       "TEST(BloodborneFlagRules, AGuestsDollBlessingFinishesWithoutTheKneelEvents) {\n"
                       " EXPECT_TRUE(EndsDollBlessing(71));\n"
                       " DollBlessingStepFor(true, true, false, false);\n}\n")
        testbase="ClearsDollLevelUpFlagOnHerBlessing\n"+m.TEST_END
        new=m.patch(m.TEST,testbase,"",upstream_test+m.TEST_END,"")
        self.assertIn("AGuestsDollBlessingFinishesWithoutTheKneelEvents",new)
        self.assertIn("EXPECT_TRUE(EndsDollBlessing(71))",new)

    def test_native_travel_tick_requires_begin_and_end_and_own_talker(self):
        prior_hook=(m.HOOK_START+
                    "    if (ClearsDollLevelUpFlagOnHerBlessing(true, false, 1)) {\n"
                    "        doll_blessing_asked.store(true);\n"
                    "    }\n")
        new_hook=(m.HOOK_START+
                  "    if (std::ranges::any_of(OtherPlayers(), [](auto) { return true; }) &&\n"
                  "        BeginsDollBlessing(true)) {\n"
                  "        doll_blessing_end_asked.store(true);\n"
                  "    }\n")
        talk_new=(m.TALK_START+
                  "    if (EndsDollBlessing(71)) {\n"
                  "        doll_blessing_end_asked.store(true);\n"
                  "    }\n")
        old_tick=(m.TICK_START+"void ClearDollLevelUpFlagAfterHerMenu() {}\n\n")
        new_tick=(m.TICK_START+
                  "void ClearDollLevelUpFlagAfterHerMenu(bool asked) {}\n"
                  "void FinishGuestDollBlessing(bool begin_asked, bool end_asked) {\n"
                  "    DollBlessingStepFor(true, begin_asked, end_asked, false);\n"
                  "    PartyGhostSetEventFlagOffset;\n}\n\n")
        base=("ClearsDollLevelUpFlagOnHerBlessing\n"
              "std::atomic<bool> doll_blessing_asked{};\n"
              +prior_hook+m.HOOK_END+"\n"
              +m.TALK_START+m.TALK_END+"\n"
              +old_tick+m.TICK_END+"\n"
              +m.TICK_OLD)
        reviewed=(new_hook+m.HOOK_END+"\n"
                  +talk_new+m.TALK_END+"\n"
                  +new_tick+m.TICK_END+"\n"
                  +m.TICK_NEW)
        result=m.patch(m.TRAVEL,base,prior_hook+m.HOOK_END,reviewed,"")
        self.assertIn("std::ranges::any_of(OtherPlayers()",result)
        self.assertIn("doll_blessing_end_asked.exchange(false)",result)
        self.assertIn("FinishGuestDollBlessing(",result)
        self.assertNotIn(m.TICK_OLD,result)
        with self.assertRaises(ValueError):
            m.patch(m.TRAVEL,result,prior_hook+m.HOOK_END,reviewed,"")

    def test_staged_full_upstream_helper_is_exact_and_mutations_fail(self):
        helper=(m.CPP_START+"    return level_up_on;\n}\n\n"
                "bool EndsDollBlessing(s32 talk_command) {\n"
                "    return talk_command == 71;\n}\n\n"
                "std::optional<bool> DollBlessingStepFor(bool guest,bool begin,bool end,bool step) {\n"
                "    return std::nullopt;\n}\n")
        middle=helper.replace("bool EndsDollBlessing(s32 talk_command) {\n"
                              "    return talk_command == 71;\n}\n\n","")
        base="ClearsDollLevelUpFlagOnHerBlessing\n"+m.CPP_END
        reviewed=helper+m.CPP_END
        staged=m.patch(m.CPP,base,"",reviewed,middle)
        m.verify_staged(m.CPP,staged,reviewed)
        with self.assertRaisesRegex(ValueError,"differs from reviewed"):
            m.verify_staged(m.CPP,
                            staged.replace("return talk_command == 71;",
                                           "return talk_command == 72;"),
                            reviewed)
        with self.assertRaisesRegex(ValueError,"start marker drift"):
            m.verify_staged(m.CPP,"not a real native source",reviewed)

    def test_unrelated_path_refused(self):
        with self.assertRaisesRegex(ValueError,"not #468 whole source"):
            m.patch("server/coop.cpp","ClearsDollLevelUpFlagOnHerBlessing","","","")

if __name__=="__main__":
    unittest.main()
