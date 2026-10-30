"""V151 source-exact YT1.3 Doll fixes from upstream #457, no fake game test."""
from pathlib import Path
import importlib.util
import unittest

p=Path(__file__).with_name("stage_doll_own_flag_v151.py")
spec=importlib.util.spec_from_file_location("doll_own_v151",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class OriginalDollV151(unittest.TestCase):
    def test_pinned_git_blob_sources_and_no_server_changes(self):
        self.assertEqual(m.BASE_PIN,"0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(m.REVIEWED_PIN,"3ce88c205648616b52b729fc2764b6fe27f7af83")
        self.assertEqual(len(m.FILES),7)
        for path in m.FILES:
            self.assertTrue(path.startswith("emulator/"))
            self.assertFalse("server/" in path or "bbport/" in path)
            self.assertEqual(len(m.FILES[path]),2)
            self.assertEqual(len(m.FILES[path][0]),40)
        self.assertEqual(m.normalized(b"x\r\ny\r\n"),b"x\ny\n")
        self.assertNotEqual(m.blob_sha(b"not original"),m.FILES[m.GAME][0])
    def test_exact_doll_menu_reset_conditional_semantics(self):
        self.assertIn("Doll",m.HELPER_START)
        previous=m.OLD_CLEAR+m.HELPER_END
        reviewed=(m.OLD_CLEAR+
            "bool ClearsDollLevelUpFlagAfterHerMenu(bool party_configured, bool level_up_on, bool blessing_on) {\n"
            "    return party_configured && level_up_on && blessing_on;\n"
            "}\n"+m.HELPER_END)
        result=m.apply(m.GAME,previous,reviewed)
        self.assertIn("return party_configured && level_up_on && blessing_on",result)
        with self.assertRaises(m.ValueError if hasattr(m,"ValueError") else ValueError):
            m.apply(m.GAME,result,reviewed)
        with self.assertRaisesRegex(ValueError,"semantics changed"):
            m.apply(m.GAME,previous,reviewed.replace(
                "party_configured && level_up_on && blessing_on",
                "party_configured || level_up_on || blessing_on"))
    def test_flag_owner_rule_is_exact_and_not_shared(self):
        reviewed=(m.RULE_OLD+
            '          "map loads (ClearsDollLevelUpFlagAfterHerMenu)"),\n'+
            m.RULE_NEXT +
            m.RULE_INSERT +
            '          "the Doll\'s blessing: own, not shared"),\n'+
            m.RULE_AFTER)
        original=(m.RULE_OLD+'          "map loads"),\n'+m.RULE_NEXT+m.RULE_AFTER)
        out=m.apply("emulator/src/core/bloodborne_flags.h",original,reviewed)
        self.assertIn("FlagOwner::PerPlayer, 0",out)
        self.assertIn("Range(72100100, 72100102",out)
        self.assertNotIn("FlagOwner::Host, 0",out)
    def test_snapshot_consistency_and_fail_closed_on_upstream_drift(self):
        name="emulator/tests/bloodborne/flag_rules_expected.txt"
        self.assertEqual(m.apply(name,"x\n"+m.EXPECTED_OLD,
                                 "x\n"+m.EXPECTED_NEW),"x\n"+m.EXPECTED_NEW)
        with self.assertRaisesRegex(ValueError,"snapshot changed"):
            m.apply(name,m.EXPECTED_OLD,"x\n")
        with self.assertRaisesRegex(ValueError,"source or duplicate drift"):
            m.exactly("foo\nfoo\n","foo\n","bar\n","ambiguous")
        with self.assertRaisesRegex(ValueError,"region start drift"):
            m.region("missing","start","end","unreviewed")
    def test_no_unreviewed_file_changes(self):
        with self.assertRaisesRegex(ValueError,"refused unrelated"):
            m.apply("server/coop/world.cpp","x","x")

if __name__=="__main__":
    unittest.main()
