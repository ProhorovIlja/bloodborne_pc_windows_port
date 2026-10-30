"""V156 source-locked observed Qt LobbyState reason categories, no private logs."""
import importlib.util
from pathlib import Path
import unittest

p=Path(__file__).with_name("stage_lobby_notice_v156.py")
spec=importlib.util.spec_from_file_location("yt130_v156_notice",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class OriginalLobbyReasonsV156(unittest.TestCase):
    def bbload_fixture(self):
        return ("struct Totals {\n"+m.COUNTERS_OLD+"\n};\n"+
                "void Game::Take(const bbcoop::Envelope &envelope, s64 now_us) {\n"+
                m.TAKE_OLD+"\n  }\n}\n"+
                "void Load::Finish() {\n"+m.OUT_OLD+"\n}\n"+
                "// Previously staged original bbload:\n"
                "udp_write_failed\nsteady_packets_sent\n")
    def shard_fixture(self):
        return ('// SHYT-V155-ORIGINAL-QT-ANONYMOUS-DATA-WIRE\n'
                'print(json.dumps({\n'+m.SHARD_OLD+'\n}))\n')
    def test_source_pin_and_exact_diagnostic_only_changes(self):
        self.assertEqual(m.PIN,"0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(m.BLOB,"edfb6ea39b898cca2638d65826981cf9fc81c334")
        staged=m.patch_bbload(self.bbload_fixture())
        self.assertEqual(staged.count(m.MARKER),1)
        self.assertIn('lobby.notice() == "no hunter of that name is online"',staged)
        self.assertIn('lobby.notice() == "several hunters have that name: give yours the team',staged)
        self.assertIn('lobby.notice() == "too many wrong codes or names: try again in a minute"',staged)
        self.assertIn('++load.totals.team_other_notice',staged)
        self.assertIn('++load.totals.team_total_notices',staged)
        self.assertIn('{"team_name_absent", static_cast<double>(totals.team_name_absent)}',staged)
        self.assertNotIn('fprintf(',m.TAKE_NEW)
        self.assertNotIn('qInfo(',m.TAKE_NEW)
        self.assertNotIn('std::cout',m.TAKE_NEW)
        self.assertNotIn('toHex()',m.TAKE_NEW)
        self.assertNotIn('lobby.players()',m.TAKE_NEW)
        with self.assertRaisesRegex(ValueError,"must follow"):
            m.patch_bbload(staged)
        self.assertEqual(staged.count("udp_write_failed"),1)
        self.assertEqual(staged.count("steady_packets_sent"),1)
    def test_actual_original_shards_aggregate_all_categories(self):
        staged=m.patch_shards(self.shard_fixture())
        for key in ("team_name_absent","team_name_ambiguous",
                    "team_lookup_throttled","team_other_notice",
                    "team_total_notices"):
            self.assertIn(f'"{key}": sum(r["{key}"] for r in results)',staged)
        self.assertIn(m.SHARD_OLD,staged)
        self.assertNotIn("user=",m.SHARD_NEW)
        self.assertNotIn("ip=",m.SHARD_NEW)
        with self.assertRaisesRegex(ValueError,"already staged"):
            m.patch_shards(staged)
    def test_fail_closed_on_missing_staged_prerequisites_and_anchor_drift(self):
        with self.assertRaisesRegex(ValueError,"V141"):
            m.patch_bbload(self.bbload_fixture().replace("udp_write_failed","missing"))
        with self.assertRaisesRegex(ValueError,"V155"):
            m.patch_shards(self.shard_fixture().replace(
                "SHYT-V155-ORIGINAL-QT-ANONYMOUS-DATA-WIRE","missing"))
        for anchor in (m.COUNTERS_OLD,m.TAKE_OLD,m.OUT_OLD):
            with self.subTest(anchor=anchor[:30]):
                with self.assertRaises(ValueError):
                    m.patch_bbload(self.bbload_fixture().replace(anchor,"BROKEN"))
                with self.assertRaises(ValueError):
                    m.patch_bbload(self.bbload_fixture()+anchor)
        with self.assertRaises(ValueError):
            m.patch_shards(self.shard_fixture().replace(m.SHARD_OLD,"missing"))
    def test_reasons_are_event_observations_not_unique_player_failures(self):
        self.assertIn("counts are reply observations",m.TAKE_NEW)
        self.assertIn("not unique",m.TAKE_NEW)
        self.assertNotIn("team_id",m.TAKE_NEW)
        self.assertNotIn("member.id",m.TAKE_NEW)
        self.assertNotIn("address",m.TAKE_NEW)

if __name__=="__main__":
    unittest.main()
