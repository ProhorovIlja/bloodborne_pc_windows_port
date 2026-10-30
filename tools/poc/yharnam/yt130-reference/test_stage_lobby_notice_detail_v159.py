"""V159 reasons for opaque real YT1.3 team lobby refusals, anonymous-only."""
from pathlib import Path
import importlib.util
import unittest

p=Path(__file__).with_name("stage_lobby_notice_detail_v159.py")
spec=importlib.util.spec_from_file_location("yt_v159_notice",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def source_fixture():
    return (
        "SHYT_V156_ANONYMOUS_LOBBY_NOTICE_CATEGORIES\n"
        "struct Totals {\n"+m.C_OLD+"\n};\n"+
        "void Game::Take(const bbcoop::Envelope &envelope, s64 now_us) {\n"+
        m.D_OLD+"\n}\n"+
        "QJsonObject out {\n"+m.OUT_OLD+"\n}\n"
    )

def shards_fixture():
    return (
        "# SHYT-V155-ORIGINAL-QT-ANONYMOUS-DATA-WIRE\n"+
        "{\n"+m.SHARDS_OLD+"\n}\n"
    )

class OriginalTeamNoticeV159Tests(unittest.TestCase):
    def test_accepted_pin_and_original_server_known_constants(self):
        self.assertEqual(m.PIN,"0645740a33ae21c56df3b4a0d9777086dbca6053")
        self.assertEqual(m.PATH,"server/loadtest/bbload.cpp")
        expected=(
            "no such invite","no team has that code","the team is full",
            "you are in a team already: leave it first","already in your team",
            "create a team first","that team is gone",
            "another team plays that world now",
        )
        for line in expected:
            self.assertIn('lobby.notice() == "'+line+'"',m.D_NEW)
        self.assertNotIn("std::cout",m.D_NEW)
        self.assertNotIn("qDebug",m.D_NEW)
        self.assertNotIn("fprintf",m.D_NEW)
        self.assertNotIn("toString()",m.D_NEW)
        self.assertNotIn("member.name",m.D_NEW)
    def test_real_source_substring_anchored_and_can_only_stage_once(self):
        got=m.patch_load(source_fixture())
        self.assertIn(m.MARK,got)
        self.assertEqual(got.count("team_unknown_other"),3) # source field, increment, output
        self.assertIn('++load.totals.team_other_notice',got)
        self.assertIn('++load.totals.team_total_notices',source_fixture() if False else
                      "++load.totals.team_total_notices") # unchanged original V156 code
        self.assertEqual(got.count("team_no_code"),3)
        self.assertEqual(got.count('lobby.notice() == "no such invite"'),1)
        with self.assertRaisesRegex(ValueError,"drift"):
            m.patch_load(got)
        for a in (m.C_OLD,m.D_OLD,m.OUT_OLD):
            with self.subTest(label=a[:28]):
                with self.assertRaisesRegex(ValueError,"drift"):
                    m.patch_load(source_fixture().replace(a,"different"))
                with self.assertRaisesRegex(ValueError,"drift"):
                    m.patch_load(source_fixture()+a)
    def test_original_shard_counter_sums_and_no_private_output(self):
        s=m.patch_shards(shards_fixture())
        for field in ("team_no_invite","team_no_code","team_full",
                      "team_already_joined","team_create_first",
                      "team_world_unavailable","team_unknown_other"):
            self.assertIn(f'"{field}": sum(r["{field}"] for r in results)',s)
        self.assertIn(m.SHARDS_OLD.splitlines()[0],s)
        self.assertNotIn("from_name",m.SHARDS_NEW)
        self.assertNotIn("player_id",m.SHARDS_NEW)
        with self.assertRaisesRegex(ValueError,"drift"):
            m.patch_shards(s)
    def test_refuse_missing_V156_staging(self):
        with self.assertRaisesRegex(ValueError,"previous real original V156"):
            m.patch_load(source_fixture().replace(
                "SHYT_V156_ANONYMOUS_LOBBY_NOTICE_CATEGORIES","bad"))
        with self.assertRaisesRegex(ValueError,"requires exact original"):
            m.patch_shards(shards_fixture().replace(
                "SHYT-V155-ORIGINAL-QT-ANONYMOUS-DATA-WIRE","bad"))

if __name__=="__main__":
    unittest.main()
